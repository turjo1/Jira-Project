"""Developer performance router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.models.models import User, Team, Ticket, TicketTransition
from app.routers.auth import requires_auth
from app.schemas import BaseModel

log = get_logger(__name__)
router = APIRouter(prefix="/api/developers", tags=["developers"])


class DeveloperMetrics(BaseModel):
    """Developer performance metrics."""

    avg_cycle_time: Optional[float]
    tickets_resolved: int
    bounce_contribution: float
    current_in_progress: int


class DeveloperResponse(BaseModel):
    """Developer response with metrics."""

    id: str
    email: str
    name: str
    metrics: DeveloperMetrics


async def _get_user_teams(session: AsyncSession, user_id: str) -> list[str]:
    """Get list of team IDs managed by the given user."""
    stmt = select(Team.id).where(Team.manager_id == user_id)
    result = await session.execute(stmt)
    return [row[0] for row in result]


async def _calculate_developer_metrics(
    session: AsyncSession, developer_id: str, team_ids: list[str]
) -> DeveloperMetrics:
    """Calculate performance metrics for a developer."""
    if not team_ids:
        return DeveloperMetrics(
            avg_cycle_time=None,
            tickets_resolved=0,
            bounce_contribution=0.0,
            current_in_progress=0,
        )

    # Count resolved tickets
    resolved_stmt = select(func.count(Ticket.id)).where(
        and_(
            Ticket.assignee_id == developer_id,
            Ticket.team_id.in_(team_ids),
            Ticket.resolved_at.isnot(None),
        )
    )
    resolved_result = await session.execute(resolved_stmt)
    tickets_resolved = resolved_result.scalar() or 0

    # Calculate average cycle time for resolved tickets
    cycle_time_calc = case(
        (
            Ticket.resolved_at.isnot(None),
            func.julianday(Ticket.resolved_at)
            - func.julianday(Ticket.created_at),
        ),
        else_=0,
    )

    cycle_time_stmt = select(func.avg(cycle_time_calc)).where(
        and_(
            Ticket.assignee_id == developer_id,
            Ticket.team_id.in_(team_ids),
            Ticket.resolved_at.isnot(None),
        )
    )
    cycle_time_result = await session.execute(cycle_time_stmt)
    avg_cycle_time = cycle_time_result.scalar()

    # Calculate bounce contribution (% of resolved tickets that bounced)
    bounce_count_stmt = select(func.count(func.distinct(Ticket.id))).where(
        and_(
            Ticket.assignee_id == developer_id,
            Ticket.team_id.in_(team_ids),
            Ticket.bounced_count > 0,
        )
    )
    bounce_count_result = await session.execute(bounce_count_stmt)
    bounced_tickets = bounce_count_result.scalar() or 0

    bounce_contribution = (
        (bounced_tickets / tickets_resolved * 100) if tickets_resolved > 0 else 0.0
    )

    # Count current in-progress tickets
    in_progress_stmt = select(func.count(Ticket.id)).where(
        and_(
            Ticket.assignee_id == developer_id,
            Ticket.team_id.in_(team_ids),
            Ticket.resolved_at.is_(None),
        )
    )
    in_progress_result = await session.execute(in_progress_stmt)
    current_in_progress = in_progress_result.scalar() or 0

    return DeveloperMetrics(
        avg_cycle_time=float(avg_cycle_time) if avg_cycle_time else None,
        tickets_resolved=int(tickets_resolved),
        bounce_contribution=float(bounce_contribution),
        current_in_progress=int(current_in_progress),
    )


@router.get("/{dev_id}", response_model=DeveloperResponse)
async def get_developer_detail(
    dev_id: str,
    user_id: str = Depends(requires_auth),
    session: AsyncSession = Depends(get_db_session),
) -> DeveloperResponse:
    """
    Get performance metrics for a specific developer.

    Args:
        dev_id: ID of the developer to retrieve
        user_id: Current user ID from JWT token (must be manager of developer's teams)
        session: Database session

    Returns:
        DeveloperResponse with developer details and metrics

    Raises:
        HTTPException: 404 if developer not found, 403 if user cannot view developer
    """
    try:
        # Fetch developer
        dev_stmt = select(User).where(User.id == dev_id)
        dev_result = await session.execute(dev_stmt)
        developer = dev_result.scalar_one_or_none()

        if not developer:
            log.warning("developers.not_found", dev_id=dev_id, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer not found",
            )

        # Get teams managed by current user
        user_team_ids = await _get_user_teams(session, user_id)

        # Check if developer belongs to any of user's teams
        if developer.team_id not in user_team_ids:
            log.warning(
                "developers.unauthorized_access",
                dev_id=dev_id,
                user_id=user_id,
                dev_team_id=developer.team_id,
                user_team_ids=user_team_ids,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this developer",
            )

        # Calculate metrics for developer (only within accessible teams)
        metrics = await _calculate_developer_metrics(session, dev_id, user_team_ids)

        log.info("developers.detail_retrieved", dev_id=dev_id, user_id=user_id)

        return DeveloperResponse(
            id=developer.id,
            email=developer.email,
            name=developer.name,
            metrics=metrics,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "developers.detail_failed",
            dev_id=dev_id,
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve developer details",
        )
