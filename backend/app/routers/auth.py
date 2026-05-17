"""JWT Authentication router with Jira OAuth2 integration."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.models import User, Credentials
from app.schemas import AuthResponse, OAuthCallbackRequest
from app.services.auth import JiraOAuth2Service, TokenService

log = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


async def requires_auth(
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Dependency to extract and validate JWT token from Authorization header.
    Returns user_id if valid, raises 401 otherwise.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = TokenService.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


@router.post("/jira", response_model=dict[str, str])
async def initiate_jira_oauth() -> dict[str, str]:
    """
    Initiate Jira OAuth2 login flow.

    Returns:
        dict with auth_url for redirecting user to Jira login
    """
    try:
        # Generate random state for CSRF protection
        state = str(uuid.uuid4())

        oauth_service = JiraOAuth2Service()
        authorization_url = await oauth_service.get_authorization_url(state)

        log.info("oauth.initiated", state=state[:8])
        return {"auth_url": authorization_url}
    except Exception as e:
        log.error("oauth.initiation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow",
        )


@router.post("/callback", response_model=AuthResponse)
async def handle_oauth_callback(
    request: OAuthCallbackRequest,
    db_session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    """
    Handle Jira OAuth2 callback and exchange code for JWT token.

    Args:
        request: OAuth callback request with code and state
        db_session: Database session for user operations

    Returns:
        AuthResponse with JWT access token

    Raises:
        HTTPException: 401 if Jira API fails, 500 for other errors
    """
    try:
        oauth_service = JiraOAuth2Service()

        # Step 1: Exchange authorization code for Jira access token
        log.info("oauth.exchanging_code", code=request.code[:8])
        token_response = await oauth_service.exchange_code_for_token(request.code)
        jira_access_token = token_response.get("access_token")

        if not jira_access_token:
            log.error("oauth.no_access_token_in_response", response=token_response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to obtain access token from Jira",
            )

        # Step 2: Fetch user info from Jira
        log.info("oauth.fetching_user_info")
        resources = await oauth_service.get_accessible_resources(jira_access_token)

        if not resources:
            log.error("oauth.no_accessible_resources")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No accessible Jira resources",
            )

        # Extract user info from first accessible resource
        resource = resources[0]
        jira_user_id = resource.get("id")
        jira_instance_url = resource.get("url")
        user_email = resource.get("email")
        user_name = resource.get("name", user_email)

        if not jira_user_id or not user_email or not jira_instance_url:
            log.error("oauth.incomplete_user_info", resource=resource)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incomplete user information from Jira",
            )

        # Step 3: Create or update user in database
        log.info("oauth.upserting_user", email=user_email, jira_user_id=jira_user_id)

        stmt = select(User).where(User.email == user_email)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update existing user
            user.name = user_name
            user.jira_user_id = jira_user_id
            log.info("oauth.user_updated", user_id=user.id)
        else:
            # Create new user
            user = User(
                id=str(uuid.uuid4()),
                email=user_email,
                name=user_name,
                jira_user_id=jira_user_id,
            )
            db_session.add(user)
            log.info("oauth.user_created", user_id=user.id, email=user_email)

        await db_session.flush()  # Ensure user.id is populated

        # Step 4: Store encrypted Jira token in credentials
        # Note: In production, encrypt jira_access_token before storing
        creds_stmt = select(Credentials).where(Credentials.user_id == user.id)
        creds_result = await db_session.execute(creds_stmt)
        credentials = creds_result.scalar_one_or_none()

        if credentials:
            credentials.jira_instance_url = jira_instance_url
            credentials.jira_token_encrypted = jira_access_token  # TODO: encrypt in production
        else:
            credentials = Credentials(
                user_id=user.id,
                jira_instance_url=jira_instance_url,
                jira_token_encrypted=jira_access_token,  # TODO: encrypt in production
            )
            db_session.add(credentials)

        await db_session.commit()
        log.info("oauth.credentials_stored", user_id=user.id)

        # Step 5: Generate JWT token for frontend
        access_token = TokenService.create_access_token(
            data={"sub": user.id, "email": user_email}
        )
        expires_in = settings.jwt_access_ttl_seconds

        log.info("oauth.token_generated", user_id=user.id)

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("oauth.callback_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/logout")
async def logout(
    user_id: str = Depends(requires_auth),
) -> dict[str, str]:
    """
    Logout endpoint (stub implementation).

    In a real implementation, this would:
    - Revoke the JWT token (add to blacklist)
    - Clear session data
    - Revoke Jira API credentials

    Args:
        user_id: Current user ID from JWT token

    Returns:
        Success message
    """
    log.info("user.logout", user_id=user_id)
    return {"message": "logged out"}
