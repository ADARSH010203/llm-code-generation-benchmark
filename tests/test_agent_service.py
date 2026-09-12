import asyncio
import pytest

from benchmark.agent_service import repair_with_model


def test_repair_adapter_rejects_unknown_model() -> None:
    with pytest.raises(ValueError):
        asyncio.run(repair_with_model("unknown", "repair"))
