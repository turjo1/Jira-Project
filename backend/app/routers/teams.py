"""Teams management router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.models.models import Team, User, Ticket
from app.routers.auth import requires_auth
from app.schemas import BaseModel

log = get_logger(__name__)
router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamMemberResponse(BaseModel):
    """Team member response."""

    id: str
    email: str
    name: str
    tickets_in_progress: int


class TeamResponse(BaseModel):
    """Basic team response for list endpoint."""

    id: str
    name: str
    manager_id: str
    member_count: int


class TeamDetailResponse(BaseModel):
    """Detailed team response with members."""

    id: str
    name: str
    manager_id: str
    members: list[TeamMemberResponse]
    metrics_updated_at: Optional[str] = None


class TeamListResponse(BaseModel):
    """List of teams response."""

    teams: list[TeamResponse]
    total: int
    skip: int
    limit: int


@router.get("", response_model=TeamListResponse)
async def list_teams(
    skip: int = 0,
    limit: int = 10,
    user_id: str = Depends(requires_auth),
    session: AsyncSession = Depends(get_db_session),
) -> TeamListResponse:
    """
    List teams managed by the current user.

    Args:
        skip: Number of results to skip (pagination)
        limit: Maximum number of results to return
        user_id: Current user ID from JWT token
        session: Database session

    Returns:
        TeamListResponse with paginated team list

    Raises:
        HTTPException: 400 if skip/limit are invalid
    """
    if skip < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters",
        )

    try:
        # Count total teams managed by user
        count_stmt = select(func.count(Team.id)).where(Team.manager_id == user_id)
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Fetch teams with pagination
        stmt = (
            select(Team)
            .where(Team.manager_id == user_id)
            .options(selectinload(Team.members))
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        teams = result.scalars().unique().all()

        log.info(
            "teams.listed",
            user_id=user_id,
            count=len(teams),
            total=total,
            skip=skip,
            limit=limit,
        )

        return TeamListResponse(
            teams=[
                TeamResponse(
                    id=team.id,
                    name=team.name,
                    manager_id=team.manager_id,
                    member_count=len(team.members) if team.members else 0,
                )
                for team in teams
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        log.error("teams.list_failed", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list teams",
        )


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team_detail(
    team_id: str,
    user_id: str = Depends(requires_auth),
    session: AsyncSession = Depends(get_db_session),
) -> TeamDetailResponse:
    """
    Get detailed information about a specific team.

    Args:
        team_id: ID of the team to retrieve
        user_id: Current user ID from JWT token (must be team manager)
        session: Database session

    Returns:
        TeamDetailResponse with team details and members

    Raises:
        HTTPException: 404 if team not found, 403 if user is not team manager
    """
    try:
        # Fetch team with members (eager loaded)
        stmt = (
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members))
        )
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()

        if not team:
            log.warning("teams.not_found", team_id=team_id, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found",
            )

        # Check authorization: user must be team manager
        if team.manager_id != user_id:
            log.warning(
                "teams.unauthorized_access",
                team_id=team_id,
                user_id=user_id,
                manager_id=team.manager_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this team",
            )

        # Count in-progress tickets per member
        member_responses = []
        for member in team.members:
            in_progress_stmt = select(func.count(Ticket.id)).where(
                Ticket.assignee_id == member.id,
                Ticket.resolved_at.is_(None),
            )
            in_progress_result = await session.execute(in_progress_stmt)
            in_progress_count = in_progress_result.scalar() or 0

            member_responses.append(
                TeamMemberResponse(
                    id=member.id,
                    email=member.email,
                    name=member.name,
                    tickets_in_progress=int(in_progress_count),
                )
            )

        log.info("teams.detail_retrieved", team_id=team_id, user_id=user_id)

        return TeamDetailResponse(
            id=team.id,
            name=team.name,
            manager_id=team.manager_id,
            members=member_responses,
            metrics_updated_at=None,  # TODO: populate from last sync timestamp
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "teams.detail_failed",
            team_id=team_id,
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team details",
        )
