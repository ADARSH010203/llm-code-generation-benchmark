from fastapi.testclient import TestClient

import server


def test_health_exposes_benchmark_models() -> None:
    response = TestClient(server.app).get("/api/health")
    assert response.status_code == 200
    assert set(response.json()["models"]) == {"qwen", "nemotron"}


def test_dashboard_is_served_from_fastapi() -> None:
    response = TestClient(server.app).get("/")
    assert response.status_code == 200
    assert "CODE ARENA" in response.text


def test_evaluation_forwards_reference_and_execution(monkeypatch) -> None:
    received = []

    def fake_evaluate(output, task, context, reference, execution):
        received.append((output, task, context, reference, execution))
        return {"overall_score_10": 8.5, "detailed_metrics": {}}

    def fake_compare(task, qwen, nemotron, reference):
        assert reference == "reference implementation"
        return {"winner": "Qwen", "reason": "test"}

    monkeypatch.setattr(server, "evaluate_code", fake_evaluate)
    monkeypatch.setattr(server, "compare_outputs", fake_compare)
    response = TestClient(server.app).post(
        "/api/evaluate",
        json={
            "task": "add a feature",
            "context": {"summary": "repo", "structure": "src"},
            "outputs": {"qwen": "qwen code", "nemotron": "nemotron code"},
            "executions": {"qwen": {"passed": True}},
            "reference_code": "reference implementation",
        },
    )
    assert response.status_code == 200
    assert len(received) == 2
    assert all(item[3] == "reference implementation" for item in received)
    assert received[0][4] == {"passed": True}
