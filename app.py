"""Streamlit interface for repository-aware LLM code benchmarking."""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from benchmark.agent import inspect_candidate
from benchmark.evaluation import compare_outputs, evaluate_code
from benchmark.ingestion import ingest_github_repo
from benchmark.model_service import get_parallel_responses
from benchmark.retrieval import build_retrieved_context
from benchmark.sandbox import clone_and_run
from benchmark.tasks import load_tasks

load_dotenv()

st.set_page_config(page_title="LLM Code Generation Benchmark", page_icon="🤖", layout="wide")

MODEL_LABELS = {"aya_expanse": "Cohere Aya Expanse", "llama_scout": "Meta Llama 4 Scout"}


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "chat_history": [],
        "context": None,
        "reference_code": "",
        "latest_task": "",
        "last_generated_code": {"aya_expanse": None, "llama_scout": None},
        "evaluation_results": {"aya_expanse": None, "llama_scout": None},
        "pairwise_result": None,
        "execution_results": {"aya_expanse": None, "llama_scout": None},
        "agent_steps": {"aya_expanse": [], "llama_scout": []},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


async def consume_stream(stream: Any, placeholder: Any) -> str:
    output = ""
    async for chunk in stream:
        output += chunk
        placeholder.code(output.strip(), language="text")
    return output.strip()


async def generate_code(task: str) -> tuple[str, str]:
    llama_stream, aya_stream = await get_parallel_responses(task, st.session_state.context)
    aya_column, llama_column = st.columns(2)
    with aya_column:
        st.subheader(MODEL_LABELS["aya_expanse"])
        aya_placeholder = st.empty()
    with llama_column:
        st.subheader(MODEL_LABELS["llama_scout"])
        llama_placeholder = st.empty()

    llama_output, aya_output = await asyncio.gather(
        consume_stream(llama_stream, llama_placeholder),
        consume_stream(aya_stream, aya_placeholder),
    )
    return aya_output, llama_output


def show_generated_history() -> None:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
            continue
        with st.chat_message("assistant"):
            aya_column, llama_column = st.columns(2)
            with aya_column:
                st.subheader(MODEL_LABELS["aya_expanse"])
                st.code(message["aya_response"], language="text")
            with llama_column:
                st.subheader(MODEL_LABELS["llama_scout"])
                st.code(message["llama_response"], language="text")


def _repository_eval_context() -> str:
    context = st.session_state.context or {}
    return f"Summary:\n{context.get('summary', '')}\n\nStructure:\n{context.get('structure', '')}"


def reset_run_state() -> None:
    st.session_state.evaluation_results = {"aya_expanse": None, "llama_scout": None}
    st.session_state.pairwise_result = None
    st.session_state.execution_results = {"aya_expanse": None, "llama_scout": None}
    st.session_state.agent_steps = {"aya_expanse": [], "llama_scout": []}


def evaluate_latest() -> None:
    outputs = st.session_state.last_generated_code
    if not outputs["aya_expanse"] or not outputs["llama_scout"]:
        st.error("Generate code with both models before evaluating it.")
        return
    with st.spinner("Running validation and model comparison..."):
        for model_name, code in outputs.items():
            st.session_state.evaluation_results[model_name] = evaluate_code(
                generated_code=code,
                task=st.session_state.latest_task,
                repository_context=_repository_eval_context(),
                reference_code=st.session_state.reference_code or None,
                execution_result=st.session_state.execution_results.get(model_name),
            )
        st.session_state.pairwise_result = compare_outputs(
            task=st.session_state.latest_task,
            aya_output=outputs["aya_expanse"],
            llama_output=outputs["llama_scout"],
            reference_code=st.session_state.reference_code or None,
        )


def run_sandbox_checks() -> None:
    outputs = st.session_state.last_generated_code
    repo_url = st.session_state.get("github_repo", "")
    if not repo_url:
        st.error("Enter a GitHub repository URL before running sandbox checks.")
        return
    if not outputs["aya_expanse"] or not outputs["llama_scout"]:
        st.error("Generate code from both models before running sandbox checks.")
        return
    with st.spinner("Running isolated checks..."):
        for model_name, output in outputs.items():
            st.session_state.execution_results[model_name] = clone_and_run(repo_url, output)
    evaluate_latest()


def run_agent_evaluation() -> None:
    """Run the visible agent trajectory: validate -> sandbox -> judge."""
    outputs = st.session_state.last_generated_code
    repo_url = st.session_state.get("github_repo", "")
    if not outputs["aya_expanse"] or not outputs["llama_scout"]:
        st.error("Generate code with both models before running agent evaluation.")
        return
    if not repo_url:
        st.error("Enter a GitHub repository URL before running agent evaluation.")
        return

    with st.spinner("Running agent-style evaluation: validate → sandbox → judge..."):
        for model_name, output in outputs.items():
            candidate_step = inspect_candidate(output)
            execution = clone_and_run(repo_url, output)
            result = evaluate_code(
                generated_code=output,
                task=st.session_state.latest_task,
                repository_context=_repository_eval_context(),
                reference_code=st.session_state.reference_code or None,
                execution_result=execution,
            )
            st.session_state.agent_steps[model_name] = [
                candidate_step,
                {"name": "isolated_execution", "status": "passed" if execution.get("passed") is True else "failed" if execution.get("passed") is False else "skipped", "details": execution},
                {"name": "semantic_evaluation", "status": "passed" if result.get("passed") else "failed", "details": {"score_10": result.get("overall_score_10")}},
            ]
            st.session_state.execution_results[model_name] = execution
            st.session_state.evaluation_results[model_name] = result

        st.session_state.pairwise_result = compare_outputs(
            task=st.session_state.latest_task,
            aya_output=outputs["aya_expanse"],
            llama_output=outputs["llama_scout"],
            reference_code=st.session_state.reference_code or None,
        )


def build_score_dataframe() -> pd.DataFrame:
    rows = []
    for metric_name in ("correctness", "readability", "best_practices"):
        rows.append({
            "Metric": metric_name.replace("_", " ").title(),
            "Aya Expanse": st.session_state.evaluation_results["aya_expanse"]["detailed_metrics"][metric_name]["score_10"],
            "Llama 4 Scout": st.session_state.evaluation_results["llama_scout"]["detailed_metrics"][metric_name]["score_10"],
        })
    rows.append({
        "Metric": "Overall Score",
        "Aya Expanse": st.session_state.evaluation_results["aya_expanse"]["overall_score_10"],
        "Llama 4 Scout": st.session_state.evaluation_results["llama_scout"]["overall_score_10"],
    })
    return pd.DataFrame(rows)


def show_validation(result: dict[str, Any]) -> None:
    validation = result.get("validation", {})
    execution = result.get("execution") or {}
    if not validation:
        return
    syntax = validation.get("syntax", {})
    security = validation.get("security", {})
    st.markdown("**Deterministic evidence**")
    st.write({
        "Files detected": validation.get("file_count", 1),
        "Lines": validation.get("line_count", 0),
        "Syntax": syntax.get("passed"),
        "Security scan": security.get("passed"),
        "Sandbox available": execution.get("available", False),
        "Sandbox executed": execution.get("executed", False),
        "Sandbox passed": execution.get("passed"),
        "Evidence level": "high" if execution.get("executed") else validation.get("evidence_level", "low"),
    })
    if security.get("message"):
        st.caption(security["message"])
    if syntax.get("message") and syntax.get("passed") is not None:
        st.caption(syntax["message"])
    if execution.get("message"):
        st.caption(execution["message"])


def show_agent_trace() -> None:
    steps = st.session_state.agent_steps
    if not any(steps.values()):
        return
    st.subheader("Agent Evaluation Trace")
    st.caption("Each candidate follows the same observable evaluation path: validation → isolated execution → semantic judge.")
    for model_name, model_steps in steps.items():
        st.markdown(f"**{MODEL_LABELS[model_name]}**")
        rows = []
        for step in model_steps:
            rows.append({"Step": step.name if hasattr(step, "name") else step["name"], "Status": step.status if hasattr(step, "status") else step["status"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def show_evaluation_results() -> None:
    results = st.session_state.evaluation_results
    if not results["aya_expanse"] or not results["llama_scout"]:
        return
    st.divider()
    st.header("Evaluation Results")
    st.caption("DeepEval uses a native 0–1 score; the dashboard displays it on a 0–10 scale.")
    if results["aya_expanse"].get("error") or results["llama_scout"].get("error"):
        st.error("One or more evaluations failed. Check the details below.")
        return

    result_df = build_score_dataframe()
    chart_df = result_df.melt(id_vars="Metric", var_name="Model", value_name="Score")
    fig = px.bar(chart_df, x="Metric", y="Score", color="Model", barmode="group",
                 range_y=[0, 10], labels={"Score": "Score (0–10)"},
                 title="Code Generation Quality Comparison")
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(result_df, hide_index=True, use_container_width=True)

    pairwise = st.session_state.pairwise_result or {}
    if pairwise.get("winner"):
        st.success(f"Pairwise judge winner: **{pairwise['winner']}**")
        st.caption(pairwise.get("reason", "No pairwise reasoning returned."))

    if st.session_state.latest_task and st.session_state.context:
        retrieved = build_retrieved_context(st.session_state.context.get("content", ""), st.session_state.latest_task)
        with st.expander("Retrieval evidence"):
            st.write({"Candidate files": retrieved["candidate_files"], "Selected files": len(retrieved["files"]), "Selected context characters": retrieved["total_chars"]})
            st.dataframe(pd.DataFrame(retrieved["files"]), hide_index=True, use_container_width=True)

    for model_name, result in results.items():
        st.subheader(MODEL_LABELS[model_name])
        show_validation(result)
        reasoning_rows = [
            {"Metric": metric.replace("_", " ").title(), "Score": values["score_10"], "Reasoning": values["reason"]}
            for metric, values in result.get("detailed_metrics", {}).items()
        ]
        st.dataframe(pd.DataFrame(reasoning_rows), hide_index=True, use_container_width=True)
        st.caption(result.get("confidence_note", "No confidence note available."))
        status = "PASS" if result.get("passed") else "FAIL"
        st.caption(f"Final status: **{status}** — LLM threshold 0.70 plus deterministic gates.")

    show_agent_trace()


initialize_state()

with st.sidebar:
    st.header("Repository Context")
    st.text_input("GitHub repository URL", placeholder="https://github.com/username/repository", key="github_repo")

    if st.button("Ingest Repository", use_container_width=True):
        try:
            with st.spinner("Reading repository..."):
                st.session_state.context = ingest_github_repo(st.session_state.github_repo)
            reset_run_state()
            st.success("Repository context is ready.")
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.header("Benchmark Task")
    try:
        benchmark_tasks = load_tasks()
        task_options = {f"{task.id} · {task.category}": task.task for task in benchmark_tasks}
        selected_task = st.selectbox("Use a reproducible task", ["Custom task", *task_options.keys()])
        if selected_task != "Custom task":
            st.session_state.latest_task = task_options[selected_task]
    except Exception as exc:
        st.warning(f"Benchmark tasks unavailable: {exc}")

    st.header("Evaluation")
    st.text_area("Reference implementation (optional)", height=180, key="reference_code")

st.title("LLM Code Generation Benchmark")
st.write("Compare repository-aware code generation, deterministic validation, isolated execution, and semantic judging across coding models.")

if st.session_state.context:
    with st.expander("Repository context", expanded=False):
        st.markdown(st.session_state.context.get("summary", "No summary available."))
        st.code(st.session_state.context.get("structure", ""), language="text")
else:
    st.info("Ingest a GitHub repository from the sidebar before generating code.")

show_generated_history()

if prompt := st.chat_input("Describe the code change you want..."):
    if not st.session_state.context:
        st.error("Ingest a GitHub repository before generating code.")
    else:
        st.session_state.latest_task = prompt
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            with st.chat_message("assistant"):
                aya_code, llama_code = asyncio.run(generate_code(prompt))
            st.session_state.last_generated_code = {"aya_expanse": aya_code, "llama_scout": llama_code}
            reset_run_state()
            st.session_state.chat_history.append({"role": "assistant", "content": "", "aya_response": aya_code, "llama_response": llama_code})
        except Exception as exc:
            st.error(f"Code generation failed: {exc}")

st.divider()
left, middle, right = st.columns(3)
with left:
    if st.button("Run Isolated Checks", use_container_width=True):
        run_sandbox_checks()
with middle:
    if st.button("Evaluate Latest", use_container_width=True):
        evaluate_latest()
with right:
    if st.button("Run Agent Evaluation", use_container_width=True):
        run_agent_evaluation()

show_evaluation_results()
