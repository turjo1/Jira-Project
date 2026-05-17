"""Pytest plugin for mock Jira server fixture.

Usage in test files:
    from mock_jira.pytest_plugin import mock_jira_client  # noqa: F401

Or add to conftest.py:
    pytest_plugins = ["mock_jira.pytest_plugin"]
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from .server import app as mock_jira_app, state as mock_jira_state


@pytest.fixture
def mock_jira_url():
    """Base URL used when mock server runs as a real process (port 8001)."""
    return "http://localhost:8001"


@pytest_asyncio.fixture
async def mock_jira_client() -> AsyncGenerator[AsyncClient, None]:
    """In-memory async HTTP client for mock Jira server (no network required).

    Resets server state before and after each test to prevent pollution.

    Example::

        async def test_oauth(mock_jira_client):
            response = await mock_jira_client.post(
                "/oauth/token",
                data={"grant_type": "authorization_code", "code": "test-auth-code"},
            )
            assert response.status_code == 200
    """
    mock_jira_state.reset()
    transport = ASGITransport(app=mock_jira_app)
    async with AsyncClient(transport=transport, base_url="http://mock-jira") as client:
        yield client
    mock_jira_state.reset()
