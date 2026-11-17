
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = BASE_DIR / "prompts" / "bpmn_system_prompt.md"


def load_system_prompt() -> str:
    """Load BPMN agent instructions from Markdown."""
    return PROMPT_PATH.read_text(encoding="utf-8")


# --------------------------------------------------
# Model
# --------------------------------------------------

model = init_chat_model(
    "openrouter:deepseek/deepseek-v4-flash",
    temperature=0,
    timeout=300_000,
    max_tokens=25000,
    max_retries=1
)


# --------------------------------------------------
# Short-term Memory
# --------------------------------------------------

checkpointer = InMemorySaver()


# --------------------------------------------------
# Agent
# --------------------------------------------------

bpmn_creator = create_agent(
    model=model,
    tools=[],
    system_prompt=load_system_prompt(),
    checkpointer=checkpointer,
)
