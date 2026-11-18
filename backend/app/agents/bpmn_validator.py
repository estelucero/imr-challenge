"""Separate agent for targeted repairs of generated BPMN diagrams."""

from functools import lru_cache
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model

from app.models.chat_request import BpmnDraft

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bpmn_validator_prompt.md"


@lru_cache(maxsize=32)
def get_bpmn_validator(model_name: str, provider: str):
    model = init_chat_model(
        f"{provider}:{model_name}", temperature=0,
        timeout=300_000 if provider == "openrouter" else 300,
        max_tokens=25000, max_retries=1,
    )
    return create_agent(
        model=model, tools=[], system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        response_format=ToolStrategy(BpmnDraft),
    )
