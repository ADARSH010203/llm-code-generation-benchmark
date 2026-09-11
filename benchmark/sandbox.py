"""Optional isolated execution for generated multi-file code.

Generated code is treated as untrusted. Docker is required, the container has
no network by default, CPU/memory/process limits are applied, and the workspace
is removed after the check completes.
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
    """Reject paths that can escape the temporary workspace."""
    candidate = Path(path.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe generated path: {path}")
    return candidate


def parse_generated_files(output: str) -> list[dict[str, str]]:
    """Parse the FILE: path + fenced code format used for multi-file tasks."""
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


def _detect_commands(root: Path) -> list[tuple[str, list[str]]]:
    """Select only deterministic checks that do not install arbitrary packages."""
    commands: list[tuple[str, list[str]]] = []

    if (
        (root / "pyproject.toml").exists()
        or (root / "requirements.txt").exists()
        or (root / "tests").is_dir()
    ):
        commands.append(("python", ["python", "-m", "compileall", "-q", "."]))

    package_json = root / "package.json"
    node_modules = root / "node_modules"
    if package_json.exists() and node_modules.is_dir():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "test" in scripts:
                commands.append(("node", ["npm", "test", "--", "--runInBand"]))
            if "build" in scripts:
                commands.append(("node", ["npm", "run", "build"]))
        except (OSError, json.JSONDecodeError):
            pass

    return commands


def _docker_command(
    image: str,
    command: list[str],
    workspace: Path,
) -> list[str]:
    """Build the restricted docker invocation."""
    return [
        "docker",
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
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=256m",
        "-v",
        f"{workspace}:/workspace:rw",
        "-w",
        "/workspace",
        image,
        *command,
    ]


def run_generated_workspace(
    generated_output: str,
    base_repository: str | os.PathLike[str] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Apply generated files to a temporary workspace and run safe checks."""
    files = parse_generated_files(generated_output)
    docker = shutil.which("docker")

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
        workspace = root / "repo"
        workspace.mkdir()

        if base_repository:
            source_root = Path(base_repository).resolve()
            if not source_root.is_dir():
                return {
                    "available": True,
                    "executed": False,
                    "passed": None,
                    "message": "Base repository path does not exist locally.",
                }
            shutil.copytree(
                source_root,
                workspace,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".git", ".venv", "node_modules"),
            )

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

        checks = _detect_commands(workspace)
        if not checks:
            return {
                "available": True,
                "executed": False,
                "passed": None,
                "message": (
                    "No safe deterministic test/build command was detected. "
                    "Node projects need existing node_modules; dependencies are not installed automatically."
                ),
                "files": [item["path"] for item in files],
            }

        results: list[dict[str, Any]] = []
        all_passed = True
        for language, command in checks:
            image = "node:22-bookworm-slim" if language == "node" else "python:3.12-slim"
            try:
                completed = subprocess.run(
                    _docker_command(image, command, workspace),
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return {
                    "available": True,
                    "executed": True,
                    "passed": False,
                    "message": f"Sandbox command timed out after {timeout_seconds} seconds.",
                    "commands": results,
                }

            passed = completed.returncode == 0
            all_passed = all_passed and passed
            results.append(
                {
                    "language": language,
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
            "message": "Deterministic checks executed inside a restricted Docker sandbox.",
            "commands": results,
        }


def clone_and_run(
    repo_url: str,
    generated_output: str,
    timeout_seconds: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Clone a public repository, overlay generated files, and run sandbox checks.

    Repository download happens outside Docker because the sandbox itself has no
    network. The cloned source is never executed on the host.
    """
    git = shutil.which("git")
    if not git:
        return {
            "available": False,
            "executed": False,
            "passed": None,
            "message": "Git is not installed; repository-backed sandbox check was skipped.",
        }

    with tempfile.TemporaryDirectory(prefix="llm-repo-") as temp_dir:
        repo_path = Path(temp_dir) / "repo"
        try:
            subprocess.run(
                [git, "clone", "--depth", "1", "--no-tags", repo_url.strip(), str(repo_path)],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            return {
                "available": bool(shutil.which("docker")),
                "executed": False,
                "passed": None,
                "message": f"Repository clone failed: {exc}",
            }

        return run_generated_workspace(
            generated_output,
            base_repository=repo_path,
            timeout_seconds=timeout_seconds,
        )
