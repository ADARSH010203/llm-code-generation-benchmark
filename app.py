"""Streamlit dashboard for repository-aware AI coding benchmark."""
from __future__ import annotations
import asyncio
from typing import Any
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from benchmark.agent_loop import run_self_repair
from benchmark.agent_service import repair_with_model
from benchmark.evaluation import compare_outputs, evaluate_code
from benchmark.ingestion import ingest_github_repo
from benchmark.model_service import MODEL_CONFIG, get_parallel_responses
from benchmark.retrieval import build_retrieved_context
from benchmark.sandbox import clone_and_run
from benchmark.tasks import load_tasks
load_dotenv()
st.set_page_config(page_title="AI Code Benchmark", page_icon="🤖", layout="wide")
LABELS = {k: v["label"] for k, v in MODEL_CONFIG.items()}

def state() -> None:
    defaults = {"context": None, "task": "", "outputs": {k: None for k in MODEL_CONFIG}, "results": {k: None for k in MODEL_CONFIG}, "executions": {k: None for k in MODEL_CONFIG}, "repairs": {k: None for k in MODEL_CONFIG}}
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

async def consume(stream, placeholder) -> str:
    text = ""
    async for chunk in stream:
        text += chunk; placeholder.code(text, language="text")
    return text.strip()

async def generate(task: str):
    first, second = await get_parallel_responses(task, st.session_state.context)
    c1, c2 = st.columns(2)
    with c1: st.subheader(LABELS["qwen"]); p1 = st.empty()
    with c2: st.subheader(LABELS["nemotron"]); p2 = st.empty()
    return await asyncio.gather(consume(first, p1), consume(second, p2))

def reset():
    st.session_state.results = {k: None for k in MODEL_CONFIG}; st.session_state.executions = {k: None for k in MODEL_CONFIG}; st.session_state.repairs = {k: None for k in MODEL_CONFIG}

def eval_latest():
    for k, code in st.session_state.outputs.items():
        st.session_state.results[k] = evaluate_code(code, st.session_state.task, _ctx(), execution_result=st.session_state.executions[k])
    st.session_state.pairwise = compare_outputs(st.session_state.task, st.session_state.outputs["qwen"], st.session_state.outputs["nemotron"])

def _ctx():
    c = st.session_state.context or {}; return f"Summary:\n{c.get('summary','')}\n\nStructure:\n{c.get('structure','')}"

def repair():
    repo = st.session_state.get("repo", "")
    if not repo: st.error("Enter a GitHub repository URL first."); return
    budget = st.session_state.max_repair_attempts
    for k, code in st.session_state.outputs.items():
        async def fn(prompt: str, model=k): return await repair_with_model(model, prompt)
        run = asyncio.run(run_self_repair(task=st.session_state.task, repository_context=_ctx(), initial_output=code, repo_url=repo, repair_fn=fn, max_attempts=budget))
        st.session_state.repairs[k] = run; st.session_state.outputs[k] = run.best_output; st.session_state.executions[k] = run.best_execution
    eval_latest()

state()
with st.sidebar:
    st.header("Repository")
    st.text_input("GitHub repository URL", key="repo", placeholder="https://github.com/user/repo")
    if st.button("Ingest Repository", use_container_width=True):
        st.session_state.context = ingest_github_repo(st.session_state.repo); reset(); st.success("Repository loaded.")
    st.header("Benchmark Task")
    try:
        tasks = load_tasks(); choices = {f"{t.id} · {t.category}": t.task for t in tasks}; picked = st.selectbox("Reproducible task", ["Custom task", *choices])
        if picked != "Custom task": st.session_state.task = choices[picked]
    except Exception as exc: st.warning(f"Task suite unavailable: {exc}")
    st.slider("Max repair attempts", 0, 3, 2, key="max_repair_attempts")
    st.text_area("Reference implementation (optional)", key="reference_code", height=140)

st.title("Repository-Aware AI Code Benchmark")
st.caption("Qwen 3.6 27B on Groq vs NVIDIA Nemotron 3 Super 120B A12B on OpenRouter")
if st.session_state.context:
    with st.expander("Repository context"): st.code(st.session_state.context.get("structure", ""), language="text")
else: st.info("Ingest a repository to begin.")
if prompt := st.chat_input("Describe the code change..."):
    st.session_state.task = prompt
    if not st.session_state.context: st.error("Ingest a repository first.")
    else:
        try:
            q, n = asyncio.run(generate(prompt)); st.session_state.outputs = {"qwen": q, "nemotron": n}; reset(); st.success("Both candidates generated.")
        except Exception as exc: st.error(f"Generation failed: {exc}")

cols = st.columns(4)
if cols[0].button("Validate + Judge", use_container_width=True): eval_latest()
if cols[1].button("Isolated Checks", use_container_width=True):
    if st.session_state.repo:
        for k, code in st.session_state.outputs.items(): st.session_state.executions[k] = clone_and_run(st.session_state.repo, code)
        eval_latest()
if cols[2].button("Self-Repair & Re-test", use_container_width=True): repair()
if cols[3].button("Show Retrieval", use_container_width=True):
    if st.session_state.context:
        r = build_retrieved_context(st.session_state.context.get("content", ""), st.session_state.task); st.json({"candidate_files": r["candidate_files"], "selected_files": len(r["files"]), "total_chars": r["total_chars"]})

r = st.session_state.results
if all(r.values()):
    st.divider(); st.header("Evaluation Results")
    rows = []
    for metric in ("correctness", "readability", "best_practices"):
        rows.append({"Metric": metric.title(), "Qwen 3.6 27B": r["qwen"]["detailed_metrics"][metric]["score_10"], "Nemotron 3 Super": r["nemotron"]["detailed_metrics"][metric]["score_10"]})
    rows.append({"Metric": "Overall", "Qwen 3.6 27B": r["qwen"]["overall_score_10"], "Nemotron 3 Super": r["nemotron"]["overall_score_10"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if getattr(st.session_state, "pairwise", {}).get("winner"): st.success(f"Pairwise winner: {st.session_state.pairwise['winner']}")
    for k, run in st.session_state.repairs.items():
        if run: st.write({"model": LABELS[k], "attempts": len(run.attempts), "result": "PASS" if run.passed else "BEST-EFFORT", "reason": run.stopped_reason})
