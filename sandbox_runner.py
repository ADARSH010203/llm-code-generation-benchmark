"""Optional isolated execution for generated multi-file code.

The runner is deliberately conservative: Docker is required, networking is
blocked by default, resources are capped, and generated code is never run on
the host Python process.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "45"))
MAX_OUTPUT_CHARS = 12_000


def _safe_relative_path(path: str) -> Path:
    """Reject paths that could escape the temporary workspace."""
    candidate = Path(path.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe generated path: {path}")
    return candidate


def parse_generated_files(output: str) -> list[dict[str, str]]:
    """Parse the FILE: path + fenced code format emitted for multi-file tasks."""
    pattern = re.compile(
        r"FILE:\s*(?P<path>[^\n]+)\n```(?P<language>[^\n]*)\n(?P<code>.*?)\n```",
        re.IGNORECASE | re.DOTALL,
    )
    return [
        {
            "path": match.group("path").strip(),
            "language": match.group("language").strip().lower(),
            "code": match.group("code"),
        }
        for match in pattern.finditer(output)
    ]


def _detect_commands(root: Path) -> list[list[str]]:
    """Detect conservative repository checks without inventing commands."""
    commands: list[list[str]] = []
    if (root / "pytest.ini").exists() or (root / "tests").is_dir() or (root / "pyproject.toml").exists():
        if shutil.which("python"):
            commands.append(["python", "-m", "compileall", "-q", "."])

    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "test" in scripts:
                commands.append(["npm", "test", "--", "--runInBand"])
            elif "build" in scripts:
                commands.append(["npm", "run", "build"])
        except (OSError, json.JSONDecodeError):
            pass

    return commands


def run_generated_workspace(
    generated_output: str,
    base_repository: str | os.PathLike[str] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Run generated code in a Docker sandbox when Docker is available.

    The function returns evidence only; it never treats a passing command as
    proof of full application correctness. Network access is disabled and the
    container is removed after execution.
    """
    docker = shutil.which("docker")
    files = parse_generated_files(generated_output)
    if not files:
        return {
            "available": bool(docker),
            "executed": False,
            "passed": None,
            "message": "No multi-file generated workspace was detected.",
        }
    if not docker:
        return {
            "available": False,
            "executed": False,
            "passed": None,
            "message": "Docker is not installed; isolated execution was skipped.",
        }

    with tempfile.TemporaryDirectory(prefix="llm-benchmark-") as temp_dir:
        root = Path(temp_dir)

        if base_repository:
            source_root = Path(base_repository).resolve()
            if source_root.exists():
                shutil.copytree(source_root, root / "repo", dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules"))
                workspace = root / "repo"
            else:
                return {
                    "available": True,
                    "executed": False,
                    "passed": None,
                    "message": "Base repository path does not exist locally.",
                }
        else:
            workspace = root / "repo"
            workspace.mkdir()

        try:
            for item in files:
                target = workspace / _safe_relative_path(item["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(item["code"], encoding="utf-8")
        except (OSError, ValueError) as exc:
            return {
                "available": True,
                "executed": False,
                "passed": False,
                "message": f"Workspace creation failed: {exc}",
            }

        commands = _detect_commands(workspace)
        if not commands:
            return {
                "available": True,
                "executed": False,
                "passed": None,
                "message": "No safe deterministic test/build command was detected.",
                "files": [item["path"] for item in files],
            }

        results: list[dict[str, Any]] = []
        all_passed = True
        for command in commands:
            completed = subprocess.run(
                [
                    docker,
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--cpus",
                    "1.0",
                    "--memory",
                    "1g",
                    "--pids-limit",
                    "128",
                    "--read-only",
                    "--tmpfs",
                    "/tmp:rw,noexec,nosuid,size=256m",
                    "-v",
                    f"{workspace}:/workspace:rw",
                    "-w",
                    "/workspace",
                    "python:3.12-slim",
                    *command,
                ],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            passed = completed.returncode == 0
            all_passed = all_passed and passed
            results.append(
                {
                    "command": command,
                    "passed": passed,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-MAX_OUTPUT_CHARS:],
                    "stderr": completed.stderr[-MAX_OUTPUT_CHARS:],
                }
            )

        return {
            "available": True,
            "executed": True,
            "passed": all_passed,
            "message": "Deterministic commands executed inside a Docker sandbox.",
            "commands": results,
        }
