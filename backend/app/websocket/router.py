"""WebSocket router for real-time metrics updates."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.config import get_settings
from app.models.models import Team, Metrics
from app.services.auth import TokenService
from app.websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.websocket("/ws/metrics/{team_id}")
async def websocket_endpoint(websocket: WebSocket, team_id: str, token: str = Query(None)):
    """
    WebSocket endpoint for real-time metrics updates.

    Endpoint: ws://localhost:8000/ws/metrics/{team_id}?token=<jwt>

    Auth:
        Pass JWT via query param. Token is validated against team manager authorization.

    Messages:
        - On connect: Sends current metrics snapshot for the team
        - On metrics update: Receives broadcast from Celery sync job
        - Ping/pong: Echo "ping" to test connection health

    Example client:
        const ws = new WebSocket(
            `ws://localhost:8000/ws/metrics/team-001?token=${jwtToken}`
        );
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            // Update dashboard with data.metrics
        };

    Args:
        websocket: The WebSocket connection
        team_id: Team ID to get metrics for
        token: JWT token (query parameter)

    Raises:
        - 1008: Policy violation (missing token, invalid token, unauthorized)
        - WebSocketDisconnect: Normal disconnect or connection error
    """

    # --- Authentication ---
    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Missing token"
        )
        logger.warning(f"WebSocket connection rejected: missing token")
        return

    payload = TokenService.verify_token(token)
    if not payload:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )
        logger.warning(f"WebSocket connection rejected: invalid token")
        return

    user_id = payload.get("sub")

    # --- Authorization ---
    # Verify user is manager of the team
    async with async_session_maker() as session:
        team = await session.get(Team, team_id)
        if not team:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Team not found"
            )
            logger.warning(f"WebSocket connection rejected: team {team_id} not found")
            return

        if team.manager_id != user_id:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized"
            )
            logger.warning(
                f"WebSocket connection rejected: user {user_id} not manager of team {team_id}"
            )
            return

    # --- Accept connection ---
    await manager.connect(websocket, team_id)
    logger.info(f"WebSocket connected: user={user_id}, team={team_id}")

    try:
        # --- Send current metrics snapshot on connect ---
        async with async_session_maker() as session:
            result = await session.execute(
                select(Metrics)
                .where(Metrics.team_id == team_id)
                .order_by(Metrics.date.desc())
                .limit(1)
            )
            current_metrics = result.scalar_one_or_none()

        if current_metrics:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "metrics_update",
                        "team_id": team_id,
                        "metrics": {
                            "cycle_time": (
                                float(current_metrics.avg_cycle_time_days)
                                if current_metrics.avg_cycle_time_days
                                else None
                            ),
                            "bounce_rate": (
                                float(current_metrics.bounce_rate)
                                if current_metrics.bounce_rate
                                else None
                            ),
                            "open_tickets": current_metrics.open_tickets,
                            "bottleneck": current_metrics.bottleneck_status,
                            "updated_at": current_metrics.date.isoformat(),
                        },
                    }
                )
            )
            logger.info(f"Sent metrics snapshot to {team_id}")
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "no_metrics",
                        "team_id": team_id,
                        "message": "No metrics available yet",
                    }
                )
            )
            logger.info(f"No metrics available for team {team_id}")

        # --- Keep connection open and listen for messages ---
        while True:
            data = await websocket.receive_text()

            # Simple ping/pong for health check
            if data == "ping":
                await websocket.send_text("pong")
            else:
                logger.debug(f"Received message from {team_id}: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, team_id)
        logger.info(f"WebSocket disconnected: team={team_id}")
    except Exception as e:
        logger.error(f"WebSocket error for team {team_id}: {e}", exc_info=True)
        manager.disconnect(websocket, team_id)
