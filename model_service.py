"""Model access and parallel streaming for the benchmark."""

import os
from collections.abc import AsyncIterator
from typing import Any

from litellm import acompletion


MODEL_CONFIG = {
    "aya_expanse": {
        "label": "Cohere Aya Expanse",
        "model": "c4ai-aya-expanse-32b",
        "api_key_env": "COHERE_API_KEY",
    },
    "llama_scout": {
        "label": "Meta Llama 4 Scout",
        "model": "llama-4-scout-17b-16e-instruct",
        "api_key_env": "CEREBRAS_API_KEY",
    },
}


def _build_prompt(prompt: str, context: dict[str, Any]) -> str:
    """Build the shared repository-aware prompt used by both models."""
    repository_summary = context.get("summary", "")
    repository_structure = context.get("structure", "")
    repository_content = context.get("content", "")

    return f"""You are contributing code to an existing software repository.

Repository summary:
{repository_summary}

Repository structure:
{repository_structure}

Repository source:
{repository_content}

Task:
{prompt}

Implementation rules:
- Match the repository's existing architecture and coding style.
- Reuse existing modules and patterns instead of creating unnecessary abstractions.
- Preserve current behavior unless the task requires a change.
- Handle realistic errors and edge cases.
- Never hard-code API keys, passwords, tokens, or other secrets.
- Keep the implementation focused, readable, and maintainable.
- Return only the code that should be added or changed. Do not wrap it in Markdown fences.
"""


def _api_key_for(model_name: str) -> str:
    """Return the configured API key for a benchmark model."""
    try:
        config = MODEL_CONFIG[model_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported model: {model_name}") from exc

    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise RuntimeError(
            f"Missing {config['api_key_env']}. Configure it in the local environment."
        )
    return api_key


async def stream_model_response(
    model_name: str,
    prompt: str,
    context: dict[str, Any],
) -> AsyncIterator[str]:
    """Stream generated code from one configured model."""
    config = MODEL_CONFIG.get(model_name)
    if config is None:
        raise ValueError(f"Unsupported model: {model_name}")

    response = await acompletion(
        model=config["model"],
        messages=[{"role": "user", "content": _build_prompt(prompt, context)}],
        api_key=_api_key_for(model_name),
        max_tokens=2000,
        stream=True,
    )

    async for chunk in response:
        content = getattr(chunk.choices[0].delta, "content", None)
        if content:
            yield content


async def get_parallel_responses(
    prompt: str,
    context: dict[str, Any],
) -> tuple[AsyncIterator[str], AsyncIterator[str]]:
    """Create independent streams for both benchmark models."""
    aya_stream = stream_model_response("aya_expanse", prompt, context)
    llama_stream = stream_model_response("llama_scout", prompt, context)
    return llama_stream, aya_stream
