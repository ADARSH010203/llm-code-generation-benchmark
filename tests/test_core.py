from benchmark.agent import build_repair_prompt, inspect_candidate
from benchmark.model_service import MODEL_CONFIG
from benchmark.retrieval import build_retrieved_context
from benchmark.sandbox import parse_generated_files
from benchmark.tasks import load_tasks
from code_ingestion import ingest_github_repo


def test_model_configuration_is_explicit() -> None:
    assert MODEL_CONFIG["aya_expanse"]["model"].startswith("c4ai-")
    assert MODEL_CONFIG["llama_scout"]["model"].startswith("llama-")


def test_ingestion_rejects_empty_url() -> None:
    try:
        ingest_github_repo(" ")
    except ValueError:
        return
    raise AssertionError("empty repository URL should be rejected")


def test_retrieval_returns_bounded_context() -> None:
    content = "FILE: auth.py\ndef login_user():\n    return True\n\nFILE: ui.py\ndef render_page():\n    return True\n"
    result = build_retrieved_context(content, "fix login authentication")
    assert result["candidate_files"] == 2
    assert result["total_chars"] <= 70000


def test_generated_file_parser_supports_multiple_files() -> None:
    output = "FILE: app.py\n```python\nprint('ok')\n```\n\nFILE: index.html\n```html\n<html></html>\n```"
    files = parse_generated_files(output)
    assert [item["path"] for item in files] == ["app.py", "index.html"]


def test_benchmark_tasks_are_reproducible() -> None:
    tasks = load_tasks()
    assert len(tasks) >= 10
    assert len({task.id for task in tasks}) == len(tasks)
    assert all(task.task for task in tasks)


def test_agent_validation_catches_secret_patterns() -> None:
    step = inspect_candidate("API_KEY = 'sk-test-1234567890abcdefghij'")
    assert step.name == "candidate_validation"
    assert step.status == "failed"


def test_repair_prompt_is_bounded_to_observed_failures() -> None:
    step = inspect_candidate("def broken(:\n    pass")
    run = type("Run", (), {"steps": [step]})()
    prompt = build_repair_prompt("Fix the parser", run)
    assert "Fix the parser" in prompt
    assert "candidate_validation" in prompt
    assert "rewrite unrelated code" in prompt
