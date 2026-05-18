"""Celery task for syncing Jira data every 5 minutes."""
import asyncio
from datetime import datetime, date
from typing import Optional, Dict, Any

from celery import Celery, Task
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models import Ticket, TicketTransition, Team, User, Credentials
from app.services.jira import JiraAPIService
from app.services.metrics import MetricsService
from app.services.auth import TokenService
from app.websocket.broadcaster import MetricsBroadcaster
from cryptography.fernet import Fernet

log = structlog.get_logger(__name__)
settings = get_settings()


class SyncTask(Task):
    """Base task class with database session management."""

    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        async with async_session_maker() as session:
            return session


# Initialize Celery app
celery_app = Celery(
    "jira_analytics",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "sync-jira-every-5min": {
            "task": "app.tasks.sync.sync_jira_data",
            "schedule": 300.0,  # 5 minutes in seconds
            "options": {"queue": "sync"},
        },
    },
)


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt encrypted Jira token using AES.

    Args:
        encrypted_token: Base64-encoded encrypted token

    Returns:
        Decrypted token string
    """
    try:
        cipher = Fernet(settings.aes_encryption_key.encode())
        decrypted = cipher.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except Exception as e:
        log.error("token_decryption_failed", error=str(e))
        raise


async def sync_team_jira_data(
    session: AsyncSession, team_id: str
) -> Dict[str, Any]:
    """
    Sync Jira tickets for a single team.

    Steps:
    1. Fetch team and credentials
    2. Query Jira API for all tickets
    3. Upsert Ticket rows (delta sync)
    4. Create/update TicketTransition records
    5. Recalculate metrics
    6. Upsert Metrics row

    Args:
        session: Database session
        team_id: Team ID to sync

    Returns:
        Dictionary with sync status and counts
    """
    try:
        log.info("sync_team_start", team_id=team_id)

        # Step 1: Get team and credentials
        team = await session.execute(
            select(Team).where(Team.id == team_id)
        )
        team = team.scalar_one_or_none()

        if not team:
            log.warning("team_not_found", team_id=team_id)
            return {"status": "skip", "reason": "Team not found", "team_id": team_id}

        # Get manager's credentials (assume manager has Jira credentials)
        creds = await session.execute(
            select(Credentials).where(Credentials.user_id == team.manager_id)
        )
        creds = creds.scalar_one_or_none()

        if not creds:
            log.warning("no_credentials", team_id=team_id, user_id=team.manager_id)
            return {
                "status": "skip",
                "reason": "No Jira credentials found",
                "team_id": team_id,
            }

        # Decrypt Jira token
        try:
            jira_token = decrypt_token(creds.jira_token_encrypted)
        except Exception as e:
            log.error("token_decrypt_error", team_id=team_id, error=str(e))
            return {
                "status": "error",
                "reason": "Failed to decrypt Jira token",
                "team_id": team_id,
            }

        # Step 2: Initialize Jira service and fetch issues
        jira_service = JiraAPIService(creds.jira_instance_url, jira_token)

        # Verify credentials first
        is_valid = await jira_service.verify_credentials()
        if not is_valid:
            log.warning("invalid_jira_credentials", team_id=team_id)
            return {
                "status": "error",
                "reason": "Invalid Jira credentials",
                "team_id": team_id,
            }

        # Build JQL to fetch issues from team's project
        jql = f"project = {team.jira_project_key}"
        log.info("fetching_jira_issues", team_id=team_id, jql=jql)

        jira_issues = await jira_service.fetch_issues(jql)
        log.info("fetched_jira_issues", team_id=team_id, count=len(jira_issues))

        # Step 3: Upsert Ticket rows (delta sync)
        tickets_upserted = 0
        now = datetime.utcnow()

        for issue in jira_issues:
            jira_key = issue["key"]
            fields = issue["fields"]

            # Check if ticket exists
            existing = await session.execute(
                select(Ticket).where(Ticket.jira_key == jira_key)
            )
            ticket = existing.scalar_one_or_none()

            # Map assignee
            assignee_id = None
            if fields.get("assignee"):
                assignee_result = await session.execute(
                    select(User).where(
                        User.jira_user_id == fields["assignee"].get("accountId")
                    )
                )
                assignee_user = assignee_result.scalar_one_or_none()
                assignee_id = assignee_user.id if assignee_user else None

            # Parse timestamps
            created_at = JiraAPIService.parse_jira_timestamp(fields.get("created"))
            resolved_at = JiraAPIService.parse_jira_timestamp(fields.get("resolutiondate"))

            # Determine cycle time
            cycle_time_days = None
            if created_at and resolved_at:
                delta = resolved_at - created_at
                cycle_time_days = float(delta.total_seconds() / 86400)

            if ticket:
                # Update existing ticket
                ticket.title = fields.get("summary", "")
                ticket.status = fields.get("status", {}).get("name", "Unknown")
                ticket.assignee_id = assignee_id
                ticket.resolved_at = resolved_at
                ticket.cycle_time_days = cycle_time_days
                ticket.last_synced = now
            else:
                # Create new ticket
                ticket = Ticket(
                    team_id=team_id,
                    jira_key=jira_key,
                    title=fields.get("summary", ""),
                    status=fields.get("status", {}).get("name", "Unknown"),
                    assignee_id=assignee_id,
                    created_at=created_at or now,
                    resolved_at=resolved_at,
                    cycle_time_days=cycle_time_days,
                    last_synced=now,
                )
                tickets_upserted += 1

            session.add(ticket)

        await session.flush()  # Flush to generate ticket IDs for new tickets

        # Step 4: Create TicketTransition records (audit log)
        transitions_created = 0

        for issue in jira_issues:
            jira_key = issue["key"]

            # Get the ticket we just upserted
            ticket_result = await session.execute(
                select(Ticket).where(Ticket.jira_key == jira_key)
            )
            ticket = ticket_result.scalar_one()

            # Process changelog
            changelog = issue.get("changelog", {})
            histories = changelog.get("histories", [])

            for history in histories:
                for item in history.get("items", []):
                    if item.get("field") == "status":
                        from_status = item.get("fromString")
                        to_status = item.get("toString")
                        transitioned_at = JiraAPIService.parse_jira_timestamp(
                            history.get("created")
                        )

                        if not transitioned_at:
                            continue

                        # Check if transition already exists (delta sync)
                        existing_trans = await session.execute(
                            select(TicketTransition).where(
                                (TicketTransition.ticket_id == ticket.id)
                                & (TicketTransition.from_status == from_status)
                                & (TicketTransition.to_status == to_status)
                                & (TicketTransition.transitioned_at == transitioned_at)
                            )
                        )

                        if not existing_trans.scalar_one_or_none():
                            # Find actor (who made the transition)
                            actor_id = None
                            if history.get("author"):
                                actor_result = await session.execute(
                                    select(User).where(
                                        User.jira_user_id
                                        == history["author"].get("accountId")
                                    )
                                )
                                actor_user = actor_result.scalar_one_or_none()
                                actor_id = actor_user.id if actor_user else None

                            # Create transition record
                            transition = TicketTransition(
                                ticket_id=ticket.id,
                                from_status=from_status,
                                to_status=to_status,
                                transitioned_at=transitioned_at,
                                actor_id=actor_id,
                            )
                            session.add(transition)
                            transitions_created += 1

        await session.commit()
        log.info(
            "tickets_and_transitions_synced",
            team_id=team_id,
            tickets=tickets_upserted,
            transitions=transitions_created,
        )

        # Step 5: Recalculate metrics
        metrics_service = MetricsService()

        cycle_time = await metrics_service.get_cycle_time(session, team_id)
        bounce_rate = await metrics_service.get_bounce_rate(session, team_id)
        open_tickets = await metrics_service.get_open_tickets(session, team_id)
        bottleneck_info = await metrics_service.get_bottleneck(session, team_id)

        from app.models.models import Metrics

        # Step 6: Upsert Metrics row
        today = date.today()

        metrics_result = await session.execute(
            select(Metrics).where(
                (Metrics.team_id == team_id) & (Metrics.date == today)
            )
        )
        metrics = metrics_result.scalar_one_or_none()

        if metrics:
            # Update existing metrics
            metrics.avg_cycle_time_days = cycle_time
            metrics.bounce_rate = bounce_rate
            metrics.open_tickets = open_tickets
            metrics.bottleneck_status = (
                bottleneck_info.get("status") if bottleneck_info else None
            )
        else:
            # Create new metrics record
            metrics = Metrics(
                team_id=team_id,
                date=today,
                avg_cycle_time_days=cycle_time,
                bounce_rate=bounce_rate,
                open_tickets=open_tickets,
                bottleneck_status=(
                    bottleneck_info.get("status") if bottleneck_info else None
                ),
            )

        session.add(metrics)
        await session.commit()

        log.info(
            "metrics_calculated",
            team_id=team_id,
            cycle_time=cycle_time,
            bounce_rate=bounce_rate,
            open_tickets=open_tickets,
            bottleneck=bottleneck_info.get("status") if bottleneck_info else None,
        )

        # Broadcast metrics update to WebSocket clients via Redis pub/sub
        bottleneck_status = bottleneck_info.get("status") if bottleneck_info else None
        MetricsBroadcaster.broadcast_metrics_update(
            team_id=team_id,
            cycle_time=cycle_time,
            bounce_rate=bounce_rate,
            open_tickets=open_tickets,
            bottleneck=bottleneck_status,
        )

        return {
            "status": "success",
            "team_id": team_id,
            "tickets_synced": len(jira_issues),
            "transitions_created": transitions_created,
            "cycle_time": cycle_time,
            "bounce_rate": bounce_rate,
            "open_tickets": open_tickets,
        }

    except Exception as e:
        log.error("sync_team_failed", team_id=team_id, error=str(e), exc_info=True)
        return {
            "status": "error",
            "team_id": team_id,
            "reason": str(e),
        }


@celery_app.task(bind=True, name="app.tasks.sync.sync_jira_data")
def sync_jira_data(self) -> Dict[str, Any]:
    """
    Celery task to sync Jira data for all teams every 5 minutes.

    Runs all team syncs in parallel and collects results.
    """

    async def run_sync():
        """Run the async sync operation."""
        async with async_session_maker() as session:
            # Fetch all active teams
            teams_result = await session.execute(select(Team))
            teams = teams_result.scalars().all()

            if not teams:
                log.info("no_teams_to_sync")
                return {"status": "skip", "reason": "No teams found"}

            log.info("sync_job_start", team_count=len(teams))

            # Sync all teams (can be parallelized further with Celery chord/group)
            results = []
            for team in teams:
                result = await sync_team_jira_data(session, team.id)
                results.append(result)

            # Summary
            successful = sum(
                1 for r in results if r.get("status") == "success"
            )
            failed = sum(
                1 for r in results if r.get("status") == "error"
            )
            skipped = sum(
                1 for r in results if r.get("status") == "skip"
            )

            log.info(
                "sync_job_complete",
                total_teams=len(teams),
                successful=successful,
                failed=failed,
                skipped=skipped,
            )

            return {
                "status": "complete",
                "total_teams": len(teams),
                "successful": successful,
                "failed": failed,
                "skipped": skipped,
                "results": results,
            }

    # Run async task
    return asyncio.run(run_sync())
