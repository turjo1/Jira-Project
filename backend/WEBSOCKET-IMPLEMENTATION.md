# WebSocket Real-Time Metrics Implementation

## Overview

This document describes the WebSocket infrastructure for real-time metrics updates in the Jira Team Performance Analytics system.

**Architecture:**
- Client connects via WebSocket with JWT token (query parameter)
- Current metrics snapshot sent on connect
- Celery sync job broadcasts updates to all connected clients via Redis pub/sub
- Target latency: <5 seconds from sync completion to client update

## Files Created

```
app/websocket/
├── __init__.py              # Module exports
├── manager.py               # ConnectionManager class
├── router.py                # WebSocket endpoint
└── broadcaster.py           # MetricsBroadcaster utility

tests/
└── test_websocket.py        # Unit and integration tests
```

## Component Details

### 1. ConnectionManager (`app/websocket/manager.py`)

Manages WebSocket connections and broadcasting.

**Key Methods:**
- `connect(websocket, team_id)` — Register a new connection for a team
- `disconnect(websocket, team_id)` — Unregister a connection
- `broadcast(team_id, message)` — Send message to all clients on a team
- `setup_redis(redis_url)` — Initialize Redis pub/sub listener
- `close_redis()` — Cleanup on shutdown

**Data Structure:**
```python
active_connections: Dict[str, Set[WebSocket]] = {
    "team-001": {ws1, ws2, ws3},
    "team-002": {ws4},
}
```

**Redis Pub/Sub:**
- Subscribes to `metrics_updated` channel
- Listens indefinitely for messages
- Broadcasts to connected clients when messages arrive
- Enables horizontal scaling (multiple FastAPI instances)

### 2. WebSocket Endpoint (`app/websocket/router.py`)

FastAPI WebSocket endpoint for real-time metrics.

**Endpoint:** `ws://localhost:8000/ws/metrics/{team_id}?token=<jwt>`

**Authentication:**
1. Extract JWT from query parameter
2. Verify token signature
3. Extract user ID from token payload
4. Authorize: user must be manager of the team

**On Connect:**
1. Accept WebSocket connection
2. Query database for latest metrics
3. Send metrics snapshot (or "no_metrics" if none exist)

**Message Protocol:**
```json
// Metrics update (broadcast from Celery)
{
  "type": "metrics_update",
  "team_id": "team-001",
  "metrics": {
    "cycle_time": 5.5,
    "bounce_rate": 0.15,
    "open_tickets": 42,
    "bottleneck": "In Review",
    "updated_at": "2026-05-18"
  }
}

// Initial snapshot on connect
{
  "type": "metrics_update",
  "team_id": "team-001",
  "metrics": {
    "cycle_time": 5.5,
    ...
  }
}

// No metrics available yet
{
  "type": "no_metrics",
  "team_id": "team-001",
  "message": "No metrics available yet"
}

// Ping/pong health check
Client sends: "ping"
Server replies: "pong"
```

**Error Handling:**
- Missing token: Close with code 1008, reason "Missing token"
- Invalid token: Close with code 1008, reason "Invalid token"
- Team not found: Close with code 1008, reason "Team not found"
- Unauthorized (not manager): Close with code 1008, reason "Unauthorized"
- Connection error: Log error, cleanup connection
- Disconnected client: Remove from active_connections

### 3. MetricsBroadcaster (`app/websocket/broadcaster.py`)

Utility for broadcasting metrics from Celery tasks.

**Method:**
```python
MetricsBroadcaster.broadcast_metrics_update(
    team_id: str,
    cycle_time: Optional[float],
    bounce_rate: Optional[float],
    open_tickets: Optional[int],
    bottleneck: Optional[str],
) -> None
```

**Implementation:**
1. Create Redis connection
2. Publish message to `metrics_updated` channel
3. Close Redis connection
4. Handle errors gracefully (non-critical operation)

## Integration with Celery

### Sync Task (`app/tasks/sync.py`)

After metrics are calculated and committed:

```python
# Step 6: Metrics are committed
session.add(metrics)
await session.commit()

# Step 7: Broadcast to WebSocket clients
MetricsBroadcaster.broadcast_metrics_update(
    team_id=team_id,
    cycle_time=cycle_time,
    bounce_rate=bounce_rate,
    open_tickets=open_tickets,
    bottleneck=bottleneck_status,
)
```

**Flow:**
1. Celery Beat triggers sync job every 5 minutes
2. sync_jira_data fetches all teams
3. sync_team_jira_data syncs each team:
   - Fetch Jira issues
   - Upsert tickets and transitions
   - Calculate metrics
   - Commit to database
   - **Broadcast metrics update**
4. MetricsBroadcaster publishes to Redis
5. ConnectionManager receives message from Redis
6. Broadcast to all connected WebSocket clients

## Integration with FastAPI

### Main App (`app/main.py`)

**Lifespan Context Manager:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    redis_task = asyncio.create_task(ws_manager.setup_redis(settings.redis_url))
    yield
    # Shutdown
    await ws_manager.close_redis()
    if not redis_task.done():
        redis_task.cancel()
```

**Router Registration:**
```python
app.include_router(ws_router.router)
```

## Frontend Integration

### Client Connection

```javascript
// React component
const token = localStorage.getItem('access_token');
const wsUrl = `ws://localhost:8000/ws/metrics/team-001?token=${token}`;

const ws = new WebSocket(wsUrl);

ws.onopen = () => {
  console.log('Connected to metrics');
  // Optionally send ping for health check
  setInterval(() => ws.send('ping'), 30000);
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'metrics_update') {
    // Update dashboard with new metrics
    updateMetrics(data.metrics);
  } else if (data.type === 'no_metrics') {
    // Handle no data state
    showNoMetricsMessage();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from metrics');
  // Implement auto-reconnect logic
  setTimeout(() => reconnectWebSocket(), 5000);
};
```

### Auto-Reconnect with Exponential Backoff

```javascript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

async function reconnectWebSocket() {
  if (reconnectAttempts >= maxReconnectAttempts) {
    console.error('Max reconnection attempts reached');
    return;
  }
  
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
  reconnectAttempts++;
  
  setTimeout(() => {
    connectWebSocket();
  }, delay);
}
```

## Deployment Considerations

### Single Instance (Development)

```yaml
# docker-compose.yml
services:
  backend:
    # FastAPI with uvicorn
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - mysql
  
  celery_worker:
    # Celery worker
  
  celery_beat:
    # Celery Beat scheduler
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

**In-Memory + Redis:**
- FastAPI: In-memory connection tracking + Redis pub/sub listener
- Celery: Redis broker for jobs
- All instances share Redis for messages

### Multiple Instances (Production)

With load balancer:

```
Client ──┬─→ FastAPI #1 (WS) ──┐
         └─→ FastAPI #2 (WS) ──┼─→ Redis pub/sub
                                └─→ Celery worker(s)
```

**How It Works:**
1. Client connects to one FastAPI instance (sticky session or balancer)
2. That instance registers connection in its `active_connections`
3. Celery worker (any instance) publishes to Redis `metrics_updated`
4. Redis delivers to all instances' pub/sub listeners
5. Each instance broadcasts to its own connections
6. Client receives message from its connected instance

**No Cross-Instance Message Loss:**
- Redis pub/sub is ephemeral (messages don't persist if no subscribers)
- All instances must be listening (done in lifespan)
- If instance is offline, its clients lose connection (normal)

### Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: backend-pod
spec:
  containers:
  - name: fastapi
    image: backend:latest
    ports:
    - containerPort: 8000
    env:
    - name: REDIS_URL
      value: redis://redis-service:6379/0
  - name: celery-worker
    image: backend:latest
    command: ["celery", "-A", "app.tasks.sync.celery_app", "worker"]
    env:
    - name: REDIS_URL
      value: redis://redis-service:6379/0
```

**WebSocket with K8s:**
- Use ClusterIP service for backend (internal)
- Use LoadBalancer or Ingress for external access
- Sticky sessions: Configure load balancer for affinity
- Health checks: Include `/health` endpoint (doesn't require WebSocket)

## Testing

### Unit Tests

**ConnectionManager:**
```python
# Track connections
manager.connect(ws1, "team-001")
manager.connect(ws2, "team-001")
assert len(manager.active_connections["team-001"]) == 2

# Broadcast
await manager.broadcast("team-001", message)
ws1.send_text.assert_called_once()

# Disconnect
manager.disconnect(ws1, "team-001")
assert ws1 not in manager.active_connections["team-001"]
```

**MetricsBroadcaster:**
```python
# Mock Redis
mock_redis.publish = mock_publish
redis.from_url = lambda *args, **kwargs: mock_redis

# Broadcast
MetricsBroadcaster.broadcast_metrics_update(...)

# Verify
assert len(published) == 1
assert published[0]["channel"] == "metrics_updated"
```

### Integration Tests

**WebSocket Connection:**
```python
with client.websocket_connect(f"/ws/metrics/team-001?token={jwt}") as ws:
    data = ws.receive_json()
    assert data["type"] == "metrics_update"
```

**End-to-End:**
1. Create team and metrics in database
2. Connect WebSocket client
3. Receive metrics snapshot
4. Trigger Celery sync job
5. Verify metrics update received <5 seconds

See `tests/test_websocket.py` for detailed tests.

## Monitoring & Debugging

### Logs

**FastAPI:**
```
INFO: WebSocket connected: user=user-123, team=team-001
INFO: Sent metrics snapshot to team-001
INFO: Client connected to team team-001. Active: 2
INFO: Failed to send to client: Connection lost
INFO: Client disconnected from team team-001
```

**Celery:**
```
INFO: sync_team_start team_id=team-001
INFO: metrics_calculated team_id=team-001 cycle_time=5.5
INFO: Broadcast metrics update for team team-001
```

### Metrics (Prometheus)

Optional: Add metrics to track:
- Active WebSocket connections per team
- Messages broadcast per minute
- Broadcast latency (time from sync to client)
- Failed broadcast attempts

### Health Checks

**Endpoint: `GET /health`** (existing)
- Doesn't require WebSocket
- Returns JSON status

**WebSocket Health: Send "ping"**
```javascript
ws.send('ping');
// Receive 'pong'
```

## Troubleshooting

### Clients Not Receiving Updates

1. **Check WebSocket connection:**
   - Verify client connects successfully
   - Check browser console for connection errors
   - Verify JWT is valid and has correct team_id

2. **Check Redis:**
   ```bash
   redis-cli
   > SUBSCRIBE metrics_updated
   # Trigger sync and verify message appears
   ```

3. **Check Celery:**
   ```bash
   celery -A app.tasks.sync.celery_app inspect active
   # Verify sync job ran
   ```

4. **Check logs:**
   ```bash
   # FastAPI logs
   docker logs backend
   
   # Celery logs
   docker logs celery-worker
   ```

### Slow Updates (>5 seconds)

1. **Measure sync duration:**
   - Check Celery logs for "sync_job_complete"
   - If >4 min, optimize Jira API queries

2. **Measure broadcast latency:**
   - Add timestamps to broadcast message
   - Client logs receive time
   - Difference is broadcast latency

3. **Check Redis:**
   - Verify Redis is responsive
   - Monitor pub/sub subscribers: `INFO pubsub`

### Memory Leaks

**ConnectionManager:**
- Verify disconnects are called on close
- Check for cyclic references in WebSocket objects
- Monitor active_connections size over time

**Redis:**
- Verify Redis connection is closed on shutdown
- Check Redis memory usage: `INFO memory`
- Monitor for leaked connections: `CONFIG GET maxclients`

## Summary

The WebSocket implementation provides:
- ✓ Real-time metrics updates to dashboard
- ✓ <5 second latency from sync to client
- ✓ Horizontal scaling via Redis pub/sub
- ✓ JWT authentication per connection
- ✓ Team-level authorization
- ✓ Graceful error handling
- ✓ Auto-cleanup on disconnect

Integration points:
- FastAPI: Lifespan context manager initializes Redis pub/sub
- Celery: sync_jira_data calls MetricsBroadcaster after metrics commit
- Frontend: WebSocket client with auto-reconnect
