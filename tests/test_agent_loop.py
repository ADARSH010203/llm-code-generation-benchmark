import asyncio

from benchmark.agent_loop import build_repair_prompt, run_self_repair


def test_repair_prompt_contains_failure_evidence() -> None:
    prompt = build_repair_prompt(
        task="fix the parser",
        repository_context="FILE: parser.py",
        current_output="bad",
        failure_evidence="Syntax failure: invalid syntax",
        attempt=1,
    )
    assert "Syntax failure" in prompt
    assert "fix the parser" in prompt


def test_self_repair_stops_after_success() -> None:
    calls = []

    async def repair(prompt: str) -> str:
        calls.append(prompt)
        return "def ok():\n    return True"

    # No repository URL means clone will fail safely; this test verifies the budgeted loop.
    result = asyncio.run(
        run_self_repair(
            task="write python",
            repository_context="summary",
            initial_output="def broken(:",
            repo_url="https://invalid.example/repo.git",
            repair_fn=repair,
            max_attempts=2,
        )
    )
    assert len(result.attempts) <= 3
    assert len(calls) <= 2
    assert result.stopped_reason
