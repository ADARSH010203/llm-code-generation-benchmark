"""Deterministic + DeepEval scoring for the two benchmark candidates."""
from __future__ import annotations
import os
from typing import Any
from deepeval.metrics import ArenaGEval, GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.test_case import ArenaTestCase, Contestant, LLMTestCase, SingleTurnParams
from .validation import validate_generated_output
THRESHOLD = 0.70

def _metric(name: str, steps: list[str], params: list[SingleTurnParams]) -> GEval:
    kwargs: dict[str, Any] = {"name": name, "evaluation_steps": steps, "evaluation_params": params, "rubric": [Rubric(score_range=(0.0,0.2), expected_outcome="Poor"), Rubric(score_range=(0.3,0.5), expected_outcome="Partially acceptable"), Rubric(score_range=(0.6,0.8), expected_outcome="Good"), Rubric(score_range=(0.9,1.0), expected_outcome="Excellent")], "threshold": THRESHOLD}
    if os.getenv("DEEPEVAL_MODEL"): kwargs["model"] = os.getenv("DEEPEVAL_MODEL")
    return GEval(**kwargs)

def evaluate_code(generated_code: str, task: str, repository_context: str | None = None, reference_code: str | None = None, execution_result: dict[str, Any] | None = None) -> dict[str, Any]:
    validation = validate_generated_output(generated_code)
    if not generated_code.strip(): return {"error":"Generated code is empty.","overall_score":0.0,"overall_score_10":0.0,"detailed_metrics":{},"validation":validation,"execution":execution_result,"passed":False}
    try:
        inp = f"Task:\n{task.strip()}" + (f"\n\nRepository context:\n{repository_context.strip()}" if repository_context else "")
        kwargs: dict[str, Any] = {"input": inp, "actual_output": generated_code}
        params = [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]
        if reference_code: kwargs["expected_output"] = reference_code; params.append(SingleTurnParams.EXPECTED_OUTPUT)
        tc = LLMTestCase(**kwargs)
        metrics = {
            "correctness": _metric("Code Correctness", ["Check task compliance and intended behavior.","Check edge cases, runtime risks, and repository fit.","Use reference output when supplied."], params),
            "readability": _metric("Code Readability", ["Check naming, structure, formatting, clarity, and maintainability."], [SingleTurnParams.ACTUAL_OUTPUT]),
            "best_practices": _metric("Code Best Practices", ["Check error handling, security, efficiency, modularity, and configuration hygiene."], [SingleTurnParams.ACTUAL_OUTPUT]),
        }
        details = {}
        for name, metric in metrics.items():
            metric.measure(tc); score = float(metric.score or 0.0); details[name] = {"score":score,"score_10":round(score*10,2),"reason":metric.reason or "No reasoning returned.","passed":metric.is_successful()}
        score = sum(x["score"] for x in details.values()) / len(details)
        execution_failed = bool(execution_result and execution_result.get("executed") and execution_result.get("passed") is False)
        passed = score >= THRESHOLD and validation["security"]["passed"] and not execution_failed
        return {"overall_score":round(score,4),"overall_score_10":round(score*10,2),"detailed_metrics":details,"validation":validation,"execution":execution_result,"passed":passed,"confidence_note":"Runtime evidence available." if execution_result and execution_result.get("executed") else "Static validation + LLM judging; runtime evidence unavailable."}
    except Exception as exc:
        return {"error":f"Evaluation failed: {exc}","overall_score":0.0,"overall_score_10":0.0,"detailed_metrics":{},"validation":validation,"execution":execution_result,"passed":False}

def compare_outputs(task: str, qwen_output: str, nemotron_output: str, reference_code: str | None = None) -> dict[str, Any]:
    try:
        def contestant(name: str, model: str, output: str) -> Contestant:
            data = {"input":task,"actual_output":output}
            if reference_code: data["expected_output"] = reference_code
            return Contestant(name=name, hyperparameters={"model":model}, test_case=LLMTestCase(**data))
        case = ArenaTestCase(contestants=[contestant("Qwen 3.6 27B","groq/qwen/qwen3.6-27b",qwen_output),contestant("NVIDIA Nemotron 3 Super 120B","openrouter/nvidia/nemotron-3-super-120b-a12b:free",nemotron_output)])
        kwargs: dict[str, Any] = {"name":"Code Generation Pairwise Comparison","evaluation_steps":["Choose the implementation that better satisfies the coding task.","Prefer correctness, repository fit, security, clarity, and maintainability.","Do not prefer length alone."],"evaluation_params":[SingleTurnParams.INPUT,SingleTurnParams.ACTUAL_OUTPUT]}
        if reference_code: kwargs["evaluation_params"].append(SingleTurnParams.EXPECTED_OUTPUT)
        if os.getenv("DEEPEVAL_MODEL"): kwargs["model"] = os.getenv("DEEPEVAL_MODEL")
        metric = ArenaGEval(**kwargs); metric.measure(case)
        return {"winner":metric.winner,"reason":metric.reason or "No pairwise reasoning returned."}
    except Exception as exc: return {"winner":None,"reason":f"Pairwise comparison unavailable: {exc}"}
