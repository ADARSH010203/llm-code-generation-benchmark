from benchmark.model_service import MODEL_CONFIG

def test_model_configuration_is_explicit() -> None:
    assert MODEL_CONFIG["qwen"]["model"] == "groq/qwen/qwen3.6-27b"
    assert MODEL_CONFIG["qwen"]["api_key_env"] == "GROQ_API_KEY"
    assert MODEL_CONFIG["nemotron"]["model"] == "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
    assert MODEL_CONFIG["nemotron"]["api_key_env"] == "OPENROUTER_API_KEY"

