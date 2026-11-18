"""Resolve the request's model once, with a provider-specific fallback."""

DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODELS = {
    "openrouter": "deepseek/deepseek-v4-flash",
    "openai": "gpt-6-luna",
}


def resolve_model(model_name: str | None, provider: str = DEFAULT_PROVIDER) -> str:
    """Use the requested model, falling back only when it is absent or blank."""
    if model_name and model_name.strip():
        return model_name.strip()
    return DEFAULT_MODELS[provider]
