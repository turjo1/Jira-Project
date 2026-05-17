"""Service for calculating team performance metrics."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func, and_, select, case
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models import Ticket, TicketTransition

log = structlog.get_logger(__name__)


class MetricsService:
    """Service for calculating team performance metrics."""

    @staticmethod
    async def get_cycle_time(
        session: AsyncSession, team_id: str, days_back: int = 30
    ) -> Optional[float]:
        """Calculate average cycle time (days from creation to resolution)."""
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Use julianday for SQLite compatibility; wraps in case() to handle NULLs
        cycle_time_calc = case(
            (Ticket.resolved_at.isnot(None),
             func.julianday(Ticket.resolved_at) - func.julianday(Ticket.created_at)),
            else_=0
        )

        stmt = select(
            func.avg(cycle_time_calc).label("avg_cycle_time")
        ).where(
            and_(
                Ticket.team_id == team_id,
                Ticket.resolved_at.isnot(None),
                Ticket.created_at >= cutoff_date,
            )
        )

        result = await session.execute(stmt)
        avg_cycle_time = result.scalar()
        return float(avg_cycle_time) if avg_cycle_time else None

    @staticmethod
    async def get_bounce_rate(
        session: AsyncSession, team_id: str, days_back: int = 30
    ) -> Optional[float]:
        """Calculate bounce rate (tickets that moved back to a prior status)."""
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Get resolved tickets created in the timeframe (only resolved tickets can bounce)
        tickets_stmt = select(Ticket.id).where(
            and_(
                Ticket.team_id == team_id,
                Ticket.created_at >= cutoff_date,
                Ticket.resolved_at.isnot(None),
            )
        )
        tickets_result = await session.execute(tickets_stmt)
        ticket_ids = [row[0] for row in tickets_result]

        if not ticket_ids:
            return None

        # Define status order: Todo < InProgress < Review < Done
        status_order_from = case(
            (TicketTransition.from_status == "Open", 1),
            (TicketTransition.from_status == "In Progress", 2),
            (TicketTransition.from_status == "In Review", 3),
            (TicketTransition.from_status == "Done", 4),
            else_=0
        )
        status_order_to = case(
            (TicketTransition.to_status == "Open", 1),
            (TicketTransition.to_status == "In Progress", 2),
            (TicketTransition.to_status == "In Review", 3),
            (TicketTransition.to_status == "Done", 4),
            else_=0
        )

        # Count tickets that have at least one backward transition (from_order > to_order)
        bounced_stmt = select(
            func.count(func.distinct(TicketTransition.ticket_id)).label("bounced")
        ).where(
            and_(
                TicketTransition.ticket_id.in_(ticket_ids),
                status_order_from > status_order_to,  # Backward movement
            )
        )

        bounced_result = await session.execute(bounced_stmt)
        bounced_count = bounced_result.scalar() or 0

        bounce_rate = (bounced_count / len(ticket_ids) * 100) if ticket_ids else 0
        return float(bounce_rate)

    @staticmethod
    async def get_open_tickets(session: AsyncSession, team_id: str) -> int:
        """Get count of currently open (unresolved) tickets."""
        stmt = select(func.count(Ticket.id)).where(
            and_(Ticket.team_id == team_id, Ticket.resolved_at.is_(None))
        )

        result = await session.execute(stmt)
        count = result.scalar() or 0
        return int(count)

    @staticmethod
    async def get_bottleneck(
        session: AsyncSession, team_id: str
    ) -> Optional[dict]:
        """Get the status with the highest average dwell time (time between consecutive transitions)."""
        from sqlalchemy.orm import aliased

        # Alias for previous and current transitions
        prev_trans = aliased(TicketTransition)
        curr_trans = aliased(TicketTransition)

        # Calculate time spent in each status (time between transitions)
        # Join current and previous transitions for the same ticket where prev_id < curr_id
        dwell_time_calc = case(
            (curr_trans.transitioned_at.isnot(None),
             func.julianday(curr_trans.transitioned_at) - func.julianday(prev_trans.transitioned_at)),
            else_=0
        )

        stmt = select(
            curr_trans.to_status,
            func.avg(dwell_time_calc).label("avg_dwell_time"),
        ).join(
            prev_trans,
            and_(
                prev_trans.ticket_id == curr_trans.ticket_id,
                prev_trans.id < curr_trans.id,
            ),
            isouter=True
        ).join(
            Ticket,
            Ticket.id == curr_trans.ticket_id
        ).where(
            Ticket.team_id == team_id
        ).group_by(curr_trans.to_status).order_by(
            func.avg(dwell_time_calc).desc()
        ).limit(1)

        result = await session.execute(stmt)
        row = result.first()

        if row:
            return {"status": row[0], "avg_dwell_days": float(row[1]) if row[1] else 0}
        return None

    @staticmethod
    async def get_status_distribution(session: AsyncSession, team_id: str) -> dict:
        """Get distribution of tickets across statuses."""
        # Use julianday for SQLite compatibility; wraps in case() to handle NULLs
        cycle_time_calc = case(
            (Ticket.resolved_at.isnot(None),
             func.julianday(Ticket.resolved_at) - func.julianday(Ticket.created_at)),
            else_=0
        )

        stmt = select(
            Ticket.status,
            func.count(Ticket.id).label("count"),
            func.avg(cycle_time_calc).label("avg_dwell_time"),
        ).where(
            Ticket.team_id == team_id,
        ).group_by(Ticket.status)

        result = await session.execute(stmt)
        distribution = {}

        for status, count, avg_dwell in result:
            distribution[status] = {
                "count": int(count),
                "avg_dwell_days": float(avg_dwell) if avg_dwell else 0,
            }

        return distribution
