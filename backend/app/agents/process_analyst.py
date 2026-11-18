"""Build a compact connected business-process graph from conversation history."""

from functools import lru_cache
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model

from app.agents.clarifier import clarifier_model_name
from app.models.process import AnalystProcessGraph

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESS_ANALYST_PROMPT_PATH = BASE_DIR / "prompts" / "process_analyst_prompt.md"


def load_process_analyst_prompt() -> str:
    return PROCESS_ANALYST_PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=8)
def get_process_analyst(provider: str = "openrouter"):
    """Build the cached analyst using the lightweight requirements model."""
    model = init_chat_model(
        f"{provider}:{clarifier_model_name(provider)}",
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
