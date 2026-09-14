"""FastAPI web interface for the repository-aware code benchmark."""
from __future__ import annotations
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, AsyncIterator
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from benchmark.agent_loop import run_self_repair
from benchmark.agent_service import repair_with_model
from benchmark.evaluation import compare_outputs, evaluate_code
from benchmark.ingestion import ingest_github_repo
from benchmark.model_service import MODEL_CONFIG, get_parallel_responses
from benchmark.retrieval import build_retrieved_context
from benchmark.sandbox import clone_and_run
from benchmark.tasks import load_tasks

load_dotenv()
ROOT = Path(__file__).parent
app = FastAPI(title="AI Code Benchmark", version="0.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

class IngestRequest(BaseModel): repo_url: str
class GenerateRequest(BaseModel):
    task: str = Field(min_length=1)
    context: dict[str, Any]
class WorkRequest(BaseModel):
    repo_url: str | None = None
    task: str = Field(min_length=1)
    context: dict[str, Any]
    outputs: dict[str, str]
    executions: dict[str, Any] | None = None
    reference_code: str | None = None
    max_attempts: int = Field(default=2, ge=0, le=3)

def _context_text(context: dict[str, Any]) -> str:
    return f"Summary:\n{context.get('summary', '')}\n\nStructure:\n{context.get('structure', '')}"
def _required_outputs(outputs: dict[str, str]) -> None:
    if not all(isinstance(outputs.get(name), str) and outputs[name].strip() for name in MODEL_CONFIG): raise HTTPException(422, "Both generated model outputs are required.")

@app.get("/", include_in_schema=False)
async def home() -> FileResponse: return FileResponse(ROOT / "static" / "index.html")
@app.get("/api/health")
async def health() -> dict[str, Any]: return {"status":"ok", "models":{key:value["label"] for key,value in MODEL_CONFIG.items()}}
@app.get("/api/tasks")
async def tasks() -> list[dict[str, str]]:
    try: return [asdict(task) for task in load_tasks()]
    except Exception as exc: raise HTTPException(500, f"Benchmark tasks could not be loaded: {exc}") from exc
@app.post("/api/ingest")
async def ingest(payload: IngestRequest) -> dict[str, Any]:
    try: return await asyncio.to_thread(ingest_github_repo, payload.repo_url)
    except Exception as exc: raise HTTPException(400, str(exc)) from exc
@app.post("/api/generate")
async def generate(payload: GenerateRequest) -> StreamingResponse:
    if not payload.context.get("content"): raise HTTPException(422, "Ingest a repository before generating candidates.")
    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue(); completed = 0
        async def pump(name: str, stream: AsyncIterator[str]) -> None:
            try:
                async for chunk in stream: await queue.put((name, chunk))
            except Exception as exc: await queue.put(("error", json.dumps({"model":name,"message":str(exc)})))
            finally: await queue.put((name, None))
        try:
            qwen, nemotron = await get_parallel_responses(payload.task, payload.context)
            workers = [asyncio.create_task(pump("qwen", qwen)), asyncio.create_task(pump("nemotron", nemotron))]
            while completed < 2:
                name, chunk = await queue.get()
                if name == "error": yield f"event: error\ndata: {chunk}\n\n"
                elif chunk is None: completed += 1; yield f"event: model_done\ndata: {json.dumps({'model':name})}\n\n"
                else: yield f"event: chunk\ndata: {json.dumps({'model':name,'text':chunk})}\n\n"
            await asyncio.gather(*workers); yield "event: done\ndata: {}\n\n"
        except Exception as exc: yield f"event: error\ndata: {json.dumps({'message':str(exc)})}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})
@app.post("/api/evaluate")
async def evaluate(payload: WorkRequest) -> dict[str, Any]:
    _required_outputs(payload.outputs); context = _context_text(payload.context); executions = payload.executions or {}
    try:
        results = {name:await asyncio.to_thread(evaluate_code, output, payload.task, context, payload.reference_code, executions.get(name)) for name,output in payload.outputs.items()}
        pairwise = await asyncio.to_thread(compare_outputs, payload.task, payload.outputs["qwen"], payload.outputs["nemotron"], payload.reference_code)
        return {"results":results,"pairwise":pairwise}
    except Exception as exc: raise HTTPException(500, f"Evaluation failed: {exc}") from exc
@app.post("/api/sandbox")
async def sandbox(payload: WorkRequest) -> dict[str, Any]:
    _required_outputs(payload.outputs)
    if not payload.repo_url: raise HTTPException(422, "A GitHub repository URL is required for isolated checks.")
    try: return {"executions":{name:await asyncio.to_thread(clone_and_run,payload.repo_url,output) for name,output in payload.outputs.items()}}
    except Exception as exc: raise HTTPException(500, f"Isolated checks failed: {exc}") from exc
@app.post("/api/repair")
async def repair(payload: WorkRequest) -> dict[str, Any]:
    _required_outputs(payload.outputs)
    if not payload.repo_url: raise HTTPException(422, "A GitHub repository URL is required for self-repair.")
    runs: dict[str, Any] = {}
    try:
        for name, output in payload.outputs.items():
            async def repair_fn(prompt: str, model: str = name) -> str: return await repair_with_model(model, prompt)
            runs[name] = asdict(await run_self_repair(task=payload.task, repository_context=_context_text(payload.context), initial_output=output, repo_url=payload.repo_url, repair_fn=repair_fn, max_attempts=payload.max_attempts))
        return {"repairs":runs,"outputs":{name:run["best_output"] for name,run in runs.items()},"executions":{name:run["best_execution"] for name,run in runs.items()}}
    except Exception as exc: raise HTTPException(500, f"Self-repair failed: {exc}") from exc
@app.post("/api/retrieval")
async def retrieval(payload: GenerateRequest) -> dict[str, Any]:
    if not payload.context.get("content"): raise HTTPException(422, "Ingest a repository before viewing retrieval.")
    data = build_retrieved_context(payload.context["content"], payload.task)
    return {"candidate_files":data["candidate_files"],"selected_files":len(data["files"]),"total_chars":data["total_chars"],"files":[item.get("path","") for item in data["files"]]}
