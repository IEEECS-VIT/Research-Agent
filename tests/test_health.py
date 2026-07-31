from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Research Alignment Agent"


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Research Alignment Agent"
    assert "python_version" in data
