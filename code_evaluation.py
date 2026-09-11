"""Evaluation utilities for repository-aware code generation.

The benchmark deliberately combines two kinds of evidence:
- deterministic checks (for example, syntax and obvious secret patterns), and
- LLM-based judging for qualities that are difficult to measure statically.

DeepEval metric scores are kept in their native 0-1 range. The UI can display
them on a 0-10 scale for readability.
"""

from __future__ import annotations

import os
from typing import Any

from deepeval.metrics import ArenaGEval, GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.test_case import ArenaTestCase, Contestant, LLMTestCase, SingleTurnParams

from code_validation import validate_generated_output

LLM_SCORE_THRESHOLD = 0.70
DISPLAY_SCALE = 10.0


def _metric(
    name: str,
    steps: list[str],
    evaluation_params: list[SingleTurnParams],
) -> GEval:
    """Create a consistently configured GEval metric."""
    kwargs: dict[str, Any] = {
        "name": name,
        "evaluation_steps": steps,
        "evaluation_params": evaluation_params,
        "rubric": [
            Rubric(score_range=(0, 2), expected_outcome="Poor; major problems make the implementation unsuitable."),
            Rubric(score_range=(3, 5), expected_outcome="Partially acceptable; important problems remain."),
            Rubric(score_range=(6, 8), expected_outcome="Good; mostly correct with minor issues."),
            Rubric(score_range=(9, 10), expected_outcome="Excellent; complete and reliable for the stated task."),
        ],
        "threshold": LLM_SCORE_THRESHOLD,
    }
    if model := os.getenv("DEEPEVAL_MODEL"):
        kwargs["model"] = model
    return GEval(**kwargs)


def _metric_result(metric: GEval) -> dict[str, Any]:
    """Convert a DeepEval metric into the application's result format."""
    score = float(metric.score or 0.0)
    return {
        "score": score,
        "score_10": round(score * DISPLAY_SCALE, 2),
        "reason": metric.reason or "No evaluator reasoning returned.",
        "passed": metric.is_successful(),
    }


def evaluate_code(
    generated_code: str,
    task: str,
    repository_context: str | None = None,
    reference_code: str | None = None,
) -> dict[str, Any]:
    """Evaluate one generated implementation without executing it.

    A reference implementation strengthens correctness evaluation, while
    repository context lets the judge consider integration and conventions.
    """
    validation = validate_generated_output(generated_code)
    if not generated_code.strip():
        return {
            "error": "Generated code is empty.",
            "overall_score": 0.0,
            "overall_score_10": 0.0,
            "detailed_metrics": {},
            "validation": validation,
            "passed": False,
        }

    try:
        evaluation_input = f"Task:\n{task.strip()}"
        if repository_context:
            evaluation_input += f"\n\nRepository context:\n{repository_context.strip()}"

        test_case_kwargs: dict[str, Any] = {
            "input": evaluation_input,
            "actual_output": generated_code,
        }
        correctness_params = [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]

        if reference_code:
            test_case_kwargs["expected_output"] = reference_code
            correctness_params.append(SingleTurnParams.EXPECTED_OUTPUT)

        test_case = LLMTestCase(**test_case_kwargs)

        correctness = _metric(
            name="Code Correctness",
            steps=[
                "Check whether the implementation directly solves the requested task.",
                "Check whether required behavior is complete and internally consistent.",
                "Look for obvious runtime failures, broken assumptions, and relevant edge cases.",
                "When reference code is provided, compare expected behavior with the generated implementation.",
                "Use repository context to identify clear integration conflicts or invented APIs.",
            ],
            evaluation_params=correctness_params,
        )

        readability = _metric(
            name="Code Readability",
            steps=[
                "Check naming, formatting, indentation, and logical organization.",
                "Check whether functions and modules have focused responsibilities.",
                "Assess comments and docstrings for useful context without unnecessary noise.",
                "Penalize avoidable duplication, cleverness, and unnecessary abstraction.",
            ],
            evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        )

        best_practices = _metric(
            name="Code Best Practices",
            steps=[
                "Check error handling and failure behavior.",
                "Check for hard-coded credentials, unsafe input handling, or insecure defaults.",
                "Look for avoidable complexity and obvious performance problems.",
                "Check modularity, reuse, separation of concerns, and maintainability.",
            ],
            evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        )

        metrics = [correctness, readability, best_practices]
        for metric in metrics:
            metric.measure(test_case)

        detailed_metrics = {
            "correctness": _metric_result(correctness),
            "readability": _metric_result(readability),
            "best_practices": _metric_result(best_practices),
        }
        llm_score = sum(item["score"] for item in detailed_metrics.values()) / len(detailed_metrics)

        hard_failure = not validation["security"]["passed"]
        passed = llm_score >= LLM_SCORE_THRESHOLD and not hard_failure

        return {
            "overall_score": round(llm_score, 4),
            "overall_score_10": round(llm_score * DISPLAY_SCALE, 2),
            "detailed_metrics": detailed_metrics,
            "validation": validation,
            "passed": passed,
            "confidence_note": _confidence_note(validation, reference_code),
        }

    except Exception as exc:
        return {
            "error": f"Evaluation failed: {exc}",
            "overall_score": 0.0,
            "overall_score_10": 0.0,
            "detailed_metrics": {},
            "validation": validation,
            "passed": False,
        }


def compare_outputs(
    task: str,
    aya_output: str,
    llama_output: str,
    reference_code: str | None = None,
) -> dict[str, Any]:
    """Run a blinded pairwise judge to choose the stronger implementation."""
    try:
        expected_output = reference_code
        contestants = [
            Contestant(
                name="Aya Expanse",
                hyperparameters={"model": "c4ai-aya-expanse-32b"},
                test_case=LLMTestCase(
                    input=task,
                    actual_output=aya_output,
                    **({"expected_output": expected_output} if expected_output else {}),
                ),
            ),
            Contestant(
                name="Llama 4 Scout",
                hyperparameters={"model": "llama-4-scout-17b-16e-instruct"},
                test_case=LLMTestCase(
                    input=task,
                    actual_output=llama_output,
                    **({"expected_output": expected_output} if expected_output else {}),
                ),
            ),
        ]

        case = ArenaTestCase(contestants=contestants)
        params = [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]
        if reference_code:
            params.append(SingleTurnParams.EXPECTED_OUTPUT)

        kwargs: dict[str, Any] = {
            "name": "Code Generation Pairwise Comparison",
            "evaluation_steps": [
                "Choose the implementation that better satisfies the coding task.",
                "Prefer correct behavior, repository fit, clear design, security, and maintainability.",
                "Do not prefer an implementation only because it is longer or more verbose.",
                "When reference code is provided, use it as evidence of intended behavior.",
            ],
            "evaluation_params": params,
        }
        if model := os.getenv("DEEPEVAL_MODEL"):
            kwargs["model"] = model

        metric = ArenaGEval(**kwargs)
        metric.measure(case)

        return {
            "winner": metric.winner,
            "reason": metric.reason or "No pairwise reasoning returned.",
        }
    except Exception as exc:
        return {
            "winner": None,
            "reason": f"Pairwise comparison unavailable: {exc}",
        }


def _confidence_note(validation: dict[str, Any], reference_code: str | None) -> str:
    """Describe the strength of the evidence behind the displayed score."""
    if validation.get("execution_verified") or validation.get("tests_executed"):
        return "High evidence: deterministic execution/tests were also available."
    if reference_code and validation["syntax"].get("passed") is True:
        return "Medium evidence: static validation plus reference-based LLM judging; runtime behavior was not executed."
    if validation["syntax"].get("passed") is True:
        return "Medium-low evidence: static validation plus LLM judging; functional runtime behavior was not executed."
    return "Low evidence: semantic LLM judging was used, but executable correctness was not verified."
