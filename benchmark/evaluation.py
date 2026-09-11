"""Evaluation utilities for repository-aware code generation.

The benchmark combines deterministic evidence with LLM-based judging. DeepEval
scores are kept in their native 0-1 range and displayed on a 0-10 scale in UI.
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
        # GEval returns a normalized 0-1 score even when a rubric is supplied.
        "rubric": [
            Rubric(score_range=(0.0, 0.2), expected_outcome="Poor; major problems make the implementation unsuitable."),
            Rubric(score_range=(0.3, 0.5), expected_outcome="Partially acceptable; important problems remain."),
            Rubric(score_range=(0.6, 0.8), expected_outcome="Good; mostly correct with minor issues."),
            Rubric(score_range=(0.9, 1.0), expected_outcome="Excellent; complete and reliable for the stated task."),
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
    execution_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate generated output with deterministic and semantic evidence."""
    validation = validate_generated_output(generated_code)
    if not generated_code.strip():
        return {
            "error": "Generated code is empty.",
            "overall_score": 0.0,
            "overall_score_10": 0.0,
            "detailed_metrics": {},
            "validation": validation,
            "execution": execution_result,
            "passed": False,
        }

    try:
        evaluation_input = f"Task:\n{task.strip()}"
        if repository_context:
            evaluation_input += f"\n\nRepository context:\n{repository_context.strip()}"

        kwargs: dict[str, Any] = {
            "input": evaluation_input,
            "actual_output": generated_code,
        }
        correctness_params = [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]
        if reference_code:
            kwargs["expected_output"] = reference_code
            correctness_params.append(SingleTurnParams.EXPECTED_OUTPUT)

        test_case = LLMTestCase(**kwargs)

        correctness = _metric(
            "Code Correctness",
            [
                "Check whether the implementation directly solves the requested task.",
                "Check whether required behavior is complete and internally consistent.",
                "Look for obvious runtime failures, broken assumptions, and relevant edge cases.",
                "When reference code is provided, compare intended behavior with the generated implementation.",
                "Use repository context to identify clear integration conflicts or invented APIs.",
            ],
            correctness_params,
        )
        readability = _metric(
            "Code Readability",
            [
                "Check naming, formatting, indentation, and organization.",
                "Check whether responsibilities are focused and understandable.",
                "Assess comments and docstrings for useful context without unnecessary noise.",
                "Penalize avoidable duplication, cleverness, and unnecessary abstraction.",
            ],
            [SingleTurnParams.ACTUAL_OUTPUT],
        )
        best_practices = _metric(
            "Code Best Practices",
            [
                "Check error handling and failure behavior.",
                "Check for hard-coded credentials, unsafe input handling, and insecure defaults.",
                "Look for avoidable complexity and obvious performance problems.",
                "Check modularity, reuse, separation of concerns, and maintainability.",
            ],
            [SingleTurnParams.ACTUAL_OUTPUT],
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

        security_failed = not validation["security"]["passed"]
        execution_failed = execution_result is not None and execution_result.get("executed") and execution_result.get("passed") is False
        passed = llm_score >= LLM_SCORE_THRESHOLD and not security_failed and not execution_failed

        return {
            "overall_score": round(llm_score, 4),
            "overall_score_10": round(llm_score * DISPLAY_SCALE, 2),
            "detailed_metrics": detailed_metrics,
            "validation": validation,
            "execution": execution_result,
            "passed": passed,
            "confidence_note": _confidence_note(validation, reference_code, execution_result),
        }
    except Exception as exc:
        return {
            "error": f"Evaluation failed: {exc}",
            "overall_score": 0.0,
            "overall_score_10": 0.0,
            "detailed_metrics": {},
            "validation": validation,
            "execution": execution_result,
            "passed": False,
        }


def compare_outputs(
    task: str,
    aya_output: str,
    llama_output: str,
    reference_code: str | None = None,
) -> dict[str, Any]:
    """Run DeepEval's blinded pairwise judge for the two model outputs."""
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
                "Prefer correct behavior, repository fit, security, clarity, and maintainability.",
                "Do not prefer an implementation merely because it is longer or more verbose.",
                "When reference code is supplied, use it as evidence of intended behavior.",
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


def _confidence_note(
    validation: dict[str, Any],
    reference_code: str | None,
    execution_result: dict[str, Any] | None,
) -> str:
    """Explain how much evidence supports the displayed evaluation."""
    if execution_result and execution_result.get("executed"):
        return "High evidence: deterministic sandbox commands were executed in addition to static validation and LLM judging."
    if reference_code and validation["syntax"].get("passed") is True:
        return "Medium evidence: static validation plus reference-based LLM judging; runtime behavior was not executed."
    if validation["syntax"].get("passed") is True:
        return "Medium-low evidence: static validation plus LLM judging; functional runtime behavior was not executed."
    return "Low evidence: semantic LLM judging was used, but executable correctness was not verified."
