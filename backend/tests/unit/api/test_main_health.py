from fastapi.testclient import TestClient

from backend.src.main import app


def test_health_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("ORS_API_KEY", "test-key")
    monkeypatch.setenv("ORS_BASE_URL", "https://atu.ie")

    with TestClient(app) as client:
        response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
