"""LLM adapter for the bounded self-repair agent loop."""

from __future__ import annotations

from typing import Any

from litellm import acompletion

from .model_service import MODEL_CONFIG, _api_key_for


async def repair_with_model(
    model_name: str,
    repair_prompt: str,
) -> str:
    """Generate one repaired candidate using an existing benchmark model."""
    config: dict[str, Any] | None = MODEL_CONFIG.get(model_name)
    if config is None:
        raise ValueError(f"Unsupported model: {model_name}")

    response = await acompletion(
        model=config["model"],
        messages=[{"role": "user", "content": repair_prompt}],
        api_key=_api_key_for(model_name),
        max_tokens=6000,
        stream=False,
        timeout=90,
        num_retries=1,
    )
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    content = getattr(choices[0].message, "content", None)
    return str(content or "").strip()
