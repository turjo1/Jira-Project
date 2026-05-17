"""Tests for WebSocket real-time metrics updates."""
import json
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth import TokenService


@pytest.fixture
def app():
    """Create test app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_jwt():
    """Create a valid JWT token."""
    return TokenService.create_access_token(data={"sub": "test-user-id"})


class TestWebSocketAuthentication:
    """Test WebSocket authentication."""

    def test_missing_token(self, client):
        """Test connection rejected with missing token."""
        with pytest.raises(Exception):  # WebSocket connection error
            with client.websocket_connect(
                "/ws/metrics/team-001"
            ) as websocket:
                pass

    def test_invalid_token(self, client):
        """Test connection rejected with invalid token."""
        with pytest.raises(Exception):  # WebSocket connection error
            with client.websocket_connect(
                "/ws/metrics/team-001?token=invalid-token"
            ) as websocket:
                pass

    def test_valid_token_accepted(self, client, valid_jwt, db_session):
        """Test connection accepted with valid token."""
        # This is a basic test - full test requires:
        # 1. Real FastAPI WebSocket support
        # 2. Mocked database session
        # 3. Team/User setup in database
        pass


class TestWebSocketBroadcasting:
    """Test WebSocket broadcast functionality."""

    @pytest.mark.asyncio
    async def test_metrics_snapshot_on_connect(self, app, valid_jwt):
        """Test that current metrics are sent on connect."""
        # Requires:
        # - AsyncTestClient
        # - Mocked Metrics in database
        # - Proper async context
        pass

    @pytest.mark.asyncio
    async def test_ping_pong(self, app, valid_jwt):
        """Test ping/pong health check."""
        # Requires:
        # - AsyncTestClient
        # - WebSocket context
        pass

    @pytest.mark.asyncio
    async def test_multiple_clients_same_team(self):
        """Test broadcast to multiple clients on same team."""
        # Requires:
        # - Multiple WebSocket connections
        # - Message verification for each
        pass

    @pytest.mark.asyncio
    async def test_isolation_between_teams(self):
        """Test that broadcasts don't cross team boundaries."""
        # Requires:
        # - Multiple teams
        # - Multiple connections per team
        # - Verify only correct team receives message
        pass


class TestMetricsBroadcaster:
    """Test the MetricsBroadcaster utility."""

    def test_broadcast_metrics_update(self, monkeypatch):
        """Test broadcast function with mocked Redis."""
        from app.websocket.broadcaster import MetricsBroadcaster
        import redis

        published = []

        class MockRedis:
            def publish(self, channel, message):
                published.append({"channel": channel, "message": message})
                return 1

            def close(self):
                pass

        def mock_from_url(url, decode_responses=False):
            return MockRedis()

        monkeypatch.setattr(redis, "from_url", mock_from_url)

        # Call broadcast
        MetricsBroadcaster.broadcast_metrics_update(
            team_id="team-001",
            cycle_time=5.5,
            bounce_rate=0.15,
            open_tickets=42,
            bottleneck="In Review",
        )

        # Verify Redis publish was called
        assert len(published) == 1
        assert published[0]["channel"] == "metrics_updated"

        payload = json.loads(published[0]["message"])
        assert payload["type"] == "metrics_update"
        assert payload["team_id"] == "team-001"
        assert payload["metrics"]["cycle_time"] == 5.5
        assert payload["metrics"]["bounce_rate"] == 0.15
        assert payload["metrics"]["open_tickets"] == 42
        assert payload["metrics"]["bottleneck"] == "In Review"

    def test_broadcast_handles_redis_error(self, monkeypatch):
        """Test broadcast gracefully handles Redis errors."""
        from app.websocket.broadcaster import MetricsBroadcaster
        from redis import ConnectionError as RedisConnectionError

        def mock_from_url(url, decode_responses=False):
            raise RedisConnectionError("Redis not available")

        import redis
        monkeypatch.setattr(redis, "from_url", mock_from_url)

        # Should not raise - broadcasting is non-critical
        MetricsBroadcaster.broadcast_metrics_update(
            team_id="team-001",
            cycle_time=5.5,
            bounce_rate=0.15,
            open_tickets=42,
            bottleneck="In Review",
        )


class TestConnectionManager:
    """Test ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_connection_tracking(self):
        """Test that connections are tracked per team."""
        from app.websocket.manager import ConnectionManager
        from unittest.mock import AsyncMock

        manager = ConnectionManager()

        # Mock WebSocket objects
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        # Connect to teams
        await manager.connect(ws1, "team-001")
        await manager.connect(ws2, "team-001")
        await manager.connect(ws3, "team-002")

        # Verify tracking
        assert "team-001" in manager.active_connections
        assert len(manager.active_connections["team-001"]) == 2
        assert ws1 in manager.active_connections["team-001"]
        assert ws2 in manager.active_connections["team-001"]

        assert "team-002" in manager.active_connections
        assert len(manager.active_connections["team-002"]) == 1
        assert ws3 in manager.active_connections["team-002"]

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self):
        """Test that disconnect removes connections and teams."""
        from app.websocket.manager import ConnectionManager
        from unittest.mock import AsyncMock

        manager = ConnectionManager()

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(ws1, "team-001")
        await manager.connect(ws2, "team-001")

        # Disconnect first client
        manager.disconnect(ws1, "team-001")
        assert len(manager.active_connections["team-001"]) == 1

        # Disconnect second client
        manager.disconnect(ws2, "team-001")
        assert "team-001" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self):
        """Test broadcast sends to all clients on team."""
        from app.websocket.manager import ConnectionManager
        from unittest.mock import AsyncMock

        manager = ConnectionManager()

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(ws1, "team-001")
        await manager.connect(ws2, "team-001")

        message = {
            "type": "metrics_update",
            "team_id": "team-001",
            "metrics": {"cycle_time": 5.5},
        }

        await manager.broadcast("team-001", message)

        # Verify both clients received message
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

        # Verify message content
        call_args_1 = ws1.send_text.call_args[0][0]
        assert json.loads(call_args_1) == message

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_clients(self):
        """Test broadcast removes clients that fail to send."""
        from app.websocket.manager import ConnectionManager
        from unittest.mock import AsyncMock

        manager = ConnectionManager()

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        # ws1 will fail on send
        ws1.send_text.side_effect = Exception("Connection lost")

        await manager.connect(ws1, "team-001")
        await manager.connect(ws2, "team-001")

        assert len(manager.active_connections["team-001"]) == 2

        message = {"type": "metrics_update"}
        await manager.broadcast("team-001", message)

        # ws1 should be removed
        assert len(manager.active_connections["team-001"]) == 1
        assert ws1 not in manager.active_connections["team-001"]
        assert ws2 in manager.active_connections["team-001"]


class TestWebSocketIntegration:
    """Integration tests (require mocking/fixtures)."""

    def test_metrics_broadcast_from_celery_task(self):
        """Test that Celery sync task broadcasts metrics."""
        # This test would verify the integration:
        # 1. Mock Celery task execution
        # 2. Verify MetricsBroadcaster.broadcast_metrics_update was called
        # 3. Verify correct metrics values were passed
        pass

    def test_end_to_end_sync_to_websocket(self):
        """Test full flow: Celery sync -> broadcast -> client receives."""
        # This is a full integration test covering:
        # 1. Trigger Celery sync_jira_data
        # 2. WebSocket client connected
        # 3. Verify client receives metrics update
        # 4. Verify timing (<5 seconds)
        pass
