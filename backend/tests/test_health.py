"""
Health and Readiness Probes Test Suite
"""
from fastapi.testclient import TestClient


def test_root_welcome(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "FDR Sentinel"
    assert "version" in data
    assert "health" in data


def test_liveness_probe(client: TestClient):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["service"] == "FDR Sentinel"
    assert "timestamp" in data


def test_liveness_alias_healthz(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_probe_success(client: TestClient):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["is_ready"] is True
    assert "components" in data
    assert "database" in data["components"]
    assert data["components"]["database"]["status"] == "connected"
    assert data["components"]["database"]["dialect"] is not None
    assert "latency_ms" in data["components"]["database"]


def test_readiness_alias_readyz(client: TestClient):
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["is_ready"] is True
