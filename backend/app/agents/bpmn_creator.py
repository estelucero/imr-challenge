"""Diagram-creator agent: maps the analyst's process graph to BPMN 2.0 XML.

It is one node of the orchestrator graph (see app/agents/orchestrator.py), so
it holds NO checkpointer of its own. The Process Analyst owns interpretation of
the conversation; this agent receives only the analyst's structured process graph
and runs ephemerally to create or repair the diagram.
"""

from pathlib import Path
from functools import lru_cache

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from langchain.agents.structured_output import ToolStrategy
from app.agents.model_config import DEFAULT_PROVIDER, resolve_model
from app.models.chat_request import BpmnDraft

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = BASE_DIR / "prompts" / "bpmn_creator_flexible_prompt.md"

def load_system_prompt() -> str:
    """Lee el sys_prompt de la carpeta prompts"""
    return PROMPT_PATH.read_text(encoding="utf-8")

@lru_cache(maxsize=32)
def get_bpmn_creator(model_name: str | None = None, provider: str = DEFAULT_PROVIDER):
    """Crea y cachea el agente creador por (modelo, provider).

    Sin checkpointer propio ni herramientas internas: recibe el grafo del
    analizador y genera el borrador. El orquestador coordina la validación y
    la reparación por un agente separado.
    """
    model = init_chat_model(
        f"{provider}:{resolve_model(model_name, provider)}",
        temperature=0,
        timeout=300_000 if provider == "openrouter" else 300,
        max_tokens=25000,
        max_retries=1,
    )
    return create_agent(
        model=model,
        tools=[],
        system_prompt=load_system_prompt(),
        response_format=ToolStrategy(BpmnDraft),
    )
