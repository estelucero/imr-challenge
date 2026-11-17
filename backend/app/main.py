
from fastapi import FastAPI, Request, HTTPException
from langserve import add_routes
from app.models.chat_request import ChatRequest, ChatResponse

from app.agents.bpmn_creator import get_bpmn_creator

app = FastAPI(title="BPMN Generator API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    creator = get_bpmn_creator(req.model,req.provider)   
    result = await creator.ainvoke(
        {"messages": [("user", req.message)]},
        config={"configurable": {"thread_id": req.session_id}},
    )
    return result["structured_response"]
