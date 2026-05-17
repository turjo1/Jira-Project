"""Tests for developers router endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.models import Team, User, Ticket, UserRole


class TestDevelopersDetail:
    """Tests for GET /api/developers/{dev_id} (detail endpoint)."""

    @pytest.mark.asyncio
    async def test_get_developer_detail_success(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_team: Team,
        test_user: User,
        jwt_token_factory,
    ):
        """Test getting developer detail returns basic information."""
        # Add test_user to test_team
        test_user.team_id = test_team.id
        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)

        response = await app_client.get(
            f"/api/developers/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert "metrics" in data

    @pytest.mark.asyncio
    async def test_get_developer_detail_with_metrics(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_team: Team,
        test_user: User,
        jwt_token_factory,
    ):
        """Test that developer metrics are calculated correctly."""
        # Add test_user to test_team
        test_user.team_id = test_team.id
        await db_session.commit()

        # Create some resolved tickets
        now = datetime.utcnow()
        resolved_tickets = []

        for i in range(5):
            created = now - timedelta(days=10 - i)
            resolved = created + timedelta(days=3)

            ticket = Ticket(
                id=str(uuid4()),
                team_id=test_team.id,
                jira_key=f"T-{i+1}",
                title=f"Ticket {i+1}",
                assignee_id=test_user.id,
                status="Done",
                created_at=created,
                resolved_at=resolved,
                cycle_time_days=3.0,
                last_synced=now,
                bounced_count=0,
            )
            db_session.add(ticket)
            resolved_tickets.append(ticket)

        # Create some in-progress tickets
        for i in range(2):
            ticket = Ticket(
                id=str(uuid4()),
                team_id=test_team.id,
                jira_key=f"T-{i+10}",
                title=f"In Progress {i+1}",
                assignee_id=test_user.id,
                status="In Progress",
                created_at=now,
                last_synced=now,
            )
            db_session.add(ticket)

        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            f"/api/developers/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        metrics = data["metrics"]
        assert metrics["tickets_resolved"] == 5
        assert metrics["avg_cycle_time"] == 3.0
        assert metrics["bounce_contribution"] == 0.0  # No bounces
        assert metrics["current_in_progress"] == 2

    @pytest.mark.asyncio
    async def test_get_developer_detail_with_bounce_contribution(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_team: Team,
        test_user: User,
        jwt_token_factory,
    ):
        """Test bounce contribution calculation."""
        # Add test_user to test_team
        test_user.team_id = test_team.id
        await db_session.commit()

        now = datetime.utcnow()

        # Create 10 resolved tickets: 2 with bounces, 8 without
        for i in range(10):
            created = now - timedelta(days=10)
            resolved = created + timedelta(days=3)

            ticket = Ticket(
                id=str(uuid4()),
                team_id=test_team.id,
                jira_key=f"T-{i+1}",
                title=f"Ticket {i+1}",
                assignee_id=test_user.id,
                status="Done",
                created_at=created,
                resolved_at=resolved,
                cycle_time_days=3.0,
                last_synced=now,
                bounced_count=1 if i < 2 else 0,  # 2 bounced tickets
            )
            db_session.add(ticket)

        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            f"/api/developers/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        metrics = data["metrics"]
        assert metrics["tickets_resolved"] == 10
        assert metrics["bounce_contribution"] == 20.0  # 2/10 * 100

    @pytest.mark.asyncio
    async def test_get_developer_detail_no_resolved_tickets(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_team: Team,
        test_user: User,
        jwt_token_factory,
    ):
        """Test metrics when developer has no resolved tickets."""
        # Add test_user to test_team
        test_user.team_id = test_team.id
        await db_session.commit()

        now = datetime.utcnow()

        # Create only in-progress tickets
        for i in range(3):
            ticket = Ticket(
                id=str(uuid4()),
                team_id=test_team.id,
                jira_key=f"T-{i+1}",
                title=f"Ticket {i+1}",
                assignee_id=test_user.id,
                status="In Progress",
                created_at=now,
                last_synced=now,
            )
            db_session.add(ticket)

        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            f"/api/developers/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        metrics = data["metrics"]
        assert metrics["tickets_resolved"] == 0
        assert metrics["avg_cycle_time"] is None
        assert metrics["bounce_contribution"] == 0.0
        assert metrics["current_in_progress"] == 3

    @pytest.mark.asyncio
    async def test_get_developer_detail_404(
        self,
        app_client: AsyncClient,
        test_manager: User,
        jwt_token_factory,
    ):
        """Test that nonexistent developer returns 404."""
        token = jwt_token_factory(user_id=test_manager.id)

        response = await app_client.get(
            f"/api/developers/{str(uuid4())}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_developer_detail_403_not_in_user_teams(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_user_factory,
        jwt_token_factory,
    ):
        """Test that user cannot view developers not in their teams."""
        # Create another manager and their team
        other_manager = await test_user_factory(role=UserRole.MANAGER)
        other_team = Team(
            id=str(uuid4()),
            name="Other Team",
            jira_project_key="OT",
            manager_id=other_manager.id,
        )
        db_session.add(other_team)
        await db_session.flush()

        # Create developer in other team
        other_developer = await test_user_factory()
        other_developer.team_id = other_team.id
        await db_session.commit()

        # Try to access as test_manager
        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            f"/api/developers/{other_developer.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_developer_detail_no_auth(
        self,
        app_client: AsyncClient,
        test_user: User,
    ):
        """Test that endpoint requires authentication."""
        response = await app_client.get(f"/api/developers/{test_user.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_developer_detail_metrics_from_multiple_teams(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_team: Team,
        test_user_factory,
        jwt_token_factory,
    ):
        """Test that developer metrics include tickets from all teams the manager oversees."""
        # Create another team managed by test_manager
        team2 = Team(
            id=str(uuid4()),
            name="Team 2",
            jira_project_key="T2",
            manager_id=test_manager.id,
        )
        db_session.add(team2)

        # Create developer in team2
        developer = await test_user_factory()
        developer.team_id = team2.id
        await db_session.flush()

        now = datetime.utcnow()

        # Create tickets in both teams assigned to developer
        # 3 resolved in team1
        for i in range(3):
            ticket = Ticket(
                id=str(uuid4()),
                team_id=test_team.id,
                jira_key=f"T1-{i+1}",
                title=f"Team1 Ticket {i+1}",
                assignee_id=developer.id,
                status="Done",
                created_at=now - timedelta(days=5),
                resolved_at=now,
                cycle_time_days=5.0,
                last_synced=now,
            )
            db_session.add(ticket)

        # 2 resolved in team2
        for i in range(2):
            ticket = Ticket(
                id=str(uuid4()),
                team_id=team2.id,
                jira_key=f"T2-{i+1}",
                title=f"Team2 Ticket {i+1}",
                assignee_id=developer.id,
                status="Done",
                created_at=now - timedelta(days=5),
                resolved_at=now,
                cycle_time_days=5.0,
                last_synced=now,
            )
            db_session.add(ticket)

        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            f"/api/developers/{developer.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should see tickets from both teams
        metrics = data["metrics"]
        assert metrics["tickets_resolved"] == 5
        assert metrics["avg_cycle_time"] == 5.0
