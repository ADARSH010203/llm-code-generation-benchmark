from code_ingestion import ingest_github_repo
from code_validation import validate_generated_output


def test_python_output_is_checked() -> None:
    result = validate_generated_output("def hello():\n    return 'world'\n")
    assert result["syntax"]["passed"] is True
    assert result["security"]["passed"] is True


def test_invalid_python_is_rejected() -> None:
    result = validate_generated_output("def hello(:\n")
    assert result["syntax"]["passed"] is False


def test_credential_pattern_is_flagged() -> None:
    result = validate_generated_output('API_KEY = "this-looks-like-a-secret-value"')
    assert result["security"]["passed"] is False


def test_empty_repository_url_is_rejected() -> None:
    try:
        ingest_github_repo("   ")
    except ValueError:
        return
    raise AssertionError("Expected ValueError for an empty repository URL")
