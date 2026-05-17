"""Pydantic models for mock Jira API responses."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class JiraIssueStatus(BaseModel):
    """Jira issue status."""

    id: str
    name: str


class JiraUser(BaseModel):
    """Jira user representation."""

    accountId: str
    displayName: str
    emailAddress: str


class JiraField(BaseModel):
    """Jira issue fields."""

    summary: str
    status: JiraIssueStatus
    assignee: Optional[JiraUser] = None
    created: str  # ISO 8601 datetime
    updated: str  # ISO 8601 datetime
    key: Optional[str] = None
    issuetype: Optional[dict] = None


class JiraIssue(BaseModel):
    """Jira issue response."""

    key: str
    id: str
    fields: JiraField


class JiraIssueSearchResponse(BaseModel):
    """Jira issue search (JQL) response."""

    startAt: int = 0
    maxResults: int = 50
    total: int = 0
    issues: List[JiraIssue] = Field(default_factory=list)


class JiraHistoryItem(BaseModel):
    """Single change item in issue history."""

    field: str
    fromString: Optional[str] = None
    toString: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None


class JiraChangeHistory(BaseModel):
    """Change history entry for an issue."""

    id: str
    created: str  # ISO 8601 datetime
    items: List[JiraHistoryItem]


class JiraChangelogResponse(BaseModel):
    """Jira issue changelog response."""

    startAt: int = 0
    maxResults: int = 50
    total: int = 0
    histories: List[JiraChangeHistory] = Field(default_factory=list)


class JiraOAuthTokenResponse(BaseModel):
    """Jira OAuth2 token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None


class JiraAccessibleResource(BaseModel):
    """Jira accessible resource (instance)."""

    id: str
    url: str
    name: str
    scopes: List[str]
    avatarUrl: str


class JiraUserProfile(BaseModel):
    """Jira user profile response."""

    accountId: str
    emailAddress: str
    displayName: str
    active: bool = True
    timeZone: str = "UTC"


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    error_description: Optional[str] = None
    status_code: int = 400
