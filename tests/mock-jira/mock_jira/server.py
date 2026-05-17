"""Mock Jira API server for testing authentication, sync, and error scenarios."""
import logging
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

from .models import (
    JiraOAuthTokenResponse,
    JiraIssueSearchResponse,
    JiraChangelogResponse,
    JiraUserProfile,
    JiraAccessibleResource,
)
from .fixtures import generate_fake_issues, generate_fake_changelog, FAKE_USERS

logger = logging.getLogger(__name__)

# Application state (reset for each test)
class MockJiraState:
    """State management for mock Jira server."""

    def __init__(self):
        self.valid_codes = {"test-auth-code"}
        self.valid_tokens = {"fake-jira-token"}
        self.error_scenarios = set()  # e.g., {"RATE_LIMIT", "SERVER_ERROR"}
        self.issue_cache: Dict[str, list] = {}  # Cache for issues by team
        self.reset()

    def reset(self):
        """Reset server state for clean tests."""
        self.valid_codes = {"test-auth-code"}
        self.valid_tokens = {"fake-jira-token"}
        self.error_scenarios = set()
        self.issue_cache = {}

    def enable_error(self, error_type: str):
        """Enable error scenario (RATE_LIMIT, SERVER_ERROR, etc.)."""
        self.error_scenarios.add(error_type)

    def disable_error(self, error_type: str):
        """Disable error scenario."""
        self.error_scenarios.discard(error_type)

    def clear_errors(self):
        """Clear all error scenarios."""
        self.error_scenarios.clear()


# Global state
state = MockJiraState()

# Create FastAPI app
app = FastAPI(
    title="Mock Jira API",
    version="0.1.0",
    description="Fake Jira API server for testing",
)


# ============================================================================
# OAuth2 Endpoints
# ============================================================================


@app.post("/oauth/token", response_model=JiraOAuthTokenResponse)
async def oauth_token(
    grant_type: str = "authorization_code",
    code: str = None,
    client_id: str = None,
    client_secret: str = None,
    redirect_uri: str = None,
):
    """Mock Jira OAuth2 token endpoint.

    Supports error injection via authorization codes:
    - Use "INVALID_CODE" to trigger 401 Unauthorized
    - Use "RATE_LIMITED" to trigger 429 Rate Limit
    - Use "SERVER_ERROR" to trigger 500 Server Error
    """
    # Error scenario: rate limit
    if "RATE_LIMIT" in state.error_scenarios or code == "RATE_LIMITED":
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "0"},
        )

    # Error scenario: server error
    if "SERVER_ERROR" in state.error_scenarios or code == "SERVER_ERROR":
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )

    # Invalid code
    if code not in state.valid_codes and code != "INVALID_CODE":
        if code == "INVALID_CODE":
            raise HTTPException(status_code=401, detail="Invalid authorization code")

    if code == "INVALID_CODE":
        raise HTTPException(status_code=401, detail="Invalid authorization code")

    # Generate fake token
    fake_token = f"jira-token-{code}-{client_id}"
    state.valid_tokens.add(fake_token)

    return JiraOAuthTokenResponse(
        access_token=fake_token,
        token_type="Bearer",
        expires_in=3600,
        refresh_token=f"refresh-{fake_token}",
    )


@app.get("/oauth/authorize/accessible-resources", response_model=List[JiraAccessibleResource])
async def accessible_resources(authorization: str = None):
    """Mock Jira accessible resources endpoint.

    Returns Jira instances accessible with the provided token.
    """
    if not authorization or "Bearer" not in authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.replace("Bearer ", "").strip()

    # Error scenarios
    if "RATE_LIMIT" in state.error_scenarios:
        raise HTTPException(status_code=429, detail="Too many requests")

    if "SERVER_ERROR" in state.error_scenarios:
        raise HTTPException(status_code=500, detail="Internal server error")

    if token not in state.valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Return mock accessible resources
    return [
        JiraAccessibleResource(
            id="jira-cloud-id",
            url="https://my-jira.atlassian.net",
            name="My Jira Cloud",
            scopes=["read:me", "read:jira-work"],
            avatarUrl="https://secure.gravatar.com/avatar/avatar.png",
        ),
    ]


@app.get("/oauth/authorize/user-profile", response_model=JiraUserProfile)
async def user_profile(authorization: str = None):
    """Mock Jira user profile endpoint."""
    if not authorization or "Bearer" not in authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.replace("Bearer ", "").strip()

    # Error scenarios
    if "RATE_LIMIT" in state.error_scenarios:
        raise HTTPException(status_code=429, detail="Too many requests")

    if "SERVER_ERROR" in state.error_scenarios:
        raise HTTPException(status_code=500, detail="Internal server error")

    if token not in state.valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Return mock user profile
    return JiraUserProfile(
        accountId="jira-user-123",
        emailAddress="testuser@example.com",
        displayName="Test User",
        active=True,
        timeZone="UTC",
    )


# ============================================================================
# Issue Search Endpoint
# ============================================================================


@app.get("/rest/api/3/issues/search", response_model=JiraIssueSearchResponse)
async def search_issues(
    jql: str = None,
    startAt: int = Query(0),
    maxResults: int = Query(50),
    expand: str = None,
):
    """Mock Jira issue search (JQL) endpoint.

    Supports:
    - JQL queries like: "assignee=user-123 AND status!=Done"
    - Pagination via startAt and maxResults
    - Error injection: Use jql="ERROR:RATE_LIMIT" or "ERROR:SERVER_ERROR"
    """
    # Error scenario: rate limit
    if jql and "ERROR:RATE_LIMIT" in jql:
        raise HTTPException(status_code=429, detail="Too many requests")

    if "RATE_LIMIT" in state.error_scenarios:
        raise HTTPException(status_code=429, detail="Too many requests")

    # Error scenario: server error
    if jql and "ERROR:SERVER_ERROR" in jql:
        raise HTTPException(status_code=500, detail="Internal server error")

    if "SERVER_ERROR" in state.error_scenarios:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Extract project key from JQL or use default
    project_key = "TEST"
    if jql and "PROJECT=" in jql.upper():
        parts = jql.upper().split("PROJECT=")
        if len(parts) > 1:
            project_key = parts[1].split()[0].strip('"')

    # Cache issues if not already cached
    if project_key not in state.issue_cache:
        state.issue_cache[project_key] = generate_fake_issues(project_key, count=100)

    all_issues = state.issue_cache[project_key]

    # Filter by JQL if provided (simple filtering)
    filtered_issues = all_issues
    if jql:
        # Very basic JQL filtering (for testing purposes)
        if "status" in jql.lower():
            # Parse status filter (e.g., "status!=Done" or "status=Open")
            if "!=" in jql:
                exclude_status = jql.split("!=")[1].split()[0].strip('"')
                filtered_issues = [
                    issue
                    for issue in filtered_issues
                    if issue.fields.status.name != exclude_status
                ]
            elif "=" in jql:
                include_status = jql.split("=")[1].split()[0].strip('"')
                filtered_issues = [
                    issue
                    for issue in filtered_issues
                    if issue.fields.status.name == include_status
                ]

    # Apply pagination
    total = len(filtered_issues)
    paginated_issues = filtered_issues[startAt : startAt + maxResults]

    return JiraIssueSearchResponse(
        startAt=startAt,
        maxResults=maxResults,
        total=total,
        issues=paginated_issues,
    )


# ============================================================================
# Issue Changelog Endpoint
# ============================================================================


@app.get("/rest/api/3/issues/{issue_key}/changelog", response_model=JiraChangelogResponse)
async def issue_changelog(
    issue_key: str,
    startAt: int = Query(0),
    maxResults: int = Query(50),
):
    """Mock Jira issue changelog endpoint.

    Returns status transition history for an issue.
    Useful for bounce rate calculation (detecting status reversions).
    """
    # Error scenario: rate limit
    if "RATE_LIMIT" in state.error_scenarios:
        raise HTTPException(status_code=429, detail="Too many requests")

    # Error scenario: server error
    if "SERVER_ERROR" in state.error_scenarios:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Check if issue exists
    # For this mock, we just generate fake changelog for any issue
    if not issue_key or issue_key.startswith("INVALID"):
        raise HTTPException(status_code=404, detail="Issue not found")

    # Generate changelog
    histories = generate_fake_changelog(issue_key)

    # Apply pagination
    total = len(histories)
    paginated_histories = histories[startAt : startAt + maxResults]

    return JiraChangelogResponse(
        startAt=startAt,
        maxResults=maxResults,
        total=total,
        histories=paginated_histories,
    )


# ============================================================================
# Admin Endpoints (for test control)
# ============================================================================


@app.post("/admin/reset")
async def admin_reset():
    """Reset server state (clear all cached data, tokens, errors)."""
    state.reset()
    return {"status": "reset"}


@app.post("/admin/error/{error_type}")
async def admin_enable_error(error_type: str):
    """Enable error scenario: RATE_LIMIT, SERVER_ERROR, etc."""
    state.enable_error(error_type)
    return {"status": "error_enabled", "error_type": error_type}


@app.delete("/admin/error/{error_type}")
async def admin_disable_error(error_type: str):
    """Disable error scenario."""
    state.disable_error(error_type)
    return {"status": "error_disabled", "error_type": error_type}


@app.delete("/admin/errors")
async def admin_clear_errors():
    """Clear all error scenarios."""
    state.clear_errors()
    return {"status": "errors_cleared"}


@app.post("/admin/token")
async def admin_add_token(token: str):
    """Add a valid token for testing."""
    state.valid_tokens.add(token)
    return {"status": "token_added", "token": token}


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "mock-jira"}


# ============================================================================
# Main Entry Point
# ============================================================================


def run_server(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """Run the mock Jira server."""
    uvicorn.run(
        "mock_jira.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run_server(host="0.0.0.0", port=8001, reload=True)
