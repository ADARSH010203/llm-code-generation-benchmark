"""Agent-style orchestration for repository-aware coding evaluations.

This module deliberately keeps execution policy conservative: generated output is
validated before it is treated as a candidate workspace, and runtime checks are
performed only through the restricted Docker sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .evaluation import evaluate_code
from .sandbox import parse_generated_files, run_generated_workspace
from .validation import validate_generated_output


@dataclass
class AgentStep:
    """One observable step in a coding-agent trajectory."""

    name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRun:
    """Structured result for one generated coding-agent candidate."""

    output: str
    steps: list[AgentStep]
    validation: dict[str, Any]
    execution: dict[str, Any] | None
    evaluation: dict[str, Any] | None

    @property
    def passed(self) -> bool:
        return bool(self.evaluation and self.evaluation.get("passed"))


def inspect_candidate(output: str) -> AgentStep:
    """Inspect generated output before any sandbox execution."""
    validation = validate_generated_output(output)
    files = parse_generated_files(output)
    security_ok = validation.get("security", {}).get("passed") is not False
    syntax_ok = validation.get("syntax", {}).get("passed") is not False
    status = "passed" if security_ok and syntax_ok else "failed"
    return AgentStep(
        name="candidate_validation",
        status=status,
        details={
            "validation": validation,
            "files": [item["path"] for item in files],
        },
    )


def run_agent_evaluation(
    generated_output: str,
    task: str,
    repository_context: str | None = None,
    reference_code: str | None = None,
    run_sandbox: bool = True,
    base_repository: str | None = None,
) -> AgentRun:
    """Evaluate one candidate through validation, optional sandbox, and judging."""
    validation = validate_generated_output(generated_output)
    steps = [inspect_candidate(generated_output)]

    execution: dict[str, Any] | None = None
    if run_sandbox:
        execution = run_generated_workspace(
            generated_output,
            base_repository=base_repository,
        )
        steps.append(
            AgentStep(
                name="isolated_execution",
                status=(
                    "passed"
                    if execution.get("passed") is True
                    else "failed"
                    if execution.get("passed") is False
                    else "skipped"
                ),
                details=execution,
            )
        )

    evaluation = evaluate_code(
        generated_code=generated_output,
        task=task,
        repository_context=repository_context,
        reference_code=reference_code,
        execution_result=execution,
    )
    steps.append(
        AgentStep(
            name="semantic_evaluation",
            status="passed" if evaluation.get("passed") else "failed",
            details={
                "overall_score": evaluation.get("overall_score"),
                "overall_score_10": evaluation.get("overall_score_10"),
            },
        )
    )

    return AgentRun(
        output=generated_output,
        steps=steps,
        validation=validation,
        execution=execution,
        evaluation=evaluation,
    )


def build_repair_prompt(task: str, run: AgentRun) -> str:
    """Build a bounded repair instruction from observable failure evidence."""
    failures: list[str] = []
    for step in run.steps:
        if step.status == "failed":
            failures.append(f"{step.name}: {step.details}")

    evidence = "\n".join(failures) if failures else "No deterministic failure evidence was recorded."
    return f"""You are repairing a previously generated repository change.

TASK
{task.strip()}

OBSERVED FAILURE EVIDENCE
{evidence}

REPAIR RULES
- Fix the observed failure instead of rewriting unrelated code.
- Preserve the repository's existing public APIs and conventions.
- Keep credentials, tokens, and secrets out of the output.
- Return only the corrected implementation using the same FILE: path fenced-block format when multiple files are required.
"""
