import httpx
import pytest

from apps.api.main import app


@pytest.mark.asyncio
async def test_admin_dashboard_html():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/admin/dashboard")
        assert response.status_code == 200
        assert "SovereignForge Ops" in response.text
        assert "ZERO-RETENTION AIR-GAP ACTIVE" in response.text


@pytest.mark.asyncio
async def test_admin_stats_api():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/admin/stats")
        assert response.status_code == 200
        data = response.json()
        assert "active_workers" in data
        assert "total_tokens_served" in data
        assert "registered_models" in data
        assert data["zero_retention_compliance"] == "verified"
