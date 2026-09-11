"""Repository ingestion utilities."""

from typing import Any

from gitingest import ingest


def ingest_github_repo(repo_url: str) -> dict[str, Any]:
    """Read a GitHub repository and return context for code generation.

    The ingestion layer deliberately keeps the repository summary, file
    structure, and source content separate so the model can use both the
    high-level architecture and the actual implementation details.
    """
    repo_url = repo_url.strip()
    if not repo_url:
        raise ValueError("Repository URL cannot be empty.")

    try:
        summary, structure, content = ingest(repo_url)
    except Exception as exc:
        raise RuntimeError(f"Unable to ingest repository: {exc}") from exc

    return {
        "summary": summary,
        "structure": structure,
        "content": content,
    }
