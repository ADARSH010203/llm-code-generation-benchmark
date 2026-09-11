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

# Prevent very large repositories from being copied into every model request.
# Full retrieval/ranking is a future improvement; this guard keeps the current
# workflow predictable and makes the limitation explicit.
MAX_CONTEXT_CHARS = 80_000


def _limit_source_context(content: str) -> str:
    """Keep repository source context within a predictable request budget."""
    if len(content) <= MAX_CONTEXT_CHARS:
        return content
    return (
        content[:MAX_CONTEXT_CHARS]
        + "\n\n[Repository source truncated for context safety. "
        "Use the summary/structure and focus on the files relevant to the task.]")


def _build_prompt(prompt: str, context: dict[str, Any]) -> str:
    """Build one shared repository-aware prompt for both models."""
    source = _limit_source_context(context.get("content", ""))

    return f"""You are modifying an existing software repository.

Repository summary:
{context.get('summary', '')}

Repository structure:
{context.get('structure', '')}

Repository source context:
{source}

Task:
{prompt}

Guidelines:
- Follow the repository's existing architecture and coding conventions.
- Preserve existing behavior unless the task requires a change.
- Reuse existing modules and patterns before creating new abstractions.
- Handle realistic errors and relevant edge cases.
- Never include credentials, tokens, passwords, or secrets.
- Keep the implementation focused and maintainable.
- Do not invent files, APIs, dependencies, or functions that are not justified by the repository.

Output format:
- For a single-file change, return the code directly.
- For a multi-file change (for example, a website), return each file using this format:

FILE: path/to/file.ext
```language
file contents
```

Repeat the FILE block for every file that must be created or changed.
- Do not add explanations outside the code/file blocks.
"""


def _api_key_for(model_name: str) -> str:
    """Read the API key required by the selected model."""
    config = MODEL_CONFIG.get(model_name)
    if config is None:
        raise ValueError(f"Unsupported model: {model_name}")

    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise RuntimeError(
            f"Missing {config['api_key_env']}. Add it to the local environment."
        )
    return api_key


async def stream_model_response(
    model_name: str,
    prompt: str,
    context: dict[str, Any],
) -> AsyncIterator[str]:
    """Stream generated output from one benchmark model."""
    config = MODEL_CONFIG.get(model_name)
    if config is None:
        raise ValueError(f"Unsupported model: {model_name}")

    response = await acompletion(
        model=config["model"],
        messages=[{"role": "user", "content": _build_prompt(prompt, context)}],
        api_key=_api_key_for(model_name),
        max_tokens=4000,
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
    """Create independent streams so both models receive the same task."""
    return (
        stream_model_response("llama_scout", prompt, context),
        stream_model_response("aya_expanse", prompt, context),
    )
