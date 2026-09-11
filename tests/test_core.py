from code_ingestion import ingest_github_repo
from context_retrieval import build_retrieved_context
from model_service import MODEL_CONFIG
from sandbox_runner import parse_generated_files


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
