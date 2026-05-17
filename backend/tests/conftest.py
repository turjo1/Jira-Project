"""Pytest configuration and shared fixtures for backend tests."""
import os
import json
from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.models.base import Base
from app.models.models import User, Team, Ticket, TicketTransition, UserRole
from app.services.auth import TokenService
from app.core.config import Settings


# ============================================================================
# Configuration & Fixtures Setup
# ============================================================================


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    return Settings(
        environment="test",
        log_level="ERROR",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",  # Use separate Redis DB for tests
        jwt_signing_key="test-secret-key-do-not-use",
        jwt_algorithm="HS256",
        jwt_access_ttl_seconds=3600,
        jira_client_id="test-client-id",
        jira_client_secret="test-client-secret",
        jira_redirect_uri="http://localhost:8000/auth/callback",
        aes_encryption_key="test-32byte-encryption-key-!!!",
        cors_origins=["http://localhost:3000"],
    )


@pytest_asyncio.fixture
async def test_db_engine(test_settings):
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session fixture for testing.

    Returns a fresh session for each test, with automatic rollback
    to ensure test isolation (no data pollution between tests).
    """
    async_session_maker = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        # Rollback to ensure test isolation
        await session.rollback()


@pytest_asyncio.fixture
async def app_client(test_settings, db_session):
    """Create FastAPI test client with overridden database dependency."""
    # Create app with test settings
    app = create_app()

    # Override database dependency
    async def override_get_db():
        yield db_session

    from app.core.database import get_db_session
    app.dependency_overrides[get_db_session] = override_get_db

    # Create async HTTP client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# User & Authentication Fixtures
# ============================================================================


@pytest.fixture
def jwt_token(test_settings):
    """Generate a valid JWT token for testing."""
    data = {
        "sub": "test-user-123",
        "email": "testuser@example.com",
    }
    token = TokenService.create_access_token(data)
    return token


@pytest.fixture
def jwt_token_factory(test_settings):
    """Factory fixture to generate JWT tokens with custom claims."""
    def create_token(user_id: str = "user-123", email: str = "user@example.com", **kwargs):
        data = {
            "sub": user_id,
            "email": email,
            **kwargs,
        }
        return TokenService.create_access_token(data)

    return create_token


@pytest_asyncio.fixture
async def test_user(db_session) -> User:
    """
    Create and persist a test user in the database.

    Example:
        async def test_something(test_user):
            assert test_user.email == "testuser@example.com"
    """
    user = User(
        id=str(uuid4()),
        email="testuser@example.com",
        name="Test User",
        jira_user_id="jira-user-123",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_manager(db_session) -> User:
    """Create and persist a test manager user in the database."""
    user = User(
        id=str(uuid4()),
        email="manager@example.com",
        name="Test Manager",
        jira_user_id="jira-manager-123",
        role=UserRole.MANAGER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session) -> User:
    """Create and persist a test admin user in the database."""
    user = User(
        id=str(uuid4()),
        email="admin@example.com",
        name="Test Admin",
        jira_user_id="jira-admin-123",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_factory(db_session):
    """Factory fixture to create multiple test users."""
    async def create_user(
        email: str = None,
        name: str = None,
        jira_user_id: str = None,
        role: UserRole = UserRole.MEMBER,
    ) -> User:
        user = User(
            id=str(uuid4()),
            email=email or f"user-{uuid4().hex[:8]}@example.com",
            name=name or "Test User",
            jira_user_id=jira_user_id or f"jira-{uuid4().hex[:8]}",
            role=role,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return create_user


# ============================================================================
# Team Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_team(db_session, test_manager) -> Team:
    """
    Create and persist a test team in the database.

    Example:
        async def test_something(test_team):
            assert test_team.name == "Test Team"
            assert test_team.manager_id == test_manager.id
    """
    team = Team(
        id=str(uuid4()),
        name="Test Team",
        jira_project_key="TEST",
        manager_id=test_manager.id,
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture
async def test_team_factory(db_session, test_manager):
    """Factory fixture to create multiple test teams."""
    async def create_team(
        name: str = None,
        jira_project_key: str = None,
        manager_id: str = None,
    ) -> Team:
        team = Team(
            id=str(uuid4()),
            name=name or f"Team-{uuid4().hex[:6]}",
            jira_project_key=jira_project_key or uuid4().hex[:6].upper(),
            manager_id=manager_id or test_manager.id,
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)
        return team

    return create_team


# ============================================================================
# Ticket & Transition Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_ticket(db_session, test_team, test_user) -> Ticket:
    """
    Create and persist a test ticket in the database.

    Example:
        async def test_something(test_ticket):
            assert test_ticket.jira_key == "TEST-1"
            assert test_ticket.status == "Open"
    """
    now = datetime.utcnow()
    ticket = Ticket(
        id=str(uuid4()),
        team_id=test_team.id,
        jira_key="TEST-1",
        title="Test Ticket",
        assignee_id=test_user.id,
        status="Open",
        created_at=now,
        last_synced=now,
        bounced_count=0,
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    return ticket


@pytest_asyncio.fixture
async def seeded_tickets(db_session, test_team, test_user) -> list[Ticket]:
    """
    Create a realistic dataset of 100 tickets with various statuses and transitions.

    Use this for metrics calculation tests (cycle time, bounce rate, etc.).

    Example:
        async def test_metrics(seeded_tickets):
            assert len(seeded_tickets) == 100
            open_tickets = [t for t in seeded_tickets if t.status == "Open"]
            assert len(open_tickets) > 0
    """
    tickets = []
    now = datetime.utcnow()

    # Create 100 tickets with realistic data
    statuses = ["Open", "In Progress", "In Review", "Done"]
    bounced_counts = [0, 0, 0, 0, 1, 2, 0, 1]  # Most have 0 bounces

    for i in range(100):
        created_at = now - timedelta(days=(i % 60))  # Spread over 60 days

        ticket = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key=f"TEST-{i+1}",
            title=f"Test Ticket {i+1}",
            assignee_id=test_user.id if i % 3 == 0 else None,  # 33% assigned
            status=statuses[i % 4],  # Distribute across statuses
            created_at=created_at,
            last_synced=now,
            bounced_count=bounced_counts[i % len(bounced_counts)],
        )

        # Resolved tickets have resolved_at and cycle_time
        if ticket.status == "Done":
            resolved_at = created_at + timedelta(days=(2 + (i % 10)))
            ticket.resolved_at = resolved_at
            ticket.cycle_time_days = (resolved_at - created_at).days

        tickets.append(ticket)
        db_session.add(ticket)

    await db_session.commit()

    # Refresh all tickets
    for ticket in tickets:
        await db_session.refresh(ticket)

    return tickets


@pytest_asyncio.fixture
async def seeded_transitions(db_session, seeded_tickets, test_user) -> list[TicketTransition]:
    """
    Create realistic transition history for seeded tickets.

    Includes bounce scenarios (transitioning back from Done) for bounce rate testing.

    Example:
        async def test_bounce_rate(seeded_transitions):
            bounces = [t for t in seeded_transitions if t.from_status == "Done"]
            assert len(bounces) > 0
    """
    transitions = []

    for idx, ticket in enumerate(seeded_tickets):
        created_at = ticket.created_at

        # Simulate transition history
        if ticket.status == "Done":
            # Open -> In Progress -> In Review -> Done
            states = ["Open", "In Progress", "In Review", "Done"]

            for i, state in enumerate(states):
                trans_time = created_at + timedelta(days=i)
                prev_state = states[i-1] if i > 0 else None

                transition = TicketTransition(
                    id=str(uuid4()),
                    ticket_id=ticket.id,
                    from_status=prev_state,
                    to_status=state,
                    transitioned_at=trans_time,
                    actor_id=test_user.id if i % 2 == 0 else None,
                )
                transitions.append(transition)
                db_session.add(transition)

            # Add bounce transitions for some tickets
            if ticket.bounced_count > 0:
                bounce_time = created_at + timedelta(days=len(states))
                transition = TicketTransition(
                    id=str(uuid4()),
                    ticket_id=ticket.id,
                    from_status="Done",
                    to_status="In Progress",
                    transitioned_at=bounce_time,
                    actor_id=test_user.id,
                )
                transitions.append(transition)
                db_session.add(transition)

        elif ticket.status == "In Progress":
            # Open -> In Progress
            trans1 = TicketTransition(
                id=str(uuid4()),
                ticket_id=ticket.id,
                from_status="Open",
                to_status="In Progress",
                transitioned_at=created_at + timedelta(hours=1),
                actor_id=test_user.id,
            )
            transitions.append(trans1)
            db_session.add(trans1)

        elif ticket.status == "Open":
            # No transitions yet
            pass

    await db_session.commit()

    # Refresh all transitions
    for transition in transitions:
        await db_session.refresh(transition)

    return transitions


# ============================================================================
# Mock Data Helpers
# ============================================================================


@pytest.fixture
def jira_oauth_response():
    """Mock Jira OAuth token response."""
    return {
        "access_token": "jira-access-token-fake",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "jira-refresh-token-fake",
    }


@pytest.fixture
def jira_user_response():
    """Mock Jira user (accessible resources) response."""
    return {
        "email": "testuser@example.com",
        "accountId": "jira-account-123",
        "name": "Test User",
        "avatarUrls": {
            "48x48": "https://secure.gravatar.com/avatar/...",
        },
    }


@pytest.fixture
def jira_issues_search_response():
    """Mock Jira issues search response."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 100,
        "issues": [
            {
                "key": "TEST-1",
                "id": "jira-issue-id-1",
                "fields": {
                    "summary": "Test Issue 1",
                    "status": {
                        "name": "Open",
                        "id": "10000",
                    },
                    "assignee": {
                        "accountId": "jira-user-123",
                        "displayName": "Test User",
                        "emailAddress": "testuser@example.com",
                    },
                    "created": "2026-01-01T00:00:00.000+0000",
                    "updated": "2026-05-17T12:00:00.000+0000",
                },
            },
            {
                "key": "TEST-2",
                "id": "jira-issue-id-2",
                "fields": {
                    "summary": "Test Issue 2",
                    "status": {
                        "name": "In Progress",
                        "id": "10001",
                    },
                    "assignee": {
                        "accountId": "jira-user-456",
                        "displayName": "Another User",
                        "emailAddress": "another@example.com",
                    },
                    "created": "2026-02-01T00:00:00.000+0000",
                    "updated": "2026-05-17T12:00:00.000+0000",
                },
            },
        ],
    }


@pytest.fixture
def jira_issue_changelog_response():
    """Mock Jira issue changelog response."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 3,
        "histories": [
            {
                "id": "1",
                "created": "2026-01-01T00:00:00.000+0000",
                "items": [
                    {
                        "field": "status",
                        "fromString": "Open",
                        "toString": "In Progress",
                    },
                ],
            },
            {
                "id": "2",
                "created": "2026-01-05T12:00:00.000+0000",
                "items": [
                    {
                        "field": "status",
                        "fromString": "In Progress",
                        "toString": "In Review",
                    },
                ],
            },
            {
                "id": "3",
                "created": "2026-01-10T18:00:00.000+0000",
                "items": [
                    {
                        "field": "status",
                        "fromString": "In Review",
                        "toString": "Done",
                    },
                ],
            },
        ],
    }


# ============================================================================
# Pytest Hooks & Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (requires pytest-asyncio)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture(autouse=True)
def reset_sqlalchemy_session():
    """Reset SQLAlchemy session state after each test."""
    yield
    # Cleanup hook if needed
