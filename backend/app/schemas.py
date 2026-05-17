"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MetricTile(BaseModel):
    """Single metric tile (Open Tickets, Cycle Time, etc.)."""

    title: str = Field(..., description="Metric title")
    value: str = Field(..., description="Main metric value")
    unit: str = Field(..., description="Unit of measurement")
    comparison: Optional[str] = Field(None, description="Comparison value")
    trend: Optional[str] = Field(None, description="Trend direction (up/down)")


class StatusDistributionItem(BaseModel):
    """Status distribution item."""

    status: str
    count: int
    avg_dwell_days: float


class TeamActivityItem(BaseModel):
    """Recent team activity item."""

    timestamp: datetime
    actor_name: str
    actor_initials: str
    action: str
    ticket_key: str
    to_status: str


class DashboardMetrics(BaseModel):
    """Complete dashboard metrics response."""

    team_id: str
    metrics: list[MetricTile]
    status_distribution: dict[str, StatusDistributionItem]
    recent_activity: list[TeamActivityItem]
    last_synced: datetime


class UserProfile(BaseModel):
    """User profile response."""

    id: str
    email: str
    name: str
    role: str
    team_id: Optional[str]


class AuthResponse(BaseModel):
    """Authentication response with JWT token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str
    state: str


class TicketResponse(BaseModel):
    """Ticket response model."""

    id: str
    jira_key: str
    title: str
    status: str
    assignee_name: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    cycle_time_days: Optional[float]
