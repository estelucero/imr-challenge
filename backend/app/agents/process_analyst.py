"""Build a compact connected business-process graph from conversation history."""

from functools import lru_cache
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model

from app.agents.model_config import DEFAULT_PROVIDER, resolve_model
from app.models.process import AnalystProcessGraph

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESS_ANALYST_PROMPT_PATH = BASE_DIR / "prompts" / "process_analyst_prompt.md"


def load_process_analyst_prompt() -> str:
    return PROCESS_ANALYST_PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=32)
def get_process_analyst(model_name: str | None = None, provider: str = DEFAULT_PROVIDER):
    """Build the analyst for the selected model and provider."""
    model = init_chat_model(
        f"{provider}:{resolve_model(model_name, provider)}",
        temperature=0,
        timeout=300_000 if provider == "openrouter" else 300,
        max_retries=1,
    )
    return create_agent(
        model=model,
        tools=[],
        system_prompt=load_process_analyst_prompt(),
        response_format=ToolStrategy(AnalystProcessGraph),
    )
