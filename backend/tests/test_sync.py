"""Tests for Celery sync task."""
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select

from app.models import Team, User, Credentials, Ticket, TicketTransition, Metrics, UserRole
from app.tasks.sync import sync_team_jira_data, decrypt_token
from app.core.database import async_session_maker


@pytest.fixture
async def setup_team_with_credentials(db_session):
    """Create a test team with manager credentials."""
    # Create manager user
    manager = User(
        id="user-mgr-001",
        email="manager@example.com",
        name="Manager User",
        jira_user_id="jira-mgr-001",
        role=UserRole.MANAGER,
    )
    db_session.add(manager)

    # Create team
    team = Team(
        id="team-001",
        name="Test Team",
        jira_project_key="TEST",
        manager_id="user-mgr-001",
    )
    db_session.add(team)

    # Create encrypted credentials (use a dummy encrypted token for testing)
    from cryptography.fernet import Fernet
    from app.core.config import get_settings

    settings = get_settings()
    cipher = Fernet(settings.aes_encryption_key.encode())
    encrypted = cipher.encrypt(b"test-jira-token-12345").decode()

    credentials = Credentials(
        id="cred-001",
        user_id="user-mgr-001",
        jira_instance_url="https://test.atlassian.net",
        jira_token_encrypted=encrypted,
    )
    db_session.add(credentials)

    await db_session.commit()
    return team, manager, credentials


@pytest.mark.asyncio
async def test_decrypt_token():
    """Test token decryption."""
    from cryptography.fernet import Fernet
    from app.core.config import get_settings

    settings = get_settings()
    cipher = Fernet(settings.aes_encryption_key.encode())
    original = "my-secret-token"
    encrypted = cipher.encrypt(original.encode()).decode()

    decrypted = decrypt_token(encrypted)
    assert decrypted == original


@pytest.mark.asyncio
async def test_sync_team_jira_data_no_team():
    """Test sync with non-existent team."""
    async with async_session_maker() as session:
        result = await sync_team_jira_data(session, "nonexistent-team")

    assert result["status"] == "skip"
    assert "Team not found" in result["reason"]


@pytest.mark.asyncio
async def test_sync_team_jira_data_no_credentials(db_session):
    """Test sync when team has no Jira credentials."""
    # Create team without credentials
    manager = User(
        id="user-mgr-002",
        email="manager2@example.com",
        name="Manager 2",
        jira_user_id="jira-mgr-002",
        role=UserRole.MANAGER,
    )
    db_session.add(manager)

    team = Team(
        id="team-002",
        name="Test Team 2",
        jira_project_key="TEST2",
        manager_id="user-mgr-002",
    )
    db_session.add(team)
    await db_session.commit()

    result = await sync_team_jira_data(db_session, "team-002")

    assert result["status"] == "skip"
    assert "No Jira credentials" in result["reason"]


@pytest.mark.asyncio
async def test_sync_team_jira_data_invalid_credentials(db_session, setup_team_with_credentials):
    """Test sync with invalid Jira credentials."""
    team, _, _ = setup_team_with_credentials

    with patch(
        "app.tasks.sync.JiraAPIService"
    ) as mock_jira_service:
        # Mock the service to return invalid credentials
        mock_instance = AsyncMock()
        mock_instance.verify_credentials = AsyncMock(return_value=False)
        mock_jira_service.return_value = mock_instance

        result = await sync_team_jira_data(db_session, team.id)

    assert result["status"] == "error"
    assert "Invalid Jira credentials" in result["reason"]


@pytest.mark.asyncio
async def test_sync_team_jira_data_fetches_issues(db_session, setup_team_with_credentials):
    """Test successful Jira issue fetch and upsert."""
    team, manager, credentials = setup_team_with_credentials

    # Mock Jira API responses
    mock_jira_issues = [
        {
            "key": "TEST-001",
            "fields": {
                "summary": "Fix login bug",
                "status": {"name": "In Progress"},
                "assignee": {"accountId": "jira-mgr-001"},
                "created": "2024-05-01T10:00:00.000Z",
                "resolutiondate": None,
            },
            "changelog": {
                "histories": [
                    {
                        "created": "2024-05-01T10:00:00.000Z",
                        "author": {"accountId": "jira-mgr-001"},
                        "items": [
                            {
                                "field": "status",
                                "fromString": None,
                                "toString": "In Progress",
                            }
                        ],
                    }
                ]
            },
        },
        {
            "key": "TEST-002",
            "fields": {
                "summary": "Add new feature",
                "status": {"name": "Done"},
                "assignee": None,
                "created": "2024-04-15T08:30:00.000Z",
                "resolutiondate": "2024-05-10T16:45:00.000Z",
            },
            "changelog": {
                "histories": [
                    {
                        "created": "2024-04-15T08:30:00.000Z",
                        "author": {"accountId": "jira-mgr-001"},
                        "items": [
                            {
                                "field": "status",
                                "fromString": None,
                                "toString": "Open",
                            }
                        ],
                    },
                    {
                        "created": "2024-05-10T16:45:00.000Z",
                        "author": {"accountId": "jira-mgr-001"},
                        "items": [
                            {
                                "field": "status",
                                "fromString": "In Progress",
                                "toString": "Done",
                            }
                        ],
                    },
                ]
            },
        },
    ]

    with patch(
        "app.tasks.sync.JiraAPIService"
    ) as mock_jira_service:
        mock_instance = AsyncMock()
        mock_instance.verify_credentials = AsyncMock(return_value=True)
        mock_instance.fetch_issues = AsyncMock(return_value=mock_jira_issues)
        mock_jira_service.return_value = mock_instance

        result = await sync_team_jira_data(db_session, team.id)

    assert result["status"] == "success"
    assert result["tickets_synced"] == 2
    assert result["transitions_created"] >= 2

    # Verify tickets were created
    tickets = await db_session.execute(select(Ticket).where(Ticket.team_id == team.id))
    tickets_list = tickets.scalars().all()
    assert len(tickets_list) == 2

    # Verify ticket data
    ticket_001 = next(t for t in tickets_list if t.jira_key == "TEST-001")
    assert ticket_001.title == "Fix login bug"
    assert ticket_001.status == "In Progress"
    assert ticket_001.assignee_id == manager.id

    ticket_002 = next(t for t in tickets_list if t.jira_key == "TEST-002")
    assert ticket_002.title == "Add new feature"
    assert ticket_002.status == "Done"
    assert ticket_002.resolved_at is not None
    assert ticket_002.cycle_time_days is not None  # Should be ~25 days

    # Verify transitions were created
    transitions = await db_session.execute(
        select(TicketTransition).where(TicketTransition.ticket_id == ticket_001.id)
    )
    transitions_list = transitions.scalars().all()
    assert len(transitions_list) >= 1


@pytest.mark.asyncio
async def test_sync_team_jira_data_delta_sync(db_session, setup_team_with_credentials):
    """Test that delta sync doesn't duplicate tickets."""
    team, _, _ = setup_team_with_credentials

    # Create an existing ticket
    existing_ticket = Ticket(
        id="ticket-001",
        team_id=team.id,
        jira_key="TEST-001",
        title="Old title",
        status="Open",
        created_at=datetime.utcnow(),
        last_synced=datetime.utcnow(),
    )
    db_session.add(existing_ticket)
    await db_session.commit()

    # Mock updated issue
    mock_jira_issues = [
        {
            "key": "TEST-001",
            "fields": {
                "summary": "Updated title",
                "status": {"name": "In Progress"},
                "assignee": None,
                "created": "2024-05-01T10:00:00.000Z",
                "resolutiondate": None,
            },
            "changelog": {"histories": []},
        }
    ]

    with patch(
        "app.tasks.sync.JiraAPIService"
    ) as mock_jira_service:
        mock_instance = AsyncMock()
        mock_instance.verify_credentials = AsyncMock(return_value=True)
        mock_instance.fetch_issues = AsyncMock(return_value=mock_jira_issues)
        mock_jira_service.return_value = mock_instance

        result = await sync_team_jira_data(db_session, team.id)

    assert result["status"] == "success"
    assert result["tickets_synced"] == 0  # No new tickets, just updated

    # Verify ticket was updated, not duplicated
    tickets = await db_session.execute(
        select(Ticket).where(Ticket.jira_key == "TEST-001")
    )
    tickets_list = tickets.scalars().all()
    assert len(tickets_list) == 1
    assert tickets_list[0].title == "Updated title"
    assert tickets_list[0].status == "In Progress"


@pytest.mark.asyncio
async def test_sync_team_metrics_calculation(db_session, setup_team_with_credentials):
    """Test that metrics are calculated after sync."""
    team, manager, _ = setup_team_with_credentials

    # Create some tickets with transitions
    now = datetime.utcnow()
    ticket1 = Ticket(
        id="ticket-001",
        team_id=team.id,
        jira_key="TEST-001",
        title="Feature A",
        status="Done",
        created_at=now - timedelta(days=10),
        resolved_at=now,
        cycle_time_days=10.0,
        last_synced=now,
    )
    db_session.add(ticket1)

    ticket2 = Ticket(
        id="ticket-002",
        team_id=team.id,
        jira_key="TEST-002",
        title="Feature B",
        status="Open",
        created_at=now - timedelta(days=5),
        resolved_at=None,
        last_synced=now,
    )
    db_session.add(ticket2)

    # Add transitions for bounce detection
    trans1 = TicketTransition(
        id="trans-001",
        ticket_id="ticket-001",
        from_status=None,
        to_status="Open",
        transitioned_at=now - timedelta(days=10),
    )
    trans2 = TicketTransition(
        id="trans-002",
        ticket_id="ticket-001",
        from_status="Open",
        to_status="In Progress",
        transitioned_at=now - timedelta(days=8),
    )
    trans3 = TicketTransition(
        id="trans-003",
        ticket_id="ticket-001",
        from_status="In Progress",
        to_status="Done",
        transitioned_at=now,
    )
    db_session.add_all([trans1, trans2, trans3])

    await db_session.commit()

    # Mock Jira API to return empty (we already have tickets in DB)
    with patch(
        "app.tasks.sync.JiraAPIService"
    ) as mock_jira_service:
        mock_instance = AsyncMock()
        mock_instance.verify_credentials = AsyncMock(return_value=True)
        mock_instance.fetch_issues = AsyncMock(return_value=[])
        mock_jira_service.return_value = mock_instance

        result = await sync_team_jira_data(db_session, team.id)

    assert result["status"] == "success"

    # Verify metrics were created
    metrics = await db_session.execute(
        select(Metrics).where(
            (Metrics.team_id == team.id) & (Metrics.date == date.today())
        )
    )
    metrics_row = metrics.scalar_one_or_none()
    assert metrics_row is not None
    assert metrics_row.open_tickets == 1  # TEST-002 is open
    assert metrics_row.avg_cycle_time_days is not None


@pytest.mark.asyncio
async def test_sync_handles_errors_gracefully(db_session, setup_team_with_credentials):
    """Test that sync handles Jira API errors gracefully."""
    team, _, _ = setup_team_with_credentials

    with patch(
        "app.tasks.sync.JiraAPIService"
    ) as mock_jira_service:
        mock_instance = AsyncMock()
        mock_instance.verify_credentials = AsyncMock(return_value=True)
        mock_instance.fetch_issues = AsyncMock(
            side_effect=Exception("Jira API unavailable")
        )
        mock_jira_service.return_value = mock_instance

        result = await sync_team_jira_data(db_session, team.id)

    assert result["status"] == "error"
    assert "Jira API unavailable" in result["reason"]
