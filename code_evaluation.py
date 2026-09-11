"""LLM-as-a-judge evaluation for generated code."""

from typing import Any

from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

SCORE_THRESHOLD = 7.0


def _metric(
    name: str,
    criteria: str,
    steps: list[str],
    params: list[LLMTestCaseParams],
) -> GEval:
    """Create a consistently configured G-Eval metric."""
    return GEval(
        name=name,
        criteria=criteria,
        evaluation_steps=steps,
        evaluation_params=params,
        rubric=[
            Rubric(score_range=(0, 2), expected_outcome="Poor; major problems make the result unsuitable."),
            Rubric(score_range=(3, 5), expected_outcome="Partially acceptable; important issues remain."),
            Rubric(score_range=(6, 8), expected_outcome="Good; mostly correct with minor issues."),
            Rubric(score_range=(9, 10), expected_outcome="Excellent; complete, reliable, and production-ready."),
        ],
        threshold=SCORE_THRESHOLD,
    )


def evaluate_code(
    generated_code: str,
    task: str,
    reference_code: str | None = None,
) -> dict[str, Any]:
    """Evaluate generated code for correctness, readability, and best practices.

    A reference implementation is optional. When supplied, correctness is
    judged against it. Without one, the evaluator uses the requested task and
    repository context represented by the task description.
    """
    if not generated_code.strip():
        return {
            "error": "Generated code is empty.",
            "overall_score": 0.0,
            "detailed_metrics": {},
            "passed": False,
        }

    try:
        test_case = LLMTestCase(
            input=task,
            actual_output=generated_code,
            expected_output=reference_code or "No reference implementation was provided.",
        )

        correctness = _metric(
            name="Code Correctness",
            criteria=(
                "Evaluate whether the generated code satisfies the requested task, "
                "is functionally sound, handles relevant edge cases, and avoids "
                "obvious runtime or integration problems."
            ),
            steps=[
                "Compare the implementation with the requested task.",
                "Check whether the required behavior is implemented completely.",
                "Look for obvious runtime errors and incorrect assumptions.",
                "Check relevant edge cases and integration with the stated repository context.",
            ],
            params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
        )

        readability = _metric(
            name="Code Readability",
            criteria="Evaluate clarity, naming, formatting, structure, and useful documentation.",
            steps=[
                "Check naming for clarity and consistency.",
                "Check formatting, indentation, and logical organization.",
                "Assess whether comments and docstrings explain non-obvious behavior.",
                "Check whether the implementation is easy for another developer to maintain.",
            ],
            params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        )

        best_practices = _metric(
            name="Code Best Practices",
            criteria=(
                "Evaluate maintainability, error handling, security, efficiency, "
                "modularity, and responsible handling of configuration and secrets."
            ),
            steps=[
                "Check error handling and failure behavior.",
                "Check for hard-coded secrets or unsafe configuration handling.",
                "Assess unnecessary complexity and avoidable performance issues.",
                "Check modularity, reuse, and separation of concerns.",
            ],
            params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        )

        metrics = [correctness, readability, best_practices]
        for metric in metrics:
            metric.measure(test_case)

        scores = [metric.score for metric in metrics]
        overall_score = sum(scores) / len(scores)

        detailed_metrics = {
            "correctness": {"score": correctness.score, "reason": correctness.reason},
            "readability": {"score": readability.score, "reason": readability.reason},
            "best_practices": {
                "score": best_practices.score,
                "reason": best_practices.reason,
            },
        }

        return {
            "overall_score": overall_score,
            "detailed_metrics": detailed_metrics,
            "passed": overall_score >= SCORE_THRESHOLD,
        }

    except Exception as exc:
        return {
            "error": f"Evaluation failed: {exc}",
            "overall_score": 0.0,
            "detailed_metrics": {},
            "passed": False,
        }
