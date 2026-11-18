"""Clarifier agent: checks completeness and returns a plain-text summary."""

import os
from functools import lru_cache
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model

from app.models.process import ClarifierResult

BASE_DIR = Path(__file__).resolve().parent.parent

CLARIFIER_PROMPT_PATH = BASE_DIR / "prompts" / "clarifier_prompt.md"

# Modelo liviano por proveedor (los ids de un proveedor no existen en el otro).
DEFAULT_CLARIFIER_MODELS = {
    "openrouter": "minimax/minimax-m3.1-flash",
    "openai": "gpt-6-luna",
}


def clarifier_model_name(provider: str = "openrouter") -> str:
    """Modelo liviano para el aclarador, configurable por env."""
    configured = os.getenv("CLARIFIER_MODEL")
    if configured:
        return configured
    return DEFAULT_CLARIFIER_MODELS.get(provider, DEFAULT_CLARIFIER_MODELS["openrouter"])


def load_clarifier_prompt() -> str:
    return CLARIFIER_PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=8)
def get_clarifier(provider: str = "openrouter"):
    """Aclarador cacheado por provider.

    Sin checkpointer: la conversación la lleva el orquestador, este agente corre
    efímero dentro del turno. Sin tools: devuelve un mensaje para el analista o
    para el cliente y, si faltan datos, preguntas concretas para completarlo.
    """
    model = init_chat_model(
        f"{provider}:{clarifier_model_name(provider)}",
        temperature=0,
        timeout=300_000 if provider == "openrouter" else 300,
        max_retries=1,
    )
    return create_agent(
        model=model,
        tools=[],
        system_prompt=load_clarifier_prompt(),
        response_format=ToolStrategy(ClarifierResult),
    )
