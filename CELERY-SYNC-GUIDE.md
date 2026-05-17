# Celery Sync Task Guide

This guide explains the 5-minute Jira data synchronization job that powers the real-time metrics dashboard.

## Overview

The Celery task `sync_jira_data` runs every 5 minutes and:
1. Fetches tickets from Jira for each team
2. Upserts Ticket rows (delta sync — no duplicates)
3. Creates TicketTransition records (audit log of status changes)
4. Recalculates metrics (Cycle Time, Bounce Rate, Open Count, Bottleneck)
5. Broadcasts metrics updates via WebSocket (Redis pub/sub)

**Architecture Flow:**
```
Celery Beat (scheduler) every 5 min
    ↓
sync_jira_data() task (async worker)
    ↓
    For each team:
    1. Get credentials (encrypted Jira token)
    2. Fetch tickets via Jira API (with changelog)
    3. Upsert Ticket rows (delta sync)
    4. Create/update TicketTransition records
    5. Calculate metrics (SQL queries)
    6. Upsert Metrics row (daily snapshot)
    7. Broadcast via MetricsBroadcaster
```

## Files

- **app/tasks/sync.py** — Main Celery task and sync logic
- **app/services/jira.py** — Jira API client
- **celery_worker.py** — Worker entrypoint (runs the task)
- **celery_beat.py** — Beat scheduler entrypoint (schedules the task every 5 min)

## Running Locally

### Start all services (docker-compose):
```bash
docker-compose up
```

This starts:
- FastAPI (port 8000)
- React frontend (port 3000, via separate docker-compose in frontend/)
- MySQL (port 3306)
- Redis (port 6379)
- Celery Worker (background tasks)
- Celery Beat (scheduler)

### Manual Celery commands:

```bash
# Terminal 1: Start Celery worker
cd backend
python celery_worker.py

# Terminal 2: Start Celery Beat scheduler
cd backend
python celery_beat.py

# Terminal 3: Monitor tasks (celery-flower) — optional
cd backend
pip install flower
celery -A app.tasks flower

# Trigger a sync manually (for testing)
cd backend
python -c "from app.tasks.sync import sync_jira_data; sync_jira_data.delay()"
```

## Task Configuration

**Defined in `app/tasks/sync.py`:**

```python
celery_app.conf.beat_schedule = {
    "sync-jira-every-5min": {
        "task": "app.tasks.sync.sync_jira_data",
        "schedule": 300.0,  # 5 minutes in seconds
        "options": {"queue": "sync"},
    },
}
```

**Environment variables (set in docker-compose.yml):**
- `CELERY_BROKER_URL` — Redis URL for task queue (default: `redis://redis:6379/0`)
- `CELERY_RESULT_BACKEND` — Redis URL for task results (default: `redis://redis:6379/0`)
- `DATABASE_URL` — MySQL connection
- `AES_ENCRYPTION_KEY` — For decrypting Jira tokens
- Other Jira OAuth2 credentials

## Data Flow

### Step 1: Fetch Team & Credentials
- Query team by ID
- Get manager's encrypted Jira credentials
- Decrypt token using AES-256

### Step 2: Fetch Jira Issues
```python
jira_service = JiraAPIService(instance_url, token)
issues = await jira_service.fetch_issues(f"project = {team.jira_project_key}")
```

**JQL Query:** `project = <PROJECT_KEY>` (all issues in team's Jira project)

**Jira API endpoint:** `GET /rest/api/3/search?jql=...&expand=changelog`

**Fields fetched:**
- `key` — Jira issue ID
- `summary` — Title
- `status` — Current status
- `assignee` — Person assigned
- `created` — Created timestamp
- `resolutiondate` — Resolved timestamp
- `changelog` — History of status transitions

### Step 3: Upsert Tickets (Delta Sync)
```python
# For each Jira issue:
ticket = Ticket.query.filter_by(jira_key=issue_key).first()
if ticket:
    # Update existing (new status, new assignee, etc.)
    ticket.title = issue.fields.summary
    ticket.status = issue.fields.status.name
    ticket.resolved_at = parse_timestamp(issue.fields.resolutiondate)
else:
    # Create new ticket
    ticket = Ticket(
        team_id=team_id,
        jira_key=issue_key,
        title=issue.fields.summary,
        status=issue.fields.status.name,
        ...
    )
```

**Delta sync:** Only new Jira issues create new Ticket rows. Existing tickets are updated in place (no duplicates).

### Step 4: Create Ticket Transitions
```python
# For each status change in issue.changelog:
transition = TicketTransition(
    ticket_id=ticket.id,
    from_status=change.from_status,
    to_status=change.to_status,
    transitioned_at=parse_timestamp(change.created),
    actor_id=user_id,  # Who made the change
)
```

**Bounce detection:** Later, metrics service identifies transitions where `from_status` > `to_status` (e.g., Done → In Progress).

### Step 5: Calculate Metrics
Uses `MetricsService` (async SQL queries):

```python
cycle_time = await metrics_service.get_cycle_time(session, team_id)
# Average days from created_at to resolved_at (last 30 days)

bounce_rate = await metrics_service.get_bounce_rate(session, team_id)
# % of resolved tickets with backward transitions

open_tickets = await metrics_service.get_open_tickets(session, team_id)
# Count of tickets with resolved_at = NULL

bottleneck = await metrics_service.get_bottleneck(session, team_id)
# Status with slowest average time-in-status
```

### Step 6: Upsert Daily Metrics
```python
metrics = Metrics(
    team_id=team_id,
    date=today,
    avg_cycle_time_days=cycle_time,
    bounce_rate=bounce_rate,
    open_tickets=open_tickets,
    bottleneck_status=bottleneck.status,
)
session.merge(metrics)  # Update if exists, insert if not
```

### Step 7: Broadcast via WebSocket
```python
MetricsBroadcaster.broadcast_metrics_update(
    team_id=team_id,
    cycle_time=cycle_time,
    bounce_rate=bounce_rate,
    open_tickets=open_tickets,
    bottleneck=bottleneck.status,
)
```

**Mechanism:** Posts to Redis pub/sub channel `metrics_updated`. WebSocket clients subscribe and receive updates within 500ms.

## Error Handling

The task catches and logs errors without failing:

1. **Team not found** → Skip (log warning)
2. **No credentials** → Skip (log warning)
3. **Invalid Jira token** → Error (log error, don't retry)
4. **Jira API timeout/error** → Error (log error, retry next cycle)
5. **Database transaction error** → Error (rollback, log)

**Retry policy:** Tasks don't explicitly retry. The 5-minute schedule means the next sync cycle will retry.

Example output:
```json
{
  "status": "success",
  "team_id": "team-001",
  "tickets_synced": 42,
  "transitions_created": 87,
  "cycle_time": 10.5,
  "bounce_rate": 15.2,
  "open_tickets": 23
}
```

## Scaling Considerations

### Single Team Sync
- **Time:** ~2-4 seconds (fetch Jira, upsert tickets, calculate metrics)
- **Database:** 3-5 SQL queries (per team)
- **Jira API:** 1-2 requests (paginated if >100 issues)

### All Teams Sync (5 min cycle)
- **Teams:** Typically 5-20 teams
- **Total time:** ~15-60 seconds per cycle
- **Concurrency:** Currently sequential. Can parallelize with Celery chord/group:

```python
# Parallel sync for all teams
from celery import chord

results = chord(
    [sync_team_jira_data.s(team.id) for team in teams]
)(lambda: "All teams synced")
```

### Database Indexes
Ensure these exist for fast queries:
- `idx_team_status` on `(team_id, status)`
- `idx_created` on `created_at`
- `uk_team_date` unique constraint on `(team_id, date)` in Metrics

See `DATABASE-SCHEMA.md` for full schema.

## Monitoring

### Logs
Structured logs (via structlog) with context:
```
sync_team_start team_id=team-001
fetched_jira_issues team_id=team-001 count=42
tickets_and_transitions_synced team_id=team-001 tickets=5 transitions=12
metrics_calculated team_id=team-001 cycle_time=10.5 bounce_rate=15.2
```

### Metrics
Expose Prometheus metrics:
- `celery_task_duration_seconds` — Sync duration
- `celery_task_total` — Task count
- `jira_api_requests_total` — Jira API calls
- `db_query_duration_seconds` — Database query time

### Health Checks
- `GET /health` — API alive
- `GET /ready` — API + DB + Redis ready
- Check Redis for task queue depth: `redis-cli LLEN celery`

## Testing

Run tests:
```bash
cd backend
pytest tests/test_sync.py -v
```

**Test cases:**
- ✓ Token decryption
- ✓ Sync with no team
- ✓ Sync with no credentials
- ✓ Sync with invalid credentials
- ✓ Successful Jira fetch and upsert
- ✓ Delta sync (no duplicates)
- ✓ Metrics calculation
- ✓ Error handling

**Mocking:** Uses `unittest.mock.patch` to mock Jira API responses.

## Troubleshooting

### Celery tasks not running
1. Check Redis is up: `redis-cli ping`
2. Check Beat scheduler is running: `ps aux | grep celery-beat`
3. Check Worker is running: `ps aux | grep celery-worker`
4. Check task queue: `redis-cli LLEN celery`

### Metrics not updating
1. Check Jira credentials are valid
2. Check Jira project key is correct (e.g., `TEST` not `test`)
3. Check database transactions are committing
4. Check Redis pub/sub: `redis-cli subscribe metrics_updated`

### Token decryption errors
1. Verify `AES_ENCRYPTION_KEY` is 32 bytes (base64-encoded)
2. Verify token was encrypted with same key
3. Check in database: `SELECT jira_token_encrypted FROM credentials LIMIT 1`

### High sync duration (>4 min)
1. Check Jira API response time: `curl -I https://instance.atlassian.net/rest/api/3/search`
2. Check database slow query log (queries >1s)
3. Consider delta sync optimization (only fetch issues modified since last sync)
4. Parallelize team syncs with Celery chord

## Future Enhancements

1. **Incremental sync** — Fetch only issues modified since last sync (use `updated >= -5m`)
2. **Parallel team sync** — Use Celery chord to sync teams in parallel
3. **Webhook integration** — Subscribe to Jira webhooks for instant updates (vs 5-min polling)
4. **Rate limiting** — Respect Jira API quota; queue excess requests
5. **Dead letter queue** — Retry failed syncs with exponential backoff
6. **Metrics persistence** — Archive old metrics to time-series DB (InfluxDB, etc.)
