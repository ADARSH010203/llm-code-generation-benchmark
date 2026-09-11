"""Deterministic checks for generated code before LLM-based judging."""

from __future__ import annotations

import ast
import re
from collections import Counter
from html.parser import HTMLParser
from typing import Any

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]{20,}"),
)
FILE_BLOCK_PATTERN = re.compile(
    r"FILE\s*:\s*(?P<path>[^\n]+)\n(?P<code>```[^\n]*\n.*?```)",
    re.IGNORECASE | re.DOTALL,
)


class _HTMLValidator(HTMLParser):
    """Lightweight HTML parser used as a structural syntax check."""

    def __init__(self) -> None:
        super().__init__()
        self.error_message: str | None = None

    def error(self, message: str) -> None:
        self.error_message = message


def _extract_python_code(code: str) -> str:
    cleaned = code.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return cleaned.strip()


def _find_file_blocks(output: str) -> list[dict[str, str]]:
    """Extract the structured multi-file format supported by the prompt."""
    files: list[dict[str, str]] = []
    for match in FILE_BLOCK_PATTERN.finditer(output):
        block = match.group("code").strip()
        lines = block.splitlines()
        language = lines[0].removeprefix("```").strip().lower() if lines else ""
        source = "\n".join(lines[1:-1]) if len(lines) >= 2 else ""
        files.append(
            {
                "path": match.group("path").strip(),
                "language": language,
                "code": source,
            }
        )
    return files


def _python_check(code: str) -> dict[str, Any]:
    source = _extract_python_code(code)
    try:
        tree = ast.parse(source)
        compile(tree, "<generated>", "exec")
        return {"passed": True, "message": "Python syntax and compilation checks passed."}
    except (SyntaxError, ValueError, TypeError) as exc:
        return {"passed": False, "message": f"Python validation failed: {exc}"}


def _html_check(code: str) -> dict[str, Any]:
    parser = _HTMLValidator()
    try:
        parser.feed(code)
        parser.close()
    except Exception as exc:
        return {"passed": False, "message": f"HTML parsing failed: {exc}"}
    if parser.error_message:
        return {"passed": False, "message": parser.error_message}
    return {"passed": True, "message": "HTML parser check passed."}


def _secret_check(output: str) -> dict[str, Any]:
    matches = sum(len(pattern.findall(output)) for pattern in SECRET_PATTERNS)
    return {
        "passed": matches == 0,
        "message": "No obvious hard-coded credential patterns detected."
        if matches == 0
        else "Potential hard-coded credential pattern detected.",
    }


def validate_generated_output(output: str) -> dict[str, Any]:
    """Run deterministic validation without executing untrusted generated code."""
    output = output.strip()
    lines = output.count("\n") + 1 if output else 0
    file_blocks = _find_file_blocks(output)

    checks: dict[str, Any] = {
        "line_count": lines,
        "file_count": len(file_blocks) or 1,
        "execution_verified": False,
        "tests_executed": False,
        "security": _secret_check(output),
        "syntax": {"passed": None, "message": "No language-specific syntax check applied."},
    }

    if file_blocks:
        language_results: list[dict[str, Any]] = []
        for file in file_blocks:
            suffix = file["path"].rsplit(".", 1)[-1].lower() if "." in file["path"] else ""
            if suffix == "py" or file["language"] in {"python", "py"}:
                result = _python_check(file["code"])
            elif suffix in {"html", "htm"} or file["language"] in {"html", "xml"}:
                result = _html_check(file["code"])
            else:
                result = {
                    "passed": None,
                    "message": "Static syntax check not configured for this file type.",
                }
            language_results.append({"path": file["path"], **result})

        checks["syntax"] = {
            "passed": all(item["passed"] is not False for item in language_results),
            "files": language_results,
        }
    else:
        python_markers = (
            "def ", "import ", "from ", "class ", "if __name__", "async def ",
        )
        looks_like_python = any(marker in output for marker in python_markers)
        if looks_like_python:
            checks["syntax"] = _python_check(output)

    checks["evidence_level"] = _evidence_level(checks)
    checks["validation_score"] = _validation_score(checks)
    return checks


def _evidence_level(checks: dict[str, Any]) -> str:
    """Describe how much deterministic evidence supports the generated output."""
    if checks["execution_verified"] or checks["tests_executed"]:
        return "high"
    if checks["syntax"].get("passed") is True and checks["security"]["passed"]:
        return "medium"
    return "low"


def _validation_score(checks: dict[str, Any]) -> float:
    """Return a deterministic validation signal, not a probability of correctness."""
    components = []

    syntax_passed = checks["syntax"].get("passed")
    if syntax_passed is not None:
        components.append(1.0 if syntax_passed else 0.0)

    components.append(1.0 if checks["security"]["passed"] else 0.0)
    return round(sum(components) / len(components), 2) if components else 0.0
