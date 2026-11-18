"""Prueba manual del agente aclarador contra la API real.

NO es un test unitario de pytest: hace llamadas LLM de verdad (necesita la API
key y consume tokens). Se corre a mano dentro del contenedor:

    docker compose exec backend python tests/check_clarifier.py [provider]

provider: openrouter (default) | openai
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.clarifier import clarifier_model_name, get_clarifier, load_clarifier_prompt

PROVIDER = sys.argv[1] if len(sys.argv) > 1 else "openrouter"
CASE_LIMIT_S = 240  # techo por caso (el ReadTimeout del SDK es ~200s)


def to_messages(history):
    return [
        HumanMessage(content=text) if role == "user" else AIMessage(content=text)
        for role, text in history
    ]


SPANISH_MARKERS = (
    "cómo", "qué", "cuál", "cuándo", "quién", "dónde", "proceso",
    "participa", "termina", "cuando", "necesito",
)

STOPWORDS = {
    "de", "la", "el", "los", "las", "que", "y", "o", "a", "en", "para", "del",
    "al", "un", "una", "se", "su", "lo", "como", "es", "por", "qué", "cuál",
    "cuando", "cómo", "dónde", "quién", "si", "hay", "the", "of", "to", "is",
    "and", "or", "in", "for", "on", "what", "how", "when", "who", "which",
    "does", "do", "is", "it",
}


def words(text: str) -> set[str]:
    return {w.strip(".,;:!?¿¡\"'()").lower() for w in text.split()}


def looks_spanish(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in SPANISH_MARKERS)


def gap_overlap(question: str, gaps: list[str]) -> bool:
    qw = words(question) - STOPWORDS
    return any(qw & (words(gap) - STOPWORDS) for gap in gaps)


CASES = [
    {
        "name": "1) pregunta solo sobre los vacíos indicados",
        "history": [("user", "Proceso de compras")],
        "gaps": [
            "No está definido qué inicia el proceso de compras",
            "No se indicaron los pasos principales ni su orden",
            "No se definió cuándo termina una compra",
        ],
        "checks": [
            ("entre 1 y 3 preguntas", lambda d: 1 <= len(d["questions"]) <= 3, ""),
            (
                "sin jerga técnica",
                lambda d: not any(
                    t in " ".join(d["questions"]).lower()
                    for t in ("xml", "bpmn", "pool", "lane", "columna")
                ),
                "",
            ),
        ],
    },
    {
        "name": "2) cada pregunta corresponde a un vacío del analista",
        "history": [(
            "user",
            "Proceso de reclamos de soporte: el cliente hace un reclamo, el "
            "agente de soporte lo evalúa y el desarrollador lo corrige. El "
            "proceso termina cuando el reclamo queda cerrado.",
        )],
        "gaps": [
            "No se definió qué decide el agente para escalar o cerrar el reclamo",
            "No se dijo cómo se notifica al desarrollador",
        ],
        "checks": [
            ("preguntas sobre los gaps", lambda d: bool(d["questions"]) and all(
                gap_overlap(
                    q,
                    [
                        "No se definió qué decide el agente para escalar o cerrar el reclamo",
                        "No se dijo cómo se notifica al desarrollador",
                    ],
                )
                for q in d["questions"]
            ), "cada pregunta debería tocar un gap reportado"),
        ],
    },
    {
        "name": "3) no repite información respondida; pregunta por lo nuevo",
        "history": [
            ("user", "Modelá el proceso de pedidos online de la tienda."),
            (
                "assistant",
                "- ¿Qué participantes intervienen en el proceso?\n"
                "- ¿Cómo termina el proceso: cuándo se considera completado un pedido?",
            ),
            (
                "user",
                "Participan el cliente y la tienda, y termina cuando la tienda "
                "despacha el paquete. Además quiero modelar el proceso de "
                "devoluciones.",
            ),
        ],
        "gaps": [
            "No se describieron los pasos del proceso de devoluciones",
            "No se definió cuándo termina el proceso de devoluciones",
        ],
        "checks": [
            (
                "pregunta por lo nuevo (devoluciones)",
                lambda d: any("devoluci" in q.lower() for q in d["questions"]),
                "",
            ),
            (
                "no vuelve a preguntar participantes del proceso anterior",
                lambda d: not any("particip" in q.lower() for q in d["questions"]),
                "",
            ),
        ],
    },
    {
        "name": "4) idioma: pregunta en el idioma del usuario",
        "history": [("user", "Purchase process")],
        "gaps": ["The process trigger is not specified"],
        "checks": [
            (
                "preguntas en inglés",
                lambda d: bool(d["questions"]) and not looks_spanish(" ".join(d["questions"])),
                "las preguntas no deberían tener marcadores de español",
            ),
        ],
    },
]


async def run_case(case: dict, clarifier) -> bool:
    print(f"\n=== {case['name']} ===")
    inputs = [SystemMessage(content=load_clarifier_prompt()), *to_messages(case["history"])]
    inputs.append(
        SystemMessage(
            content="Process Analyst specification: business facts from the conversation.\n"
            "Essential gaps identified by the Process Analyst:\n- "
            + "\n- ".join(case["gaps"])
        )
    )

    t0 = time.time()
    try:
        result = await asyncio.wait_for(
            clarifier.ainvoke({"messages": inputs}), timeout=CASE_LIMIT_S
        )
    except asyncio.TimeoutError:
        print(f"  ✗ HANG >{CASE_LIMIT_S}s (wait_for lo mató)")
        return False
    except Exception as exc:
        print(f"  ✗ {type(exc).__name__} en {time.time() - t0:.1f}s: {str(exc)[:200]}")
        return False

    structured = result.get("structured_response")
    if structured is None:
        last = result.get("messages", [])[-1:]
        print(f"  ✗ sin structured_response en {time.time() - t0:.1f}s | last: {str(last)[:150]}")
        return False

    data = structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)
    print(f"  {time.time() - t0:.1f}s -> questions={len(data['questions'])}")
    for question in data["questions"]:
        print(f"    ? {question}")

    failures = []
    for name, check, detail in case["checks"]:
        ok = check(data)
        print(f"    {'✓' if ok else '✗'} {name}" + (f" — {detail}" if not ok and detail else ""))
        if not ok:
            failures.append(name)
    return not failures


async def main() -> int:
    clarifier = get_clarifier(PROVIDER)
    print(f"Aclarador: provider={PROVIDER} modelo={clarifier_model_name(PROVIDER)}")

    results = [await run_case(case, clarifier) for case in CASES]
    passed = sum(results)
    print(f"\n{'=' * 50}\nRESULTADO: {passed}/{len(CASES)} casos OK")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
