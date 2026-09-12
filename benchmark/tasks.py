"""Benchmark task loading and normalization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkTask:
    """A reproducible task used by the benchmark harness."""

    id: str
    category: str
    language: str
    task: str


def load_tasks(path: str | Path = "data/benchmark_tasks.json") -> list[BenchmarkTask]:
    """Load and validate benchmark tasks from JSON."""
    source = Path(path)
    payload: Any = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Benchmark task file must contain a JSON list.")

    tasks: list[BenchmarkTask] = []
    seen_ids: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each benchmark task must be a JSON object.")
        required = ("id", "category", "language", "task")
        if any(not isinstance(item.get(key), str) or not item[key].strip() for key in required):
            raise ValueError(f"Invalid benchmark task: {item!r}")
        task = BenchmarkTask(
            id=item["id"].strip(),
            category=item["category"].strip(),
            language=item["language"].strip(),
            task=item["task"].strip(),
        )
        if task.id in seen_ids:
            raise ValueError(f"Duplicate benchmark task id: {task.id}")
        seen_ids.add(task.id)
        tasks.append(task)
    return tasks


def get_task(task_id: str, path: str | Path = "data/benchmark_tasks.json") -> BenchmarkTask:
    """Return one benchmark task by stable id."""
    for task in load_tasks(path):
        if task.id == task_id:
            return task
    raise KeyError(f"Unknown benchmark task: {task_id}")
