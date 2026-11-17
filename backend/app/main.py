
from fastapi import FastAPI, Request, HTTPException
from langserve import add_routes
from app.models.chat_request import ChatRequest, ChatResponse

from app.agents.bpmn_creator import bpmn_creator

app = FastAPI(title="BPMN Generator API")

add_routes(
    app,
    bpmn_creator,
    # path="/bpmn",
    config_keys=("configurable",),
    # per_req_config_modifier=preserve_thread_id,
)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    result = await bpmn_creator.ainvoke(
        {"messages": [("user", req.message)]},
        config={"configurable": {"thread_id": req.session_id}},
    )
    return result["structured_response"]
