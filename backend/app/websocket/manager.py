"""WebSocket connection manager for real-time metrics broadcasting."""
import json
import logging
from typing import Dict, Set, Optional

import redis.asyncio as redis
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts metrics updates.

    Architecture:
    - In-memory connections dict: {team_id: {websocket1, websocket2, ...}}
    - Redis pub/sub for horizontal scaling
    - Broadcast on metrics_updated events from Celery jobs
    """

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub_task = None

    async def connect(self, websocket: WebSocket, team_id: str) -> None:
        """
        Register a WebSocket connection for a team.

        Args:
            websocket: The WebSocket connection
            team_id: Team ID to register connection for
        """
        await websocket.accept()
        if team_id not in self.active_connections:
            self.active_connections[team_id] = set()
        self.active_connections[team_id].add(websocket)
        logger.info(
            f"Client connected to team {team_id}. "
            f"Active connections: {len(self.active_connections[team_id])}"
        )

    def disconnect(self, websocket: WebSocket, team_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            team_id: Team ID to disconnect from
        """
        if team_id in self.active_connections:
            self.active_connections[team_id].discard(websocket)
            if not self.active_connections[team_id]:
                del self.active_connections[team_id]
            logger.info(f"Client disconnected from team {team_id}")

    async def broadcast(self, team_id: str, message: dict) -> None:
        """
        Send message to all clients connected to a team.

        Handles disconnected clients gracefully by removing them from
        the active connections set.

        Args:
            team_id: Team ID to broadcast to
            message: Dictionary to serialize and send as JSON
        """
        if team_id not in self.active_connections:
            return

        json_data = json.dumps(message)
        disconnected = []

        for connection in list(self.active_connections[team_id]):
            try:
                await connection.send_text(json_data)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, team_id)

    async def setup_redis(self, redis_url: str = "redis://localhost:6379") -> None:
        """
        Initialize Redis pub/sub for horizontal scaling.

        Subscribes to 'metrics_updated' channel and listens for messages.
        When messages arrive, broadcasts to connected clients.

        Args:
            redis_url: Redis connection URL
        """
        try:
            self.redis_client = await redis.from_url(redis_url, decode_responses=True)
            logger.info("Redis pub/sub initialized")

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection successful")

            # Subscribe to metrics update channel
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("metrics_updated")
            logger.info("Subscribed to metrics_updated channel")

            # Listen for messages (this runs indefinitely in background)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        team_id = payload.get("team_id")
                        if team_id:
                            await self.broadcast(team_id, payload)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Redis message: {e}")
        except Exception as e:
            logger.error(f"Redis pub/sub setup failed: {e}")
            # Continue operation without Redis (single instance mode)

    async def close_redis(self) -> None:
        """Close Redis connection on shutdown."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


# Global instance
manager = ConnectionManager()
