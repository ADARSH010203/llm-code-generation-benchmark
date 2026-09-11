"""LLM-as-a-judge evaluation combined with deterministic validation."""

from __future__ import annotations

from typing import Any

from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from code_validation import validate_generated_output

# DeepEval scores GEval metrics from 0 to 1. The UI converts them to 0–10.
LLM_SCORE_THRESHOLD = 0.70


def _metric(
    name: str,
    criteria: str,
    steps: list[str],
    params: list[LLMTestCaseParams],
) -> GEval:
    """Create one consistently configured GEval metric."""
    return GEval(
        name=name,
        criteria=criteria,
        evaluation_steps=steps,
        evaluation_params=params,
        rubric=[
            Rubric(score_range=(0, 2), expected_outcome="Poor; major problems make the result unsuitable."),
            Rubric(score_range=(3, 5), expected_outcome="Partially acceptable; important issues remain."),
            Rubric(score_range=(6, 8), expected_outcome="Good; mostly correct with minor issues."),
            Rubric(score_range=(9, 10), expected_outcome="Excellent; complete and reliable for the stated task."),
        ],
        threshold=LLM_SCORE_THRESHOLD,
    )


def _metric_result(metric: GEval) -> dict[str, Any]:
    """Convert a DeepEval metric into the application's result format."""
    score = float(metric.score or 0.0)
    return {
        "score": score,
        "score_10": round(score * 10, 2),
        "reason": metric.reason or "No evaluator reasoning returned.",
        "passed": metric.is_successful(),
    }


def evaluate_code(
    generated_code: str,
    task: str,
    reference_code: str | None = None,
) -> dict[str, Any]:
    """Evaluate generated code with deterministic checks and GEval.

    This function intentionally does not execute arbitrary model-generated code.
    A successful syntax check is evidence that the source parses/compiles, not
    proof that the program is functionally correct.
    """
    if not generated_code.strip():
        return {
            "error": "Generated code is empty.",
            "overall_score": 0.0,
            "overall_score_10": 0.0,
            "detailed_metrics": {},
            "validation": validate_generated_output(generated_code),
            "passed": False,
        }

    validation = validate_generated_output(generated_code)

    try:
        test_case = LLMTestCase(
            input=task,
            actual_output=generated_code,
            expected_output=reference_code or "No reference implementation was provided.",
        )

        correctness = _metric(
            name="Code Correctness",
            criteria=(
                "Evaluate whether the generated implementation satisfies the task, "
                "fits the repository context, handles relevant edge cases, and avoids "
                "obvious runtime or integration mistakes."
            ),
            steps=[
                "Compare the output with the requested task.",
                "Check whether required behavior is implemented completely.",
                "Look for obvious runtime errors, broken assumptions, and missing edge cases.",
                "When reference code is provided, compare expected behavior with the implementation.",
            ],
            params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
        )

        readability = _metric(
            name="Code Readability",
            criteria="Evaluate naming, formatting, organization, documentation, and maintainability.",
            steps=[
                "Check naming for clarity and consistency.",
                "Check formatting and logical organization.",
                "Assess comments and docstrings for useful context without unnecessary noise.",
                "Check whether another developer could reasonably maintain the implementation.",
            ],
            params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        )

        best_practices = _metric(
            name="Code Best Practices",
            criteria=(
                "Evaluate error handling, security, efficiency, modularity, and safe configuration."
            ),
            steps=[
                "Check error handling and failure behavior.",
                "Check for hard-coded credentials or unsafe configuration handling.",
                "Look for unnecessary complexity and avoidable performance problems.",
                "Check modularity, reuse, separation of concerns, and maintainability.",
            ],
            params=[LLMTestCaseParams.ACTUAL_OUTPUT],
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

        # A deterministic security failure is a hard fail. Other static checks
        # are reported separately instead of pretending to establish correctness.
        hard_failure = not validation["security"]["passed"]
        passed = llm_score >= LLM_SCORE_THRESHOLD and not hard_failure

        return {
            "overall_score": round(llm_score, 4),
            "overall_score_10": round(llm_score * 10, 2),
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


def _confidence_note(validation: dict[str, Any], reference_code: str | None) -> str:
    """Explain what the evaluation can and cannot establish."""
    if reference_code and validation["syntax"].get("passed") is True:
        return "Medium evidence: static validation plus reference-based LLM judging. Runtime behavior was not executed."
    if validation["syntax"].get("passed") is True:
        return "Medium-low evidence: syntax/security checks plus LLM judging. Functional runtime behavior was not executed."
    if validation["file_count"] > 1:
        return "Low evidence for full-system correctness: multiple files were detected, but no integration test suite was executed."
    return "Low evidence: semantic LLM judging was used, but executable correctness was not verified."
