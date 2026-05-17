"""Dashboard API router."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models import Team, Ticket, TicketTransition, User, Metrics
from app.schemas import DashboardMetrics, MetricTile, StatusDistributionItem, TeamActivityItem
from app.services import MetricsService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/{team_id}/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    team_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> DashboardMetrics:
    """Get complete dashboard metrics for a team."""

    # Verify team exists
    stmt = select(Team).where(Team.id == team_id)
    team = await session.execute(stmt)
    if not team.scalar():
        raise HTTPException(status_code=404, detail="Team not found")

    # Calculate current metrics
    cycle_time = await MetricsService.get_cycle_time(session, team_id)
    bounce_rate = await MetricsService.get_bounce_rate(session, team_id)
    open_tickets = await MetricsService.get_open_tickets(session, team_id)
    bottleneck = await MetricsService.get_bottleneck(session, team_id)
    status_distribution = await MetricsService.get_status_distribution(session, team_id)

    # Get prior metrics (30 days ago) for comparison
    prior_date = datetime.now() - timedelta(days=30)
    prior_metrics_stmt = select(Metrics).where(
        and_(
            Metrics.team_id == team_id,
            Metrics.date <= prior_date.date(),
        )
    ).order_by(Metrics.date.desc()).limit(1)

    prior_metrics_result = await session.execute(prior_metrics_stmt)
    prior_metrics = prior_metrics_result.scalar()

    # Calculate deltas
    cycle_time_delta = 0
    cycle_time_trend = "neutral"
    if prior_metrics and prior_metrics.avg_cycle_time_days and cycle_time:
        cycle_time_delta = cycle_time - prior_metrics.avg_cycle_time_days
        cycle_time_trend = "down" if cycle_time_delta < 0 else "up"
    elif cycle_time and cycle_time < 5.5:
        cycle_time_trend = "down"

    bounce_rate_delta = 0
    bounce_rate_trend = "neutral"
    if prior_metrics and prior_metrics.bounce_rate and bounce_rate is not None:
        bounce_rate_delta = bounce_rate - prior_metrics.bounce_rate
        bounce_rate_trend = "down" if bounce_rate_delta < 0 else "up"
    elif bounce_rate and bounce_rate < 13:
        bounce_rate_trend = "down"

    # Count tickets in bottleneck status
    bottleneck_count = 0
    if bottleneck:
        bottleneck_status = bottleneck["status"]
        bottleneck_count = status_distribution.get(bottleneck_status, {}).get("count", 0)

    # Build metric tiles
    metrics = [
        MetricTile(
            title="Open tickets",
            value=str(open_tickets),
            unit="",
            comparison=f"{open_tickets} open",
            trend=None,
        ),
        MetricTile(
            title="Avg. cycle time",
            value=f"{cycle_time:.1f}" if cycle_time else "N/A",
            unit="days" if cycle_time else "",
            comparison=f"{cycle_time_delta:+.1f}d vs prior 30 days" if cycle_time else "N/A",
            trend=cycle_time_trend,
        ),
        MetricTile(
            title="QA bounce rate",
            value=f"{bounce_rate:.0f}" if bounce_rate is not None else "0",
            unit="%" if bounce_rate is not None else "",
            comparison=f"{bounce_rate_delta:+.1f}% pts vs prior 30 days" if bounce_rate is not None else "N/A",
            trend=bounce_rate_trend,
        ),
        MetricTile(
            title="Current bottleneck",
            value=f"{bottleneck['avg_dwell_days']:.1f}d" if bottleneck else "N/A",
            unit="",
            comparison=f"{bottleneck['status']} {bottleneck_count} tickets" if bottleneck else "",
            trend="down" if bottleneck and bottleneck['avg_dwell_days'] < 3 else "up",
        ),
    ]

    # Convert status distribution
    dist_items = {
        status: StatusDistributionItem(
            status=status,
            count=data["count"],
            avg_dwell_days=data["avg_dwell_days"],
        )
        for status, data in status_distribution.items()
    }

    # Get recent activity
    stmt = (
        select(TicketTransition, User, Ticket)
        .join(User, User.id == TicketTransition.actor_id, isouter=True)
        .join(Ticket, Ticket.id == TicketTransition.ticket_id)
        .where(Ticket.team_id == team_id)
        .order_by(TicketTransition.transitioned_at.desc())
        .limit(10)
    )
    result = await session.execute(stmt)
    activity = []
    for transition, actor, ticket in result:
        activity.append(
            TeamActivityItem(
                timestamp=transition.transitioned_at,
                actor_name=actor.name if actor else "Unknown",
                actor_initials=(
                    "".join([n[0] for n in actor.name.split()])
                    if actor
                    else "?"
                ),
                action=f"moved {ticket.jira_key} to",
                ticket_key=ticket.jira_key,
                to_status=transition.to_status,
            )
        )

    return DashboardMetrics(
        team_id=team_id,
        metrics=metrics,
        status_distribution=dist_items,
        recent_activity=activity,
        last_synced=datetime.now(),
    )


@router.get("/{team_id}/tickets")
async def get_team_tickets(
    team_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    """Get list of tickets for a team."""
    stmt = select(Ticket).where(Ticket.team_id == team_id)

    if status:
        stmt = stmt.where(Ticket.status == status)

    # Eager load assignee to avoid N+1 queries
    stmt = stmt.options(selectinload(Ticket.assignee))

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    tickets = result.scalars().all()
    
    return {
        "tickets": [
            {
                "id": t.id,
                "jira_key": t.jira_key,
                "title": t.title,
                "status": t.status,
                "assignee": t.assignee.name if t.assignee else None,
                "created_at": t.created_at,
                "resolved_at": t.resolved_at,
                "cycle_time_days": float(t.cycle_time_days) if t.cycle_time_days else None,
            }
            for t in tickets
        ],
        "total": len(tickets),
    }
