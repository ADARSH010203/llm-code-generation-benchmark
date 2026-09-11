"""Lightweight repository-aware retrieval for coding tasks.

The project uses GitIngest for repository collection and a small lexical ranker
here to choose the most relevant file sections before sending context to an LLM.
This keeps the dependency footprint small while avoiding a full-repository dump.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_FILES = 24
MAX_CHARS_PER_FILE = 9_000
MAX_TOTAL_CHARS = 70_000


@dataclass(frozen=True)
class FileChunk:
    path: str
    content: str
    score: float


def _tokens(text: str) -> set[str]:
    """Return simple normalized tokens used by the lexical ranker."""
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_./-]{1,}", text)
        if len(token) > 1
    }


def _split_files(content: str) -> list[tuple[str, str]]:
    """Split common GitIngest file sections into path/content pairs.

    GitIngest output is intentionally human/LLM friendly rather than an API
    contract for a structured AST. The parser therefore supports the common
    `path` heading style and falls back to one undivided chunk when needed.
    """
    lines = content.splitlines()
    sections: list[tuple[str, str]] = []
    current_path: str | None = None
    current: list[str] = []

    path_pattern = re.compile(r"^(?:#+\s*)?(?:file|path)\s*:?\s*`?([^`]+)`?\s*$", re.I)
    fence_path_pattern = re.compile(r"^={3,}\s*(.+?)\s*={3,}$")

    for line in lines:
        match = path_pattern.match(line.strip()) or fence_path_pattern.match(line.strip())
        if match:
            if current_path is not None:
                sections.append((current_path, "\n".join(current).strip()))
            current_path = match.group(1).strip()
            current = []
            continue
        current.append(line)

    if current_path is not None:
        sections.append((current_path, "\n".join(current).strip()))

    if not sections:
        return [("repository", content.strip())]
    return [(path, text) for path, text in sections if text]


def rank_relevant_files(content: str, task: str, limit: int = MAX_FILES) -> list[FileChunk]:
    """Rank repository sections against a coding task using lexical overlap."""
    query_terms = _tokens(task)
    ranked: list[FileChunk] = []

    for path, file_content in _split_files(content):
        path_terms = _tokens(path)
        content_terms = _tokens(file_content[:30_000])

        score = 0.0
        score += 4.0 * len(query_terms & path_terms)
        score += 1.5 * len(query_terms & content_terms)

        # Prefer code/config files over generated or documentation-heavy files.
        lower_path = path.lower()
        if any(lower_path.endswith(ext) for ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs")):
            score += 1.0
        if lower_path in {"package.json", "pyproject.toml", "requirements.txt", "dockerfile"}:
            score += 1.5

        ranked.append(
            FileChunk(
                path=path,
                content=file_content[:MAX_CHARS_PER_FILE],
                score=score,
            )
        )

    ranked.sort(key=lambda item: (-item.score, item.path.lower()))
    return ranked[:limit]


def build_retrieved_context(content: str, task: str) -> dict[str, object]:
    """Build bounded, task-focused context while retaining repository metadata."""
    chunks = rank_relevant_files(content, task)
    selected: list[str] = []
    total = 0

    for chunk in chunks:
        section = f"FILE: {chunk.path}\n{chunk.content}\n"
        if total + len(section) > MAX_TOTAL_CHARS:
            break
        selected.append(section)
        total += len(section)

    return {
        "files": [{"path": item.path, "score": round(item.score, 2)} for item in chunks],
        "content": "\n".join(selected),
        "total_chars": total,
        "candidate_files": len(_split_files(content)),
    }
