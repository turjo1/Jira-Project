"""Broadcasting utilities for WebSocket metrics updates."""
import json
import logging
from typing import Optional, Dict, Any

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MetricsBroadcaster:
    """Broadcasts metrics updates to WebSocket clients via Redis pub/sub."""

    @staticmethod
    def broadcast_metrics_update(
        team_id: str,
        cycle_time: Optional[float],
        bounce_rate: Optional[float],
        open_tickets: Optional[int],
        bottleneck: Optional[str],
    ) -> None:
        """
        Broadcast metrics update to all connected clients for a team.

        Called from Celery sync task after metrics are calculated.
        Uses Redis pub/sub so it works even with multiple FastAPI instances.

        Args:
            team_id: Team ID
            cycle_time: Average cycle time in days
            bounce_rate: Bounce rate percentage
            open_tickets: Count of open tickets
            bottleneck: Status name with slowest average time-in-status
        """
        try:
            redis_client = redis.from_url(settings.redis_url, decode_responses=True)

            payload = {
                "type": "metrics_update",
                "team_id": team_id,
                "metrics": {
                    "cycle_time": cycle_time,
                    "bounce_rate": bounce_rate,
                    "open_tickets": open_tickets,
                    "bottleneck": bottleneck,
                    "updated_at": None,  # Will be set on client side
                },
            }

            redis_client.publish("metrics_updated", json.dumps(payload))
            logger.info(f"Broadcast metrics update for team {team_id}")
            redis_client.close()
        except Exception as e:
            logger.error(f"Failed to broadcast metrics update: {e}")
            # Don't raise - broadcasting is non-critical
