"""Streamlit interface for comparing LLM code generation."""

import asyncio
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from code_evaluation import evaluate_code
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
    """Create session state values used by the application."""
    defaults: dict[str, Any] = {
        "chat_history": [],
        "context": None,
        "reference_code": "",
        "last_generated_code": {
            "aya_expanse": None,
            "llama_scout": None,
        },
        "evaluation_results": {
            "aya_expanse": None,
            "llama_scout": None,
        },
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clean_generated_code(text: str) -> str:
    """Remove common Markdown code fences from a model response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


async def _consume_stream(stream: Any, placeholder: Any) -> str:
    """Consume one model stream and update its UI placeholder."""
    response = ""
    async for chunk in stream:
        response += chunk
        placeholder.code(clean_generated_code(response), language="python")
    return clean_generated_code(response)


async def generate_code(task: str) -> tuple[str, str]:
    """Generate code concurrently with both benchmark models."""
    llama_stream, aya_stream = await get_parallel_responses(
        task,
        st.session_state.context,
    )

    with st.container():
        aya_column, llama_column = st.columns(2)
        with aya_column:
            st.subheader(MODEL_LABELS["aya_expanse"])
            aya_placeholder = st.empty()
        with llama_column:
            st.subheader(MODEL_LABELS["llama_scout"])
            llama_placeholder = st.empty()

    llama_code, aya_code = await asyncio.gather(
        _consume_stream(llama_stream, llama_placeholder),
        _consume_stream(aya_stream, aya_placeholder),
    )
    return aya_code, llama_code


def show_generated_results() -> None:
    """Render previous model outputs from the current session."""
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
            continue

        with st.chat_message("assistant"):
            aya_column, llama_column = st.columns(2)
            with aya_column:
                st.subheader(MODEL_LABELS["aya_expanse"])
                st.code(message["aya_response"], language="python")
            with llama_column:
                st.subheader(MODEL_LABELS["llama_scout"])
                st.code(message["llama_response"], language="python")


def evaluate_generated_code(task: str) -> None:
    """Evaluate the latest output from both models."""
    outputs = st.session_state.last_generated_code
    if not outputs["aya_expanse"] or not outputs["llama_scout"]:
        st.error("Generate code with both models before running an evaluation.")
        return

    with st.spinner("Evaluating both implementations..."):
        for model_name, code in outputs.items():
            st.session_state.evaluation_results[model_name] = evaluate_code(
                generated_code=code,
                task=task,
                reference_code=st.session_state.reference_code or None,
            )


def build_results_dataframe() -> pd.DataFrame:
    """Create a compact table for side-by-side model comparison."""
    rows = []
    for metric_name in ("correctness", "readability", "best_practices"):
        rows.append(
            {
                "Metric": metric_name.replace("_", " ").title(),
                "Aya Expanse": st.session_state.evaluation_results["aya_expanse"][
                    "detailed_metrics"
                ][metric_name]["score"],
                "Llama 4 Scout": st.session_state.evaluation_results["llama_scout"][
                    "detailed_metrics"
                ][metric_name]["score"],
            }
        )

    rows.append(
        {
            "Metric": "Overall Score",
            "Aya Expanse": st.session_state.evaluation_results["aya_expanse"][
                "overall_score"
            ],
            "Llama 4 Scout": st.session_state.evaluation_results["llama_scout"][
                "overall_score"
            ],
        }
    )
    return pd.DataFrame(rows)


def show_evaluation_results() -> None:
    """Render scores and evaluator reasoning."""
    results = st.session_state.evaluation_results
    if not results["aya_expanse"] or not results["llama_scout"]:
        return

    if results["aya_expanse"].get("error") or results["llama_scout"].get("error"):
        st.error("One or more evaluations failed. Check the evaluation details below.")

    st.divider()
    st.header("Evaluation Results")
    st.caption("Scores are produced by an LLM-as-a-judge evaluation using DeepEval.")

    result_df = build_results_dataframe()
    chart_df = result_df.melt(
        id_vars="Metric",
        var_name="Model",
        value_name="Score",
    )

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

    st.dataframe(
        result_df.style.format(
            {"Aya Expanse": "{:.2f}", "Llama 4 Scout": "{:.2f}"}
        ),
        hide_index=True,
        use_container_width=True,
    )

    for model_name, result in results.items():
        st.subheader(f"{MODEL_LABELS[model_name]} — evaluator reasoning")
        if result.get("error"):
            st.error(result["error"])
            continue

        details = result.get("detailed_metrics", {})
        reasoning_rows = [
            {
                "Metric": metric.replace("_", " ").title(),
                "Score": values["score"],
                "Reasoning": values["reason"],
            }
            for metric, values in details.items()
        ]
        st.dataframe(
            pd.DataFrame(reasoning_rows).style.format({"Score": "{:.2f}"}),
            hide_index=True,
            use_container_width=True,
        )

        status = "Passed" if result.get("passed") else "Below threshold"
        st.caption(f"Evaluation status: **{status}** (threshold: 7.0 / 10).")


initialize_state()

with st.sidebar:
    st.header("Repository Context")
    github_repo = st.text_input(
        "GitHub repository URL",
        placeholder="https://github.com/username/repository",
    )

    if st.button("Ingest Repository", use_container_width=True):
        if not github_repo.strip():
            st.error("Enter a GitHub repository URL first.")
        else:
            with st.spinner("Reading repository..."):
                try:
                    st.session_state.context = ingest_github_repo(github_repo)
                    st.session_state.evaluation_results = {
                        "aya_expanse": None,
                        "llama_scout": None,
                    }
                    st.success("Repository context is ready.")
                except Exception as exc:
                    st.error(str(exc))

    st.divider()
    st.header("Evaluation")
    st.session_state.reference_code = st.text_area(
        "Reference implementation (optional)",
        value=st.session_state.reference_code,
        height=180,
        help="A reference implementation improves correctness evaluation.",
    )

st.title("LLM Code Generation Benchmark")
st.write(
    "Generate repository-aware code with two LLMs and compare the results "
    "using the same task, repository context, and evaluation criteria."
)

if st.session_state.context:
    with st.expander("Repository context", expanded=False):
        st.markdown(st.session_state.context.get("summary", "No summary available."))
        st.code(st.session_state.context.get("structure", ""), language="text")
else:
    st.info("Ingest a GitHub repository from the sidebar before generating code.")

show_generated_results()

if prompt := st.chat_input("Describe the code you want to generate..."):
    if not st.session_state.context:
        st.error("Ingest a GitHub repository before generating code.")
    else:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        try:
            with st.chat_message("assistant"):
                aya_code, llama_code = asyncio.run(generate_code(prompt))

            st.session_state.last_generated_code = {
                "aya_expanse": aya_code,
                "llama_scout": llama_code,
            }
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": "",
                    "aya_response": aya_code,
                    "llama_response": llama_code,
                }
            )
            st.session_state.evaluation_results = {
                "aya_expanse": None,
                "llama_scout": None,
            }
        except Exception as exc:
            st.error(f"Code generation failed: {exc}")

st.divider()
if st.button("Evaluate Latest Generation", use_container_width=False):
    latest_task = ""
    for message in reversed(st.session_state.chat_history):
        if message["role"] == "user":
            latest_task = message["content"]
            break

    if latest_task:
        evaluate_generated_code(latest_task)
    else:
        st.error("Generate code before running an evaluation.")

show_evaluation_results()
