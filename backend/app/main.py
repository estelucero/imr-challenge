
from fastapi import FastAPI, Request, HTTPException
from langserve import add_routes

from app.agents.bpmn_creator import bpmn_creator

app = FastAPI(title="BPMN Generator API")


async def preserve_thread_id(config: dict, request: Request) -> dict:
    body = await request.json()

    thread_id = (
        body.get("config", {})
        .get("configurable", {})
        .get("thread_id")
    )

    if not thread_id:
        raise HTTPException(
            status_code=400,
            detail="thread_id is required"
        )

    config = dict(config)
    configurable = dict(config.get("configurable", {}))
    configurable["thread_id"] = str(thread_id)

    config["configurable"] = configurable

    return config


add_routes(
    app,
    bpmn_creator,
    path="/bpmn",
    config_keys=("configurable",),
    per_req_config_modifier=preserve_thread_id,
)


@app.get("/health")
def health():
    return {"status": "ok"}
