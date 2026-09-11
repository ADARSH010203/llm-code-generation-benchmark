"""GitHub repository ingestion and lightweight context sanitization."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from gitingest import ingest

GITHUB_HOSTS = {"github.com", "www.github.com"}

_SECRET_VALUE_PATTERNS = (
    re.compile(
        r"(?i)(api[_-]?key|access[_-]?token|secret[_-]?key|password)\s*([:=])\s*(['\"]).+?\3"
    ),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.DOTALL),
)


def _validate_github_url(repo_url: str) -> None:
    parsed = urlparse(repo_url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in GITHUB_HOSTS:
        raise ValueError("Enter a valid github.com repository URL.")
    if not parsed.path.strip("/"):
        raise ValueError("Enter a GitHub repository URL, not the GitHub home page.")


def _redact_sensitive_content(content: str) -> tuple[str, int]:
    """Replace obvious credential values before they reach an LLM provider."""
    redactions = 0
    sanitized = content

    for pattern in _SECRET_VALUE_PATTERNS:
        sanitized, count = pattern.subn(
            lambda match: f"{match.group(1)}{match.group(2)}\"[REDACTED]\""
            if match.lastindex and match.lastindex >= 2
            else "[REDACTED_CREDENTIAL]",
            sanitized,
        )
        redactions += count

    return sanitized, redactions


def ingest_github_repo(repo_url: str) -> dict[str, Any]:
    """Read a public GitHub repository and return sanitized model context."""
    repo_url = repo_url.strip()
    if not repo_url:
        raise ValueError("Repository URL cannot be empty.")

    _validate_github_url(repo_url)

    try:
        summary, structure, content = ingest(repo_url)
    except Exception as exc:
        raise RuntimeError(f"Unable to ingest repository: {exc}") from exc

    safe_content, redaction_count = _redact_sensitive_content(content)
    return {
        "summary": summary,
        "structure": structure,
        "content": safe_content,
        "redactions": redaction_count,
    }
