"""Shared LLM factory for all agents.

Uses OpenRouter as an OpenAI-compatible API, so any provider's model
can be selected via the OPENROUTER_MODEL env var.
"""

import os

from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI client pointed at OpenAI or OpenRouter."""
    if os.getenv("OPENROUTER_API_KEY"):
        model_name = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = "https://openrouter.ai/api/v1"
    else:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = None

    kwargs = {
        "model": model_name,
        "openai_api_key": api_key,
        "max_retries": 3,
        "temperature": 0.3,
    }
    if base_url:
        kwargs["openai_api_base"] = base_url

    return ChatOpenAI(**kwargs)