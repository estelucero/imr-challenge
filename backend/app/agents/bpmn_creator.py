
from pathlib import Path
from functools import lru_cache
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from langchain.agents.structured_output import ToolStrategy 
from app.models.chat_request import ChatResponse

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = BASE_DIR / "prompts" / "bpmn_system_prompt.md"

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_PROVIDER = "openrouter"

checkpointer = InMemorySaver()

def load_system_prompt() -> str:
    """Lee el sys_prompt de la carpeta prompts"""
    return PROMPT_PATH.read_text(encoding="utf-8")

@lru_cache(maxsize=32)
def get_bpmn_creator(model_name: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER):
    """Crea un cachea un modelo para diferentes instancias con un cache
    de 16 modelos.
    Las sesiones son independientes pero el checkpointer es singleton.
    """
    model = init_chat_model(
        f"{provider}:{model_name or DEFAULT_MODEL}",
        temperature=0,
        timeout = 300_000 if provider == "openrouter" else 300,
        max_tokens=25000,
        max_retries=1,
    )
    return create_agent(
        model=model,
        tools=[],
        system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        checkpointer=checkpointer,
        response_format=ToolStrategy(ChatResponse),
    )