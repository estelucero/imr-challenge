import logging
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.chat_request import ChatRequest, ChatResponse

from app.agents.orchestrator import get_orchestrator


logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")

logger = logging.getLogger("app.main")

origins = [
    "http://localhost:3000",
]

app = FastAPI(title="BPMN Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    started = perf_counter()
    response_status = "exception"
    try:
        graph = get_orchestrator(req.model, req.provider)
        result = await graph.ainvoke(
            {
                "messages": [("user", req.message)],
                "request_id": req.session_id,
            },
            config={"configurable": {"thread_id": req.session_id}},
        )

        # Guard: ninguna terminal escribió la respuesta -> nunca un 500 por None.
        response = result.get("response")
        if response is None:
            logger.error(
                "chat: orchestrator finished without response | request_id=%s keys=%s",
                req.session_id,
                list(result),
            )
            response_status = "error"
            return ChatResponse(
                status="error",
                message="No se pudo procesar el pedido. Intentá de nuevo.",
                bpmn_xml=None,
            )

        response_status = response.status
        return response
    finally:
        logger.info(
            "chat_timing request_id=%s provider=%s model=%s status=%s elapsed_ms=%.1f",
            req.session_id,
            req.provider,
            req.model or "default",
            response_status,
            (perf_counter() - started) * 1000,
        )
