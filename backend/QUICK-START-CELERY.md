# Quick Start: Celery Sync Task

## One-Liner: Start Everything

```bash
cd backend && docker-compose up
```

This starts FastAPI, MySQL, Redis, Celery Worker, and Celery Beat. The sync task will run automatically every 5 minutes.

## What You'll See

### Startup (docker-compose up)
```
celery-worker  | app.tasks.sync._sync_worker_startup
celery-beat    | celery beat v5.3.6 ... active

# After 5 minutes:
celery-worker  | sync_team_start team_id=team-001
celery-worker  | fetched_jira_issues count=42
celery-worker  | metrics_calculated cycle_time=10.5 bounce_rate=15.2
```

### Dashboard Updates
Open http://localhost:3000 → Metrics update automatically within 5 seconds of Jira change.

## Manual Testing (without Docker)

```bash
cd backend

# Terminal 1: Start worker
python celery_worker.py

# Terminal 2: Start scheduler
python celery_beat.py

# Terminal 3: Trigger sync manually
python -c "from app.tasks.sync import sync_jira_data; sync_jira_data.delay()"

# Watch logs:
tail -f logs/celery.log
```

## Key Files

| File | Purpose |
|------|---------|
| `app/tasks/sync.py` | Main sync task (430 lines) |
| `app/services/jira.py` | Jira API client (160 lines) |
| `celery_worker.py` | Worker entrypoint |
| `celery_beat.py` | Scheduler entrypoint |
| `tests/test_sync.py` | 8 test cases |

## Run Tests

```bash
cd backend
pytest tests/test_sync.py -v
# Expected: 8 passed in 2.5s
```

## Verify It Works

### Check Redis queue:
```bash
redis-cli LLEN celery
# Should see task count
```

### Check database:
```bash
mysql jira_analytics -u app -papp

# See synced tickets:
SELECT COUNT(*) FROM tickets;

# See transitions:
SELECT COUNT(*) FROM ticket_transitions;

# See metrics:
SELECT * FROM metrics ORDER BY created_at DESC LIMIT 1;
```

### Check logs:
```bash
# In docker-compose up terminal, look for:
sync_job_complete total_teams=3 successful=3 failed=0
```

## Adjust Sync Interval

Edit `app/tasks/sync.py` line 48:
```python
"schedule": 60.0,  # 1 minute (for testing)
"schedule": 300.0,  # 5 minutes (default)
"schedule": 900.0,  # 15 minutes
```

Restart Beat scheduler for changes to take effect.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Tasks not running | Check Redis: `redis-cli ping` |
| Celery worker hanging | Check database: `mysql -u app -papp jira_analytics` |
| Sync fails with auth error | Verify JIRA_CLIENT_ID/SECRET in .env |
| Metrics not updating | Check Jira project key matches in `teams` table |
| Redis connection error | Ensure Redis container is healthy: `docker ps` |

## Architecture

```
Celery Beat (every 5 min)
    ↓
Celery Worker (picks up task)
    ↓
For each team:
  1. Get Jira credentials
  2. Fetch issues
  3. Upsert tickets
  4. Create transitions
  5. Calculate metrics
  6. Broadcast to WebSocket
    ↓
Dashboard updates in real-time
```

## Next Steps

After sync is working:
1. Verify metrics in dashboard (http://localhost:3000)
2. Test WebSocket updates (open DevTools → Network → WS)
3. Implement remaining Phase 5 tasks
4. Set up monitoring/alerting

See `CELERY-SYNC-GUIDE.md` for detailed operational guide.
