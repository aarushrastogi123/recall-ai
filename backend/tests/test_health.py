import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "RECALL AI API"
    assert "message" in data
    assert data["version"] == "0.1.0"


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "recall-ai-backend"


def test_health_v1(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "recall-ai-backend"
    assert data["version"] == "0.1.0"


def test_unknown_endpoint(client: TestClient):
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_cors_origins(client: TestClient):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3221",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3221"

    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:3221",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3221"