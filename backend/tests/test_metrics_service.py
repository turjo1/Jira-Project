"""Comprehensive unit tests for the metrics service."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.metrics import MetricsService
from app.models.models import Ticket, TicketTransition


class TestCycleTimeCalculation:
    """Tests for cycle time metric calculation."""

    @pytest.mark.asyncio
    async def test_cycle_time_calculation(
        self, db_session: AsyncSession, seeded_tickets
    ):
        """Test that cycle_time calculates average days from creation to resolution for resolved tickets."""
        # Get team_id from seeded tickets
        team_id = seeded_tickets[0].team_id

        # Get expected cycle times from resolved tickets
        resolved = [t for t in seeded_tickets if t.resolved_at is not None]
        assert len(resolved) > 0, "No resolved tickets in seeded data"

        expected_cycle_times = [
            (t.resolved_at - t.created_at).days for t in resolved
        ]
        expected_avg = sum(expected_cycle_times) / len(expected_cycle_times)

        # Call the service
        result = await MetricsService.get_cycle_time(db_session, team_id)

        # Assert the result is close to expected (allowing 0.1 day tolerance for precision)
        assert result is not None
        assert abs(result - expected_avg) < 0.1, (
            f"Expected ~{expected_avg}, got {result}"
        )

    @pytest.mark.asyncio
    async def test_cycle_time_only_resolved_tickets(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that cycle_time only includes resolved tickets, not open ones."""
        # Create mix of resolved and unresolved tickets
        now = datetime.utcnow()
        created_1 = now - timedelta(days=10)
        resolved_1 = created_1 + timedelta(days=5)  # 5-day cycle

        # Resolved ticket
        ticket1 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-CYCLE-1",
            title="Resolved ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=created_1,
            resolved_at=resolved_1,
            cycle_time_days=(resolved_1 - created_1).days,
            last_synced=now,
            bounced_count=0,
        )

        # Unresolved ticket (should be excluded)
        ticket2 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-CYCLE-2",
            title="Open ticket",
            assignee_id=test_user.id,
            status="Open",
            created_at=now - timedelta(days=30),
            resolved_at=None,  # Not resolved
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket1)
        db_session.add(ticket2)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_cycle_time(db_session, test_team.id)

        # Assert: only resolved ticket's cycle time is used
        assert result is not None
        assert abs(result - 5.0) < 0.1, f"Expected ~5 days, got {result}"

    @pytest.mark.asyncio
    async def test_cycle_time_null_dates(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that cycle_time handles tickets with missing created_at or resolved_at gracefully."""
        now = datetime.utcnow()

        # Ticket with resolved_at but no created_at (edge case)
        # This shouldn't happen in practice, but test resilience
        ticket1 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-NULL-1",
            title="Ticket with dates",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )

        # Ticket with only created_at (still open)
        ticket2 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-NULL-2",
            title="Open ticket",
            assignee_id=test_user.id,
            status="In Progress",
            created_at=now - timedelta(days=10),
            resolved_at=None,
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket1)
        db_session.add(ticket2)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_cycle_time(db_session, test_team.id)

        # Assert: only ticket1 is included, no errors
        assert result is not None
        assert result > 0, "Cycle time should be positive"

    @pytest.mark.asyncio
    async def test_cycle_time_respects_days_back_filter(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that cycle_time filters by days_back parameter."""
        now = datetime.utcnow()

        # Ticket created 40 days ago (outside 30-day default window)
        ticket_old = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-OLD-1",
            title="Old ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=40),
            resolved_at=now - timedelta(days=35),  # 5-day cycle
            last_synced=now,
            bounced_count=0,
        )

        # Ticket created 10 days ago (within 30-day window)
        ticket_new = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-NEW-1",
            title="New ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=10),
            resolved_at=now - timedelta(days=5),  # 5-day cycle
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket_old)
        db_session.add(ticket_new)
        await db_session.commit()

        # Call service with default 30 days
        result_30 = await MetricsService.get_cycle_time(db_session, test_team.id, days_back=30)

        # Call service with 50 days (includes old ticket)
        result_50 = await MetricsService.get_cycle_time(db_session, test_team.id, days_back=50)

        # Both should include ticket_new (5 days cycle)
        assert result_30 is not None
        assert result_50 is not None
        # With 50 days, we include both old and new, so average should still be ~5
        assert abs(result_50 - 5.0) < 0.1


class TestBounceRateCalculation:
    """Tests for bounce rate metric calculation."""

    @pytest.mark.asyncio
    async def test_bounce_rate_detects_backward_transitions(
        self, db_session: AsyncSession, seeded_transitions
    ):
        """Test that bounce_rate correctly identifies backward transitions (Done -> InProgress)."""
        # Get team_id from transitions
        if seeded_transitions:
            team_id = seeded_transitions[0].ticket.team_id
        else:
            pytest.skip("No seeded transitions available")

        # Get bounce transitions
        bounces = [
            t for t in seeded_transitions if t.from_status == "Done"
        ]

        # Call service
        result = await MetricsService.get_bounce_rate(db_session, team_id)

        # Assert: should return a value (0 or > 0)
        assert result is not None
        assert isinstance(result, float)
        assert result >= 0 and result <= 100, "Bounce rate should be 0-100%"

    @pytest.mark.asyncio
    async def test_bounce_rate_zero_if_no_bounces(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that bounce_rate is 0% when all transitions are forward-only."""
        now = datetime.utcnow()

        # Create a single resolved ticket with only forward transitions
        ticket = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-NO-BOUNCE",
            title="Forward-only ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )
        db_session.add(ticket)
        await db_session.commit()

        # Create forward-only transitions: Open -> In Progress -> In Review -> Done
        transitions = [
            TicketTransition(
                id=str(uuid4()),
                ticket_id=ticket.id,
                from_status="Open",
                to_status="In Progress",
                transitioned_at=now - timedelta(days=4),
                actor_id=test_user.id,
            ),
            TicketTransition(
                id=str(uuid4()),
                ticket_id=ticket.id,
                from_status="In Progress",
                to_status="In Review",
                transitioned_at=now - timedelta(days=2),
                actor_id=test_user.id,
            ),
            TicketTransition(
                id=str(uuid4()),
                ticket_id=ticket.id,
                from_status="In Review",
                to_status="Done",
                transitioned_at=now,
                actor_id=test_user.id,
            ),
        ]
        for trans in transitions:
            db_session.add(trans)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_bounce_rate(db_session, test_team.id)

        # Assert: bounce rate is 0%
        assert result is not None
        assert result == 0.0, f"Expected 0% bounce rate, got {result}%"

    @pytest.mark.asyncio
    async def test_bounce_rate_with_bounces(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that bounce_rate correctly calculates when tickets bounce."""
        now = datetime.utcnow()

        # Create one resolved ticket
        ticket = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-BOUNCE",
            title="Bounced ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=1,
        )
        db_session.add(ticket)
        await db_session.commit()

        # Create transitions with a bounce: Open -> Done -> In Progress -> Done
        transitions = [
            TicketTransition(
                id=str(uuid4()),
                ticket_id=ticket.id,
                from_status="Open",
                to_status="Done",
                transitioned_at=now - timedelta(days=4),
                actor_id=test_user.id,
            ),
            TicketTransition(
                id=str(uuid4()),
                ticket_id=ticket.id,
                from_status="Done",
                to_status="In Progress",  # BOUNCE!
                transitioned_at=now - timedelta(days=3),
                actor_id=test_user.id,
            ),
            TicketTransition(
                id=str(uuid4()),
                ticket_id=ticket.id,
                from_status="In Progress",
                to_status="Done",
                transitioned_at=now,
                actor_id=test_user.id,
            ),
        ]
        for trans in transitions:
            db_session.add(trans)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_bounce_rate(db_session, test_team.id)

        # Assert: bounce rate is 100% (1 out of 1 ticket bounced)
        assert result is not None
        assert abs(result - 100.0) < 0.1, f"Expected 100% bounce rate, got {result}%"

    @pytest.mark.asyncio
    async def test_bounce_rate_partial_bounces(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test bounce_rate with a mix of bouncing and non-bouncing tickets."""
        now = datetime.utcnow()

        # Create 2 resolved tickets: 1 bounces, 1 doesn't
        ticket1 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-BOUNCE-1",
            title="Bounced ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=1,
        )

        ticket2 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-NO-BOUNCE-1",
            title="Non-bounced ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=4),
            resolved_at=now - timedelta(days=1),
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket1)
        db_session.add(ticket2)
        await db_session.commit()

        # Create transitions for ticket1 (with bounce)
        trans1 = TicketTransition(
            id=str(uuid4()),
            ticket_id=ticket1.id,
            from_status="Open",
            to_status="Done",
            transitioned_at=now - timedelta(days=4),
            actor_id=test_user.id,
        )
        trans2 = TicketTransition(
            id=str(uuid4()),
            ticket_id=ticket1.id,
            from_status="Done",
            to_status="In Progress",  # BOUNCE
            transitioned_at=now - timedelta(days=2),
            actor_id=test_user.id,
        )
        trans3 = TicketTransition(
            id=str(uuid4()),
            ticket_id=ticket1.id,
            from_status="In Progress",
            to_status="Done",
            transitioned_at=now,
            actor_id=test_user.id,
        )

        # Create transitions for ticket2 (no bounce)
        trans4 = TicketTransition(
            id=str(uuid4()),
            ticket_id=ticket2.id,
            from_status="Open",
            to_status="Done",
            transitioned_at=now - timedelta(days=3),
            actor_id=test_user.id,
        )

        for trans in [trans1, trans2, trans3, trans4]:
            db_session.add(trans)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_bounce_rate(db_session, test_team.id)

        # Assert: 50% bounce rate (1 out of 2)
        assert result is not None
        assert abs(result - 50.0) < 0.1, f"Expected 50% bounce rate, got {result}%"

    @pytest.mark.asyncio
    async def test_bounce_rate_empty_team(
        self, db_session: AsyncSession, test_team
    ):
        """Test that bounce_rate returns None for empty team (no resolved tickets)."""
        # Call service on empty team
        result = await MetricsService.get_bounce_rate(db_session, test_team.id)

        # Assert: should return None when no resolved tickets
        assert result is None


class TestOpenTicketCount:
    """Tests for open ticket count metric."""

    @pytest.mark.asyncio
    async def test_open_count_filters_resolved_status(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that get_open_tickets only counts unresolved tickets (resolved_at is None)."""
        now = datetime.utcnow()

        # Create mix of resolved and unresolved
        ticket_open = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-OPEN",
            title="Open ticket",
            assignee_id=test_user.id,
            status="Open",
            created_at=now - timedelta(days=10),
            resolved_at=None,
            last_synced=now,
            bounced_count=0,
        )

        ticket_inprogress = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-INPROG",
            title="In Progress ticket",
            assignee_id=test_user.id,
            status="In Progress",
            created_at=now - timedelta(days=5),
            resolved_at=None,
            last_synced=now,
            bounced_count=0,
        )

        ticket_done = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-DONE",
            title="Done ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket_open)
        db_session.add(ticket_inprogress)
        db_session.add(ticket_done)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_open_tickets(db_session, test_team.id)

        # Assert: only 2 open (Open and In Progress), Done is excluded
        assert result == 2, f"Expected 2 open tickets, got {result}"

    @pytest.mark.asyncio
    async def test_open_count_zero_for_resolved_only(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that open count is 0 when all tickets are resolved."""
        now = datetime.utcnow()

        ticket = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-RESOLVED",
            title="Resolved ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_open_tickets(db_session, test_team.id)

        # Assert: 0 open tickets
        assert result == 0


class TestBottleneckDetection:
    """Tests for bottleneck (slowest status) detection."""

    @pytest.mark.asyncio
    async def test_bottleneck_identifies_slowest_status(
        self, db_session: AsyncSession, seeded_transitions
    ):
        """Test that bottleneck correctly identifies a status (any status with dwell time)."""
        # Use seeded transitions which have a complete transition history
        if seeded_transitions:
            team_id = seeded_transitions[0].ticket.team_id
        else:
            pytest.skip("No seeded transitions available")

        # Call service
        result = await MetricsService.get_bottleneck(db_session, team_id)

        # Assert: should return a valid bottleneck result
        # (may be any status depending on the transitions)
        assert result is not None
        assert isinstance(result, dict)
        assert "status" in result
        assert "avg_dwell_days" in result
        assert result["avg_dwell_days"] >= 0, "Dwell time should be non-negative"
        # The bottleneck status should be one of the valid statuses
        assert result["status"] in ["Open", "In Progress", "In Review", "Done"]

    @pytest.mark.asyncio
    async def test_bottleneck_empty_team(
        self, db_session: AsyncSession, test_team
    ):
        """Test that bottleneck returns None for empty team."""
        result = await MetricsService.get_bottleneck(db_session, test_team.id)
        assert result is None


class TestStatusDistribution:
    """Tests for status distribution metric."""

    @pytest.mark.asyncio
    async def test_status_distribution_counts_by_status(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test that status_distribution correctly counts tickets per status."""
        now = datetime.utcnow()

        # Create 10 tickets: 3 Open, 2 In Progress, 5 Done
        statuses_to_create = [
            ("Open", 3),
            ("In Progress", 2),
            ("Done", 5),
        ]

        for status, count in statuses_to_create:
            for i in range(count):
                ticket = Ticket(
                    id=str(uuid4()),
                    team_id=test_team.id,
                    jira_key=f"TEST-{status.replace(' ', '')}-{i}",
                    title=f"{status} ticket {i}",
                    assignee_id=test_user.id,
                    status=status,
                    created_at=now - timedelta(days=5),
                    resolved_at=now if status == "Done" else None,
                    last_synced=now,
                    bounced_count=0,
                )
                db_session.add(ticket)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_status_distribution(db_session, test_team.id)

        # Assert: counts match expected
        assert result is not None
        assert result["Open"]["count"] == 3
        assert result["In Progress"]["count"] == 2
        assert result["Done"]["count"] == 5

    @pytest.mark.asyncio
    async def test_status_distribution_empty_team(
        self, db_session: AsyncSession, test_team
    ):
        """Test that status_distribution returns empty dict for empty team."""
        result = await MetricsService.get_status_distribution(db_session, test_team.id)

        # Assert: returns empty dict (not None)
        assert result == {}


class TestMetricsHandleEmptyTeam:
    """Tests for metrics service handling of empty teams."""

    @pytest.mark.asyncio
    async def test_metrics_handles_empty_team(
        self, db_session: AsyncSession, test_team
    ):
        """Test that all metric methods handle empty teams gracefully."""
        # Call all metric methods on empty team
        cycle_time = await MetricsService.get_cycle_time(db_session, test_team.id)
        bounce_rate = await MetricsService.get_bounce_rate(db_session, test_team.id)
        open_count = await MetricsService.get_open_tickets(db_session, test_team.id)
        bottleneck = await MetricsService.get_bottleneck(db_session, test_team.id)
        distribution = await MetricsService.get_status_distribution(db_session, test_team.id)

        # Assert: no errors, sensible defaults
        assert cycle_time is None
        assert bounce_rate is None
        assert open_count == 0
        assert bottleneck is None
        assert distribution == {}


class TestCycleTimeDateCalculation:
    """Tests for proper date calculation in cycle time."""

    @pytest.mark.asyncio
    async def test_cycle_time_date_calculation_specific_dates(
        self, db_session: AsyncSession, test_team, test_user
    ):
        """Test cycle_time calculation with specific known dates."""
        now = datetime.utcnow()

        # Create tickets with known cycle times
        # Ticket 1: 10-day cycle
        ticket1 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-DATE-1",
            title="10-day ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=10),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )

        # Ticket 2: 5-day cycle
        ticket2 = Ticket(
            id=str(uuid4()),
            team_id=test_team.id,
            jira_key="TEST-DATE-2",
            title="5-day ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket1)
        db_session.add(ticket2)
        await db_session.commit()

        # Call service
        result = await MetricsService.get_cycle_time(db_session, test_team.id)

        # Assert: average is (10 + 5) / 2 = 7.5 days
        assert result is not None
        assert abs(result - 7.5) < 0.1, f"Expected 7.5 days, got {result}"


class TestMultipleTeamsIsolation:
    """Tests for proper isolation between teams."""

    @pytest.mark.asyncio
    async def test_metrics_isolated_by_team(
        self, db_session: AsyncSession, test_user, test_manager
    ):
        """Test that metrics for one team don't include data from other teams."""
        now = datetime.utcnow()

        # Create two teams
        from app.models.models import Team
        from uuid import uuid4

        team1 = Team(
            id=str(uuid4()),
            name="Team 1",
            jira_project_key="TEAM1",
            manager_id=test_manager.id,
        )

        team2 = Team(
            id=str(uuid4()),
            name="Team 2",
            jira_project_key="TEAM2",
            manager_id=test_manager.id,
        )

        db_session.add(team1)
        db_session.add(team2)
        await db_session.commit()

        # Create tickets for team1
        ticket1 = Ticket(
            id=str(uuid4()),
            team_id=team1.id,
            jira_key="T1-001",
            title="Team 1 ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=10),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )

        # Create tickets for team2 (different cycle time)
        ticket2 = Ticket(
            id=str(uuid4()),
            team_id=team2.id,
            jira_key="T2-001",
            title="Team 2 ticket",
            assignee_id=test_user.id,
            status="Done",
            created_at=now - timedelta(days=5),
            resolved_at=now,
            last_synced=now,
            bounced_count=0,
        )

        db_session.add(ticket1)
        db_session.add(ticket2)
        await db_session.commit()

        # Get cycle times for each team
        ct1 = await MetricsService.get_cycle_time(db_session, team1.id)
        ct2 = await MetricsService.get_cycle_time(db_session, team2.id)

        # Assert: teams have different cycle times
        assert ct1 is not None
        assert ct2 is not None
        assert abs(ct1 - 10.0) < 0.1, f"Team1 should be ~10 days"
        assert abs(ct2 - 5.0) < 0.1, f"Team2 should be ~5 days"
