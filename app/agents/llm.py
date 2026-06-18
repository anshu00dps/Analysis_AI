"""OpenAI LLM client factory.

Per-stage LLM selection based on environment configuration. Nodes in the LangGraph
agent call `get_chat_model(stage)` to get a model bound with tools.
"""

from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.models.enums import Stage


def get_chat_model(stage: Stage | str) -> ChatOpenAI:
    """Get a ChatOpenAI model for a stage.

    Reads the per-stage model name from settings (e.g., BRD_AGENT_MODEL) and
    constructs a `ChatOpenAI` instance with the configured API key.
    """
    settings = get_settings()
    stage_str = stage if isinstance(stage, str) else stage.value

    model_attr = f"{stage_str.upper()}_AGENT_MODEL"
    model_name = getattr(settings, model_attr, "gpt-4.1")

    return ChatOpenAI(
        model=model_name,
        api_key=settings.openai_api_key,
        temperature=0.7,
    )
