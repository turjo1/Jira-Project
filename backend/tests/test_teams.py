"""Tests for teams router endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.models import Team, User, Ticket, UserRole
from datetime import datetime, timedelta


class TestTeamsList:
    """Tests for GET /api/teams (list endpoint)."""

    @pytest.mark.asyncio
    async def test_list_teams_success(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        jwt_token_factory,
    ):
        """Test listing teams returns paginated results."""
        # Create 3 teams
        teams = []
        for i in range(3):
            team = Team(
                id=str(uuid4()),
                name=f"Team {i+1}",
                jira_project_key=f"T{i+1}",
                manager_id=test_manager.id,
            )
            db_session.add(team)
            teams.append(team)

        await db_session.commit()

        # Create JWT token for manager
        token = jwt_token_factory(user_id=test_manager.id)

        # Call endpoint
        response = await app_client.get(
            "/api/teams",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["teams"]) == 3
        assert data["skip"] == 0
        assert data["limit"] == 10

        # Verify team details
        for i, team_data in enumerate(data["teams"]):
            assert team_data["name"] == f"Team {i+1}"
            assert team_data["manager_id"] == test_manager.id
            assert team_data["member_count"] == 0

    @pytest.mark.asyncio
    async def test_list_teams_with_pagination(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        jwt_token_factory,
    ):
        """Test pagination parameters work correctly."""
        # Create 15 teams
        for i in range(15):
            team = Team(
                id=str(uuid4()),
                name=f"Team {i+1}",
                jira_project_key=f"T{i+1:02d}",
                manager_id=test_manager.id,
            )
            db_session.add(team)

        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)

        # Request first page with limit=5
        response = await app_client.get(
            "/api/teams?skip=0&limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 5
        assert data["total"] == 15
        assert data["skip"] == 0
        assert data["limit"] == 5

        # Request second page
        response = await app_client.get(
            "/api/teams?skip=5&limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 5
        assert data["skip"] == 5

    @pytest.mark.asyncio
    async def test_list_teams_invalid_pagination(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        jwt_token_factory,
    ):
        """Test invalid pagination parameters return 400."""
        token = jwt_token_factory(user_id=test_manager.id)

        # Negative skip
        response = await app_client.get(
            "/api/teams?skip=-1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

        # Limit > 100
        response = await app_client.get(
            "/api/teams?limit=101",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

        # Limit < 1
        response = await app_client.get(
            "/api/teams?limit=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_teams_only_own_teams(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_user_factory,
        jwt_token_factory,
    ):
        """Test that users only see their own teams."""
        # Create another manager
        other_manager = await test_user_factory(role=UserRole.MANAGER)

        # Create team for test_manager
        team1 = Team(
            id=str(uuid4()),
            name="Team 1",
            jira_project_key="T1",
            manager_id=test_manager.id,
        )
        db_session.add(team1)

        # Create team for other_manager
        team2 = Team(
            id=str(uuid4()),
            name="Team 2",
            jira_project_key="T2",
            manager_id=other_manager.id,
        )
        db_session.add(team2)

        await db_session.commit()

        # Get teams as test_manager
        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            "/api/teams",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["teams"][0]["name"] == "Team 1"

    @pytest.mark.asyncio
    async def test_list_teams_no_auth(self, app_client: AsyncClient):
        """Test that endpoint requires authentication."""
        response = await app_client.get("/api/teams")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_teams_with_members(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_user: User,
        jwt_token_factory,
    ):
        """Test that member_count is correct."""
        # Create team
        team = Team(
            id=str(uuid4()),
            name="Team",
            jira_project_key="T1",
            manager_id=test_manager.id,
        )
        db_session.add(team)
        await db_session.flush()

        # Add user to team
        test_user.team_id = team.id
        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            "/api/teams",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["teams"][0]["member_count"] == 1


class TestTeamsDetail:
    """Tests for GET /api/teams/{team_id} (detail endpoint)."""

    @pytest.mark.asyncio
    async def test_get_team_detail_success(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_team: Team,
        jwt_token_factory,
    ):
        """Test getting team detail returns correct data."""
        token = jwt_token_factory(user_id=test_manager.id)

        response = await app_client.get(
            f"/api/teams/{test_team.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_team.id
        assert data["name"] == test_team.name
        assert data["manager_id"] == test_manager.id
        assert isinstance(data["members"], list)

    @pytest.mark.asyncio
    async def test_get_team_detail_with_members(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_team: Team,
        test_user_factory,
        jwt_token_factory,
    ):
        """Test that team detail includes members with in-progress ticket counts."""
        # Create 2 team members
        member1 = await test_user_factory(name="Member 1")
        member2 = await test_user_factory(name="Member 2")

        # Add to team
        member1.team_id = test_team.id
        member2.team_id = test_team.id

        # Create in-progress tickets
        now = datetime.utcnow()
        ticket1 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="T-1",
            title="Ticket 1",
            assignee_id=member1.id,
            status="In Progress",
            created_at=now,
            last_synced=now,
        )
        ticket2 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="T-2",
            title="Ticket 2",
            assignee_id=member1.id,
            status="In Progress",
            created_at=now,
            last_synced=now,
        )
        ticket3 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="T-3",
            title="Ticket 3",
            assignee_id=member2.id,
            status="In Progress",
            created_at=now,
            last_synced=now,
        )

        db_session.add_all([ticket1, ticket2, ticket3])
        await db_session.commit()

        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            f"/api/teams/{test_team.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["members"]) == 2

        # Find members and check in-progress counts
        member_dict = {m["id"]: m for m in data["members"]}
        assert member_dict[member1.id]["tickets_in_progress"] == 2
        assert member_dict[member2.id]["tickets_in_progress"] == 1

    @pytest.mark.asyncio
    async def test_get_team_detail_404(
        self,
        app_client: AsyncClient,
        test_manager: User,
        jwt_token_factory,
    ):
        """Test that nonexistent team returns 404."""
        token = jwt_token_factory(user_id=test_manager.id)

        response = await app_client.get(
            f"/api/teams/{str(uuid4())}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_team_detail_403_unauthorized(
        self,
        app_client: AsyncClient,
        db_session: AsyncSession,
        test_manager: User,
        test_user_factory,
        jwt_token_factory,
    ):
        """Test that users cannot view teams they don't manage."""
        # Create another manager
        other_manager = await test_user_factory(role=UserRole.MANAGER)

        # Create team for other_manager
        other_team = Team(
            id=str(uuid4()),
            name="Other Team",
            jira_project_key="OT",
            manager_id=other_manager.id,
        )
        db_session.add(other_team)
        await db_session.commit()

        # Try to access as test_manager
        token = jwt_token_factory(user_id=test_manager.id)
        response = await app_client.get(
            f"/api/teams/{other_team.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_team_detail_no_auth(
        self,
        app_client: AsyncClient,
        test_team: Team,
    ):
        """Test that endpoint requires authentication."""
        response = await app_client.get(f"/api/teams/{test_team.id}")
        assert response.status_code == 401
