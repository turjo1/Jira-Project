# WebSocket Real-Time Metrics - Quick Start

## What Was Implemented

This implementation provides real-time metrics updates to the frontend dashboard via WebSocket. When the Celery sync job completes every 5 minutes, all connected clients receive metrics updates within <5 seconds.

## Files Added/Modified

### New Files
- `app/websocket/manager.py` - ConnectionManager for WebSocket connections
- `app/websocket/router.py` - WebSocket endpoint with JWT auth
- `app/websocket/broadcaster.py` - Redis pub/sub broadcaster utility
- `tests/test_websocket.py` - Unit and integration tests
- `WEBSOCKET-IMPLEMENTATION.md` - Detailed technical documentation
- This file - Quick start guide

### Modified Files
- `app/websocket/__init__.py` - Module exports
- `app/main.py` - Register WebSocket router, initialize Redis pub/sub
- `app/tasks/sync.py` - Call MetricsBroadcaster after metrics calculated

## How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│ Client (React Dashboard)                            │
│ - Connects: ws://localhost:8000/ws/metrics/team-01  │
│ - Receives: Metrics updates in real-time            │
│ - Send: Ping for health check                       │
└────────────────┬────────────────────────────────────┘
                 │ WebSocket (WSS in prod)
                 ↓
┌─────────────────────────────────────────────────────┐
│ FastAPI Backend                                     │
│ - Endpoint: /ws/metrics/{team_id}                   │
│ - Handles: Auth, metrics snapshot, broadcast recv   │
│ - Redis Listener: Listens for metrics_updated msgs  │
└────────────────┬────────────────────────────────────┘
                 │ Redis pub/sub
                 ↓
┌─────────────────────────────────────────────────────┐
│ Redis (Message Broker)                              │
│ - Channel: metrics_updated                          │
│ - Messages: Team metrics updates from Celery        │
└─────────────────────────────────────────────────────┘
                 ↑
                 │ Publish (every 5 min)
                 │
┌─────────────────────────────────────────────────────┐
│ Celery Worker                                       │
│ - Task: sync_jira_data (runs every 5 min)           │
│ - Steps: Fetch Jira → Upsert data → Calculate       │
│          metrics → Broadcast via Redis              │
└─────────────────────────────────────────────────────┘
```

### Key Components

#### 1. ConnectionManager (`app/websocket/manager.py`)
- Tracks active WebSocket connections per team
- In-memory set: `{team_id: {ws1, ws2, ...}}`
- Broadcasts messages to all connections on a team
- Listens to Redis pub/sub for metrics updates
- Cleans up disconnected clients automatically

#### 2. WebSocket Endpoint (`app/websocket/router.py`)
- Route: `ws://localhost:8000/ws/metrics/{team_id}?token=<jwt>`
- Authenticates with JWT (query parameter)
- Authorizes (user must be team manager)
- Sends current metrics snapshot on connect
- Handles ping/pong for health checks

#### 3. MetricsBroadcaster (`app/websocket/broadcaster.py`)
- Called from Celery sync task
- Publishes metrics to Redis `metrics_updated` channel
- Non-critical operation (failures logged, not raised)

#### 4. Celery Integration (`app/tasks/sync.py`)
- After metrics calculated and committed:
  ```python
  MetricsBroadcaster.broadcast_metrics_update(
      team_id=team_id,
      cycle_time=cycle_time,
      bounce_rate=bounce_rate,
      open_tickets=open_tickets,
      bottleneck=bottleneck_status,
  )
  ```

## Testing

### Run Unit Tests
```bash
cd backend
./venv/bin/pytest tests/test_websocket.py -v
```

**Test Coverage:**
- `TestMetricsBroadcaster` - Redis pub/sub broadcasting (2 tests)
- `TestConnectionManager` - Connection tracking and broadcast (4 tests)
- `TestWebSocketAuthentication` - Auth validation (3 tests)
- `TestWebSocketBroadcasting` - Message delivery (4 tests)

### Manual Testing

#### 1. Start Backend with Redis
```bash
# Terminal 1: Start FastAPI
cd backend
./venv/bin/uvicorn app.main:app --reload

# Terminal 2: Start Celery worker
./venv/bin/celery -A app.tasks.sync.celery_app worker --loglevel=info

# Terminal 3: Start Celery Beat (scheduler)
./venv/bin/celery -A app.tasks.sync.celery_app beat --loglevel=info

# Or use docker-compose
docker-compose up
```

#### 2. Test WebSocket Connection
```bash
# In a browser console or WebSocket client (wscat):
npm install -g wscat

# Get a JWT token from /auth/jira endpoint first
# Then connect:
wscat -c "ws://localhost:8000/ws/metrics/team-001?token=<your-jwt>"

# You should receive:
# {
#   "type": "metrics_update",
#   "team_id": "team-001",
#   "metrics": { ... }
# }

# Test ping/pong:
> ping
< pong
```

#### 3. Trigger Metrics Broadcast
```bash
# Option A: Wait for Celery Beat (5 minute interval)

# Option B: Manually trigger sync via Celery
# In Python shell:
from app.tasks.sync import sync_jira_data
result = sync_jira_data.delay()
print(result.get())

# Option C: Call sync endpoint (if exists)
curl http://localhost:8000/api/sync
```

## Configuration

### Environment Variables
```bash
# .env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
JWT_SIGNING_KEY=your-secret-key
```

### Docker Compose
See `docker-compose.yml` for full stack:
- FastAPI (port 8000)
- Redis (port 6379)
- MySQL (port 3306)
- Celery worker
- Celery Beat

## Frontend Integration

### React Client Example
```javascript
import { useEffect, useRef } from 'react';

function MetricsListener({ teamId, token, onMetricsUpdate }) {
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8000/ws/metrics/${teamId}?token=${token}`
    );

    ws.onopen = () => {
      console.log('Connected to metrics');
      // Optional: Send ping periodically
      setInterval(() => ws.send('ping'), 30000);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'metrics_update') {
        onMetricsUpdate(data.metrics);
      } else if (data.type === 'no_metrics') {
        console.log('Metrics not available yet');
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Disconnected from metrics');
      // Implement auto-reconnect
      setTimeout(connectWebSocket, 5000);
    };

    wsRef.current = ws;

    return () => ws.close();
  }, [teamId, token]);

  return null; // This is a listener component
}

export default MetricsListener;
```

### Auto-Reconnect Logic
```javascript
let reconnectAttempts = 0;
const maxAttempts = 5;

function connectWithBackoff() {
  if (reconnectAttempts >= maxAttempts) {
    console.error('Failed to reconnect after max attempts');
    return;
  }

  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
  reconnectAttempts++;

  setTimeout(connectWebSocket, delay);
}
```

## Success Criteria

- ✅ WebSocket endpoint authenticated with JWT
- ✅ Current metrics sent on connect
- ✅ Multiple clients receive same metrics (broadcast)
- ✅ <5 second latency from sync to client update
- ✅ Proper error handling (auth, disconnect)
- ✅ Redis pub/sub for horizontal scaling
- ✅ No memory leaks on disconnects
- ✅ Celery sync triggers broadcast
- ✅ Unit tests passing

## Troubleshooting

### WebSocket Connection Fails

**Symptom:** "Connection refused"
- Verify FastAPI is running: `curl http://localhost:8000/health`
- Verify Redis is running: `redis-cli ping` should return "PONG"
- Check JWT is valid: Decode token at jwt.io

**Symptom:** "1008 Policy Violation"
- Missing token: Add `?token=<jwt>` to URL
- Invalid token: Generate new token from `/auth/jira`
- Wrong team: Verify team_id in URL matches a team you're manager of

### Metrics Not Updating

**Symptom:** Receive snapshot on connect, but no updates
- Verify Celery worker is running: `celery -A app.tasks.sync inspect active`
- Verify Celery Beat is running: Check for "sync-jira-every-5min" in beat logs
- Verify metrics calculation: Check database for Metrics records
- Check Redis pub/sub: `redis-cli SUBSCRIBE metrics_updated`

**Symptom:** Updates take >5 seconds
- Check Celery task duration: Look for "sync_job_complete" in logs
- Check database: Slow queries may delay metrics calculation
- Check Redis: `redis-cli INFO stats` for throughput

### Memory Leaks

- Monitor WebSocket connections: `ConnectionManager.active_connections` size
- Verify disconnects: Check logs for "Client disconnected"
- Monitor Redis connections: `redis-cli INFO clients`

## Next Steps

1. **Frontend:** Integrate WebSocket listener in Dashboard component
2. **E2E Testing:** Create Playwright test for full flow
3. **Monitoring:** Add Prometheus metrics for WebSocket connections
4. **Load Testing:** Test with 100+ concurrent connections
5. **Deployment:** Configure WebSocket on Kubernetes (sticky sessions)

## See Also

- `WEBSOCKET-IMPLEMENTATION.md` - Detailed technical documentation
- `app/websocket/` - Source code with inline documentation
- `tests/test_websocket.py` - Unit tests and examples
- `ARCHITECTURE.md` § Real-time Architecture

## Questions?

Refer to detailed docs in `WEBSOCKET-IMPLEMENTATION.md` or code comments in:
- `app/websocket/manager.py`
- `app/websocket/router.py`
- `app/websocket/broadcaster.py`
