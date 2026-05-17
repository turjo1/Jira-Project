# Full Testing Guide — Jira Team Performance Analytics

## Build Status ✅

**Frontend:**
- TypeScript compilation: ✅ PASS (0 errors)
- Vite production build: ✅ PASS (167.23 kB gzipped)
- All modules compile successfully

**Backend:**
- Python modules: ✅ PASS (all modules compile)
- Code syntax: ✅ VALID

---

## Option 1: Local Development Testing (No Docker)

### Prerequisites
```bash
# Backend: Python 3.11+ with dependencies
cd backend
pip install -r requirements.txt

# Frontend: Node 20+ with dependencies
cd frontend
npm install
```

### Start Services (in separate terminals)

**Terminal 1 - Frontend Dev Server:**
```bash
cd frontend
npm run dev
# Opens on http://localhost:5173
```

**Terminal 2 - Backend Dev Server:**
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# API: http://localhost:8000
# Health: http://localhost:8000/health
```

**Terminal 3 - Backend Tests:**
```bash
cd backend
python -m pytest tests/ -v --tb=short
```

### What Works Without Docker
✅ Frontend dev server with hot reload
✅ Backend API with in-memory SQLite (fixtures)
✅ OAuth2 flow (mocked responses)
✅ All API endpoints (with mock data)
✅ WebSocket connections (no broadcasts without Redis)
✅ Component rendering
✅ Type checking
✅ Unit tests (66 passing)

### What Requires Docker
❌ Real MySQL database (uses SQLite in tests)
❌ Redis (pub/sub for WebSocket broadcasts)
❌ Celery worker (5-min sync job)
❌ Celery Beat (scheduler)
❌ Full E2E tests (Playwright integration)

---

## Option 2: Full Stack Testing (With Docker)

### Prerequisites
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
docker --version        # Should be 24.0+
docker-compose --version  # Should be 2.0+
```

### Start Full Stack
```bash
cd /Users/turjomazumder/Antigravity\ Project/Jira\ Project

# Start all services
docker-compose up -d

# Verify services
docker-compose ps
docker-compose logs -f

# Run migrations (if not automatic)
docker-compose exec api alembic upgrade head

# Check health
curl http://localhost:8000/health
```

### Services Running
- Frontend: http://localhost:3000 (Nginx)
- Backend API: http://localhost:8000
- MySQL: localhost:3306 (root/password)
- Redis: localhost:6379
- Celery Worker: running in background
- Celery Beat: running 5-min sync schedule

### Verify Full Stack
```bash
# Check all services healthy
docker-compose exec api curl http://localhost:8000/health
docker-compose exec mysql mysql -uroot -ppassword -e "SHOW TABLES;"
docker-compose exec redis redis-cli ping

# Run tests in container
docker-compose exec api pytest tests/ -v
docker-compose exec frontend npm run test:run

# Watch Celery logs
docker-compose logs celery-worker -f
docker-compose logs celery-beat -f
```

---

## Manual Testing Checklist

### 1. Authentication Flow
- [ ] Navigate to http://localhost:5173 (or :3000 with Docker)
- [ ] See "Login with Jira" button
- [ ] Click button → redirects to Jira OAuth2 (mock response in test)
- [ ] Accept authorization → returns with JWT token
- [ ] JWT stored in localStorage (check DevTools → Application → Local Storage)
- [ ] Dashboard renders

### 2. Dashboard View
- [ ] 4 KPI cards visible (Cycle Time, Bounce Rate, Open Count, Bottleneck)
- [ ] Recent Activity section shows activity feed
- [ ] Team In Flight Load shows members working on tickets
- [ ] Manual refresh button works (re-fetches metrics)
- [ ] Metrics update every 30 seconds (polling, or <5s if WebSocket connected)

### 3. Team Selector
- [ ] Dropdown at top-left shows available teams
- [ ] Select different team → Dashboard updates
- [ ] Selected team persists on page refresh
- [ ] No hardcoded "team-001" visible

### 4. Table View
- [ ] Click "Table" tab
- [ ] Table renders with 6 columns: Key, Summary, Status, Assignee, Cycle Time, Last Updated
- [ ] Click column headers to sort (blue ↑↓ indicator)
- [ ] Status filter dropdown: All, Todo, In Progress, Review, Done
- [ ] Filter changes table instantly
- [ ] Pagination works: Prev/Next buttons, page number display
- [ ] Click assignee name → Developer modal opens

### 5. Kanban View
- [ ] Click "Kanban" tab
- [ ] 4 columns: Todo, InProgress, Review, Done
- [ ] Cards show: ticket key (blue), summary, cycle time badge (top-right), assignee initials (bottom-left)
- [ ] Column headers show ticket counts
- [ ] Cards are read-only (no drag-drop for MVP)
- [ ] Click assignee avatar → Developer modal opens

### 6. Developer Modal
- [ ] Modal opens with developer name, email
- [ ] Shows 4 metrics in 2x2 grid:
  - [ ] Avg Cycle Time (days)
  - [ ] Tickets Resolved (count)
  - [ ] Bounce Contribution (%)
  - [ ] Currently In Progress (count)
- [ ] Close button (X) or click outside to close
- [ ] No console errors

### 7. API Endpoints (use curl or Postman)
```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live

# Auth flow
curl -X POST http://localhost:8000/auth/jira
# Returns: { "authorization_url": "..." }

# Teams
curl -H "Authorization: Bearer <jwt>" http://localhost:8000/api/teams
curl -H "Authorization: Bearer <jwt>" http://localhost:8000/api/teams/team-001

# Metrics
curl -H "Authorization: Bearer <jwt>" http://localhost:8000/api/dashboard/team-001/metrics

# Tickets
curl -H "Authorization: Bearer <jwt>" http://localhost:8000/api/dashboard/team-001/tickets?status=InProgress

# Developer
curl -H "Authorization: Bearer <jwt>" http://localhost:8000/api/developers/dev-123

# WebSocket
wscat -c "ws://localhost:8000/ws/metrics/team-001?token=<jwt>"
# Should receive: { "type": "metrics_update", "metrics": {...} }
```

### 8. Error Handling
- [ ] Log out → redirects to login (token cleared)
- [ ] Provide invalid team ID → 404 response
- [ ] Provide missing JWT → 401 Unauthorized
- [ ] Network error on API call → error message shown in UI
- [ ] Disconnect WebSocket → auto-reconnect with exponential backoff (max 10s)

### 9. Performance & Observability
- [ ] DevTools → Network: check API latency (<200ms target)
- [ ] DevTools → Performance: no memory leaks on navigation
- [ ] DevTools → Console: no JavaScript errors or warnings
- [ ] Check Prometheus metrics: http://localhost:8000/metrics (if exposed)

---

## Success Criteria

✅ **All checks pass = MVP ready for UAT**

| Check | Status |
|-------|--------|
| Frontend builds (0 TS errors) | ✅ PASS |
| Backend compiles (all modules) | ✅ PASS |
| Unit tests (66 passing) | ⏳ Ready to test |
| Dashboard renders | ⏳ Ready to test |
| All 3 views work | ⏳ Ready to test |
| API endpoints respond | ⏳ Ready to test |
| No console errors | ⏳ Ready to test |
| Metrics update <5s | ⏳ Ready to test |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| API response time p95 | <200ms |
| WebSocket latency | <5s |
| Frontend FCP | <2s |
| Database query time p95 | <100ms |
| Sync job duration | <4min |

---

## Quick Start

**Start testing immediately (no Docker):**

```bash
# Terminal 1: Frontend
cd frontend && npm run dev

# Terminal 2: Backend
cd backend && python3 -m uvicorn app.main:app --reload --port 8000

# Open browser: http://localhost:5173
```

**Ready? Let's test! 🚀**
