"""Streamlit interface for repository-aware LLM code benchmarking."""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from code_evaluation import compare_outputs, evaluate_code
from code_ingestion import ingest_github_repo
from model_service import get_parallel_responses

load_dotenv()

st.set_page_config(
    page_title="LLM Code Generation Benchmark",
    page_icon="🤖",
    layout="wide",
)

MODEL_LABELS = {
    "aya_expanse": "Cohere Aya Expanse",
    "llama_scout": "Meta Llama 4 Scout",
}


def initialize_state() -> None:
    """Create values that need to survive Streamlit reruns."""
    defaults: dict[str, Any] = {
        "chat_history": [],
        "context": None,
        "reference_code": "",
        "latest_task": "",
        "last_generated_code": {"aya_expanse": None, "llama_scout": None},
        "evaluation_results": {"aya_expanse": None, "llama_scout": None},
        "pairwise_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


async def consume_stream(stream: Any, placeholder: Any) -> str:
    """Consume a model stream and update the visible output incrementally."""
    output = ""
    async for chunk in stream:
        output += chunk
        placeholder.code(output.strip(), language="text")
    return output.strip()


async def generate_code(task: str) -> tuple[str, str]:
    """Run both model generations concurrently with identical inputs."""
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
    """Render completed generations from the current session."""
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
    """Return bounded context for the evaluator without duplicating the full prompt."""
    context = st.session_state.context or {}
    summary = context.get("summary", "")
    structure = context.get("structure", "")
    return f"Summary:\n{summary}\n\nStructure:\n{structure}"


def evaluate_latest() -> None:
    """Run per-model evaluation and a direct pairwise comparison."""
    outputs = st.session_state.last_generated_code
    if not outputs["aya_expanse"] or not outputs["llama_scout"]:
        st.error("Generate code with both models before evaluating it.")
        return
    if not st.session_state.latest_task:
        st.error("The latest coding task is missing.")
        return

    with st.spinner("Running validation and model comparison..."):
        for model_name, code in outputs.items():
            st.session_state.evaluation_results[model_name] = evaluate_code(
                generated_code=code,
                task=st.session_state.latest_task,
                repository_context=_repository_eval_context(),
                reference_code=st.session_state.reference_code or None,
            )

        st.session_state.pairwise_result = compare_outputs(
            task=st.session_state.latest_task,
            aya_output=outputs["aya_expanse"],
            llama_output=outputs["llama_scout"],
            reference_code=st.session_state.reference_code or None,
        )


def build_score_dataframe() -> pd.DataFrame:
    """Build the user-facing 0–10 score table."""
    rows = []
    for metric_name in ("correctness", "readability", "best_practices"):
        rows.append(
            {
                "Metric": metric_name.replace("_", " ").title(),
                "Aya Expanse": st.session_state.evaluation_results["aya_expanse"][
                    "detailed_metrics"
                ][metric_name]["score_10"],
                "Llama 4 Scout": st.session_state.evaluation_results["llama_scout"][
                    "detailed_metrics"
                ][metric_name]["score_10"],
            }
        )

    rows.append(
        {
            "Metric": "Overall Score",
            "Aya Expanse": st.session_state.evaluation_results["aya_expanse"][
                "overall_score_10"
            ],
            "Llama 4 Scout": st.session_state.evaluation_results["llama_scout"][
                "overall_score_10"
            ],
        }
    )
    return pd.DataFrame(rows)


def show_validation(result: dict[str, Any]) -> None:
    """Show static evidence separately from subjective LLM judging."""
    validation = result.get("validation", {})
    if not validation:
        return

    syntax = validation.get("syntax", {})
    security = validation.get("security", {})
    st.markdown("**Deterministic validation**")
    st.write(
        {
            "Files detected": validation.get("file_count", 1),
            "Lines": validation.get("line_count", 0),
            "Syntax": syntax.get("passed"),
            "Security scan": security.get("passed"),
            "Execution verified": validation.get("execution_verified", False),
            "Tests executed": validation.get("tests_executed", False),
            "Evidence level": validation.get("evidence_level", "low"),
        }
    )
    if validation.get("redactions", 0):
        st.caption("Some repository credentials were redacted before model evaluation.")

    if security.get("message"):
        st.caption(security["message"])
    if syntax.get("message") and syntax.get("passed") is not None:
        st.caption(syntax["message"])


def show_evaluation_results() -> None:
    """Render score, validation evidence, and pairwise winner."""
    results = st.session_state.evaluation_results
    if not results["aya_expanse"] or not results["llama_scout"]:
        return

    st.divider()
    st.header("Evaluation Results")
    st.caption("DeepEval keeps metric scores in 0–1; this dashboard displays them on a 0–10 scale.")

    if results["aya_expanse"].get("error") or results["llama_scout"].get("error"):
        st.error("One or more evaluations failed. Check the details below.")
        return

    result_df = build_score_dataframe()
    chart_df = result_df.melt(id_vars="Metric", var_name="Model", value_name="Score")
    fig = px.bar(
        chart_df,
        x="Metric",
        y="Score",
        color="Model",
        barmode="group",
        range_y=[0, 10],
        labels={"Score": "Score (0–10)"},
        title="Code Generation Quality Comparison",
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(result_df, hide_index=True, use_container_width=True)

    pairwise = st.session_state.pairwise_result or {}
    if pairwise.get("winner"):
        st.success(f"Pairwise judge winner: **{pairwise['winner']}**")
        st.caption(pairwise.get("reason", "No pairwise reasoning returned."))
    else:
        st.info(pairwise.get("reason", "Pairwise comparison is unavailable."))

    for model_name, result in results.items():
        st.subheader(MODEL_LABELS[model_name])
        show_validation(result)

        reasoning_rows = [
            {
                "Metric": metric.replace("_", " ").title(),
                "Score": values["score_10"],
                "Reasoning": values["reason"],
            }
            for metric, values in result.get("detailed_metrics", {}).items()
        ]
        st.dataframe(pd.DataFrame(reasoning_rows), hide_index=True, use_container_width=True)

        st.caption(result.get("confidence_note", "No confidence note available."))
        status = "PASS" if result.get("passed") else "FAIL"
        st.caption(f"LLM-judge status: **{status}** at a 0.70 native DeepEval threshold.")


initialize_state()

with st.sidebar:
    st.header("Repository Context")
    github_repo = st.text_input(
        "GitHub repository URL",
        placeholder="https://github.com/username/repository",
    )

    if st.button("Ingest Repository", use_container_width=True):
        try:
            with st.spinner("Reading repository..."):
                st.session_state.context = ingest_github_repo(github_repo)
            st.session_state.evaluation_results = {"aya_expanse": None, "llama_scout": None}
            st.session_state.pairwise_result = None
            st.success("Repository context is ready.")
            if st.session_state.context.get("redactions", 0):
                st.warning("Potential credentials were redacted from repository context before model use.")
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.header("Evaluation")
    st.text_area(
        "Reference implementation (optional)",
        height=180,
        key="reference_code",
        help="Reference code gives the correctness judge stronger behavioral evidence.",
    )

st.title("LLM Code Generation Benchmark")
st.write(
    "Compare Aya Expanse and Llama 4 Scout on the same repository-aware coding task, "
    "then separate static evidence from LLM-based quality judgment."
)

if st.session_state.context:
    context = st.session_state.context
    with st.expander("Repository context", expanded=False):
        st.markdown(context.get("summary", "No summary available."))
        st.code(context.get("structure", ""), language="text")
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

            st.session_state.last_generated_code = {
                "aya_expanse": aya_code,
                "llama_scout": llama_code,
            }
            st.session_state.evaluation_results = {"aya_expanse": None, "llama_scout": None}
            st.session_state.pairwise_result = None
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": "",
                    "aya_response": aya_code,
                    "llama_response": llama_code,
                }
            )
        except Exception as exc:
            st.error(f"Code generation failed: {exc}")

st.divider()
if st.button("Evaluate Latest Generation"):
    evaluate_latest()

show_evaluation_results()
