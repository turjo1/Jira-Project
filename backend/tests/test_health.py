import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoints_return_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ("/health", "/ready", "/live"):
            r = await client.get(path)
            assert r.status_code == 200
            assert r.json()["status"] in {"ok", "ready", "live"}


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]
        body = r.text
        assert "jira_sync_duration_seconds" in body or "api_request_latency_ms" in body
