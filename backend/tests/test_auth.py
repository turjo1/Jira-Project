"""Tests for JWT authentication router."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select

from app.models.models import User, Credentials
from app.schemas import OAuthCallbackRequest


@pytest.mark.asyncio
async def test_initiate_jira_oauth(app_client):
    """Test POST /auth/jira returns authorization URL."""
    response = await app_client.post("/auth/jira")

    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "https://auth.atlassian.com/authorize" in data["auth_url"]
    assert "client_id=" in data["auth_url"]
    assert "response_type=code" in data["auth_url"]
    assert "state=" in data["auth_url"]


@pytest.mark.asyncio
async def test_oauth_callback_success(app_client, db_session):
    """Test POST /auth/callback exchanges code for JWT token."""
    mock_token_response = {
        "access_token": "jira_access_token_123",
        "token_type": "bearer",
    }

    mock_resources = [
        {
            "id": "jira_user_id_123",
            "url": "https://myteam.atlassian.net",
            "email": "user@example.com",
            "name": "John Doe",
        }
    ]

    with patch(
        "app.routers.auth.JiraOAuth2Service.exchange_code_for_token",
        new_callable=AsyncMock,
        return_value=mock_token_response,
    ), patch(
        "app.routers.auth.JiraOAuth2Service.get_accessible_resources",
        new_callable=AsyncMock,
        return_value=mock_resources,
    ):
        request = OAuthCallbackRequest(code="oauth_code_123", state="state_123")
        response = await app_client.post(
            "/auth/callback",
            json={"code": "oauth_code_123", "state": "state_123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data

    # Verify user was created in database
    stmt = select(User).where(User.email == "user@example.com")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.name == "John Doe"
    assert user.jira_user_id == "jira_user_id_123"

    # Verify credentials were stored
    creds_stmt = select(Credentials).where(Credentials.user_id == user.id)
    creds_result = await db_session.execute(creds_stmt)
    credentials = creds_result.scalar_one_or_none()
    assert credentials is not None
    assert credentials.jira_instance_url == "https://myteam.atlassian.net"


@pytest.mark.asyncio
async def test_oauth_callback_jira_api_error(app_client):
    """Test POST /auth/callback handles Jira API errors."""
    with patch(
        "app.routers.auth.JiraOAuth2Service.exchange_code_for_token",
        new_callable=AsyncMock,
        side_effect=Exception("Jira API error"),
    ):
        response = await app_client.post(
            "/auth/callback",
            json={"code": "invalid_code", "state": "state_123"},
        )

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_logout_requires_auth(app_client):
    """Test POST /auth/logout requires valid JWT token."""
    # No authorization header
    response = await app_client.post("/auth/logout")
    assert response.status_code == 401

    # Invalid token
    response = await app_client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_valid_token(app_client, test_settings, db_session):
    """Test POST /auth/logout with valid JWT token."""
    # Create a user
    from app.models.models import User
    import uuid

    user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        name="John Doe",
        jira_user_id="jira_123",
    )
    db_session.add(user)
    await db_session.commit()

    # Generate JWT token
    from app.services.auth import TokenService

    token = TokenService.create_access_token(
        data={"sub": user.id, "email": user.email}
    )

    # Call logout with valid token
    response = await app_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "logged out"
