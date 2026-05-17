"""Database models for Jira Team Performance Analytics."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Numeric,
    String,
    Text,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    Date,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class UserRole(str, Enum):
    """User roles."""

    MEMBER = "member"
    MANAGER = "manager"
    ADMIN = "admin"


class User(BaseModel):
    """User model."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jira_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(String(50), default=UserRole.MEMBER)
    team_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("teams.id"))

    # Relationships
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="members", foreign_keys=[team_id])
    credentials: Mapped[Optional["Credentials"]] = relationship("Credentials", uselist=False, back_populates="user")
    managed_teams: Mapped[list["Team"]] = relationship(
        "Team", foreign_keys="Team.manager_id", back_populates="manager"
    )
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="assignee")
    transitions: Mapped[list["TicketTransition"]] = relationship("TicketTransition", back_populates="actor")

    __table_args__ = (Index("idx_email", "email"), Index("idx_jira_user_id", "jira_user_id"))


class Team(BaseModel):
    """Team model."""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jira_project_key: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    manager_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # Relationships
    manager: Mapped[User] = relationship(
        "User", foreign_keys=[manager_id], back_populates="managed_teams"
    )
    members: Mapped[list[User]] = relationship(
        "User", foreign_keys="User.team_id", back_populates="team"
    )
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="team")
    metrics: Mapped[list["Metrics"]] = relationship("Metrics", back_populates="team")

    __table_args__ = (
        Index("idx_manager_id", "manager_id"),
        Index("idx_jira_project_key", "jira_project_key"),
    )


class Credentials(BaseModel):
    """Encrypted Jira API credentials."""

    __tablename__ = "credentials"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    jira_instance_url: Mapped[str] = mapped_column(String(255), nullable=False)
    jira_token_encrypted: Mapped[str] = mapped_column(String(1024), nullable=False)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="credentials")


class Ticket(BaseModel):
    """Jira ticket model."""

    __tablename__ = "tickets"

    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), nullable=False)
    jira_key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cycle_time_days: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    bounced_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    team: Mapped[Team] = relationship("Team", back_populates="tickets")
    assignee: Mapped[Optional[User]] = relationship("User", back_populates="tickets", foreign_keys=[assignee_id])
    transitions: Mapped[list["TicketTransition"]] = relationship("TicketTransition", back_populates="ticket")

    __table_args__ = (
        Index("idx_team_status", "team_id", "status"),
        Index("idx_assignee", "assignee_id"),
        Index("idx_created", "created_at"),
        Index("idx_team_resolved", "team_id", "resolved_at"),
    )


class TicketTransition(BaseModel):
    """Audit log for ticket status transitions."""

    __tablename__ = "ticket_transitions"

    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id"), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    transitioned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))

    # Relationships
    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="transitions")
    actor: Mapped[Optional[User]] = relationship("User", back_populates="transitions")

    __table_args__ = (
        Index("idx_ticket", "ticket_id"),
        Index("idx_bounce_detection", "ticket_id", "from_status", "to_status"),
    )


class Metrics(BaseModel):
    """Pre-calculated daily metrics."""

    __tablename__ = "metrics"

    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    avg_cycle_time_days: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    bounce_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    open_tickets: Mapped[Optional[int]] = mapped_column(Integer)
    bottleneck_status: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationships
    team: Mapped[Team] = relationship("Team", back_populates="metrics")

    __table_args__ = (UniqueConstraint("team_id", "date", name="uk_team_date"),)
