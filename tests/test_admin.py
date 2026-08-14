import pytest
import httpx
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_admin_dashboard_html():
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert "SovereignForge Ops" in response.text
    assert "ZERO-RETENTION AIR-GAP ACTIVE" in response.text


def test_admin_stats_api():
    response = client.get("/api/v1/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert "active_workers" in data
    assert "total_tokens_served" in data
    assert "registered_models" in data
    assert data["zero_retention_compliance"] == "verified"
