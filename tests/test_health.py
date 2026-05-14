"""Health & metrics endpoint smoke tests."""
from __future__ import annotations


def test_root_banner(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_metrics_endpoint(client):
    # Trigger something to populate metrics
    client.get("/")
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    # Prometheus exposition format
    assert "http_requests_total" in body or "http_request" in body


def test_openapi_schema(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    paths = schema["paths"]
    for endpoint in [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/books",
        "/api/v1/borrow",
    ]:
        assert endpoint in paths
