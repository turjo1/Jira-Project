"""Jira OAuth2 authentication service."""
import httpx
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import structlog

from app.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()


class JiraOAuth2Service:
    """Service for handling Jira OAuth2 flow."""

    def __init__(self):
        self.client_id = settings.jira_client_id
        self.client_secret = settings.jira_client_secret
        self.redirect_uri = settings.jira_redirect_uri
        self.authorize_url = settings.jira_oauth_authorize_url
        self.token_url = settings.jira_oauth_token_url
        self.accessible_resources_url = settings.jira_accessible_resources_url

    async def get_authorization_url(self, state: str) -> str:
        """Generate Jira OAuth2 authorization URL."""
        return (
            f"{self.authorize_url}"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
            f"&scope=read:me"
        )

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def get_accessible_resources(self, access_token: str) -> list[dict]:
        """Get list of Jira instances accessible with the access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.accessible_resources_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()


class TokenService:
    """Service for JWT token management."""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                seconds=settings.jwt_access_ttl_seconds
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_signing_key, algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token, settings.jwt_signing_key, algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError:
            log.warning("Invalid JWT token")
            return None
