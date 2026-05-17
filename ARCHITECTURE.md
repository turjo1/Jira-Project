# Architecture Document: Jira Team Performance Analytics

**Status:** Approved for Implementation  
**Version:** 1.0  
**Last Updated:** 2026-05-16

---

## System Overview

Jira Team Performance Analytics is a real-time dashboard platform that helps engineering managers and product owners track team velocity, identify bottlenecks, and measure developer performance through Jira data.

### Core Purpose
- Ingest Jira ticket data every 5 minutes
- Calculate key metrics: cycle time, bounce rates, bottlenecks
- Provide real-time dashboards and drill-down views
- Enable data-driven team management decisions

### Key Requirements
- 5-minute data sync latency
- Real-time metric updates (<1 second)
- Support 100-500 concurrent users
- Handle 1-5M tickets per team
- WCAG AA accessibility

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Client Layer (React + TypeScript)               │
│  - Dashboard (metrics tiles)  - Table View  - Kanban Board   │
│  - Developer Modal  - Real-time WebSocket updates            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│         API Layer (FastAPI + Pydantic)                       │
│  - Authentication (JWT + Jira OAuth2)                        │
│  - REST endpoints (/teams, /metrics, /tickets)               │
│  - WebSocket gateway (/ws/metrics/:teamId)                   │
└──────────────────────────┬──────────────────────────────────┘
                  ┌─────────┼─────────┐
        ┌─────────▼──┐  ┌──▼─────────┬────────┬────────────┐
        │  MySQL     │  │  Celery    │ Redis  │ Jira API   │
        │  - Users   │  │  + Redis   │        │ (Cloud)    │
        │  - Teams   │  │  - Sync    │        │            │
        │  - Tickets │  │  - Calc    │        │ Webhooks   │
        │  - Metrics │  │  - Alert   │        │ (planned)  │
        └────────────┘  └────────────┘        └────────────┘
```

---

## Data Flow: 5-Minute Sync

```
Celery Beat (Every 5 min)
    │
    ▼ Trigger sync_jira_data()
    
1. Fetch from Jira API
   - GET /rest/api/3/issues
   - Filter: updated >= last_sync_time
   - With transition history
    │
    ▼
2. Process & Calculate
   - Cycle time = resolved_date - created_date
   - Bounce = Done → prior_status transitions
   - Current status & time in status
   - Bottleneck = slowest status
    │
    ▼
3. Upsert to MySQL
   - Insert new tickets
   - Update existing tickets
   - Preserve audit trail
    │
    ▼
4. Calculate Team Metrics
   - SELECT AVG(cycle_time) WHERE resolved > 30 days ago
   - SELECT COUNT(*) WHERE status = 'Done' AND transitioned_back = true
   - SELECT status, AVG(days_in_status) GROUP BY status
    │
    ▼
5. Broadcast via WebSocket
   - All connected clients for this team
   - Update: {cycle_time, bounce_rate, open_count, bottleneck}
   - Client-side state updates immediately
```

---

## User Request Flow

```
1. POST /auth/jira
   - FastAPI redirects to Jira OAuth2
   - User authorizes
   - Receives code → exchanges for access_token
   - Stores encrypted token in MySQL
   - Returns JWT (valid for 24h)

2. GET /teams/:teamId/metrics
   - Validates JWT
   - Queries MySQL for latest metrics
   - Returns 4 KPIs + timestamps

3. WS /ws/metrics/:teamId
   - Establishes WebSocket
   - Server registers client in memory
   - Sends current metrics immediately
   - Client auto-reconnects if disconnected

4. User Interactions
   - Sort/Filter: Frontend handles locally
   - Drill-down: GET /developers/:id (fetch from DB)
   - Details modal: Loads in <1 second
```

---

## Component Breakdown

### Frontend
```
React App (Single Page Application)
├── Contexts & Hooks
│   ├── useAuth (JWT token management)
│   ├── useTeams (team selection)
│   ├── useMetrics (real-time updates)
│   ├── useTickets (sorted/filtered tickets)
│   └── useWebSocket (connection lifecycle)
│
├── Views
│   ├── Dashboard (2×2 metric tiles)
│   ├── TableView (sortable, filterable)
│   ├── KanbanBoard (4 columns by status)
│   └── Modals (developer details)
│
└── Components (per DESIGN-SYSTEM-Guide.md)
    ├── MetricsTile
    ├── StatusBadge
    ├── DataTable
    └── DeveloperModal
```

### Backend
```
FastAPI Application
├── main.py (app initialization)
├── routers/
│   ├── auth.py (OAuth2, JWT)
│   ├── teams.py (GET /teams)
│   ├── metrics.py (GET /teams/:id/metrics)
│   ├── tickets.py (GET /tickets with filters)
│   └── developers.py (GET /developers/:id)
│
├── models/
│   ├── database.py (SQLAlchemy ORM)
│   ├── schemas.py (Pydantic validation)
│   └── calculations.py (cycle_time, bounce logic)
│
├── services/
│   ├── jira_service.py (Jira API calls)
│   ├── metric_service.py (aggregate calculations)
│   └── auth_service.py (OAuth2, JWT)
│
├── websocket/
│   ├── manager.py (client lifecycle)
│   ├── handlers.py (incoming messages)
│   └── broadcasters.py (send to clients)
│
└── tasks/
    └── celery_tasks.py (sync_jira_data, calculate_metrics)
```

### Database Schema
```
Users
├── id, email, jira_user_id, role, created_at

Teams
├── id, name, jira_project_key, manager_id, created_at

Credentials
├── id, user_id, jira_token_encrypted, token_expires_at

Tickets
├── id, team_id, jira_key, title, assignee_id, status
├── created_at, resolved_at, cycle_time_days, last_synced

TicketTransitions
├── id, ticket_id, from_status, to_status, transitioned_at

Metrics (calculated every sync)
├── id, team_id, date, avg_cycle_time, bounce_rate
├── open_count, bottleneck_status, calculated_at
```

---

## API Specification (Summary)

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| GET | /health | Health check | Public |
| POST | /auth/jira | Initiate OAuth2 | Public |
| POST | /auth/logout | Clear session | JWT |
| GET | /teams | List user's teams | JWT |
| GET | /teams/:id/metrics | Dashboard KPIs | JWT |
| GET | /teams/:id/tickets | Paginated tickets | JWT |
| GET | /developers/:id | Developer stats | JWT |
| WS | /ws/metrics/:teamId | Real-time updates | JWT |

---

## Deployment Architecture

### Local Development
```bash
docker-compose up
# Starts: FastAPI (8000), React (3000), MySQL (3306), Redis (6379), Celery
```

### Kubernetes (Production)
```
Namespace: jira-analytics

Deployments:
├── fastapi (3 replicas, resources: 500m CPU, 512Mi RAM)
├── celery-worker (2 replicas)
├── nginx-frontend (2 replicas)

StatefulSets:
├── mysql (1 replica, PV: 10Gi)
└── redis (1 replica, PV: 1Gi)

Services:
├── fastapi (ClusterIP:8000)
├── frontend (ClusterIP:80)
├── mysql (ClusterIP:3306)
└── redis (ClusterIP:6379)

ConfigMaps & Secrets:
├── jira-oauth-config
├── db-credentials
└── jwt-signing-key
```

---

## Security Model

### Authentication
- Jira OAuth2 for user identity
- JWT token for API requests (24h expiry)
- Refresh token for token renewal (14d expiry)

### Authorization
- Users can only view their own teams' data
- Managers can view all team members' data
- Admins can manage users and teams

### Data Protection
- Jira API tokens encrypted at rest (AES-256)
- HTTPS enforced in production
- JWT uses HS256 signing
- Rate limiting: 1000 req/min per user

---

## Scalability Limits & Solutions

| Component | Current Limit | Solution |
|-----------|---------------|----------|
| **Concurrent Users** | 500 | Add FastAPI replicas (6+) |
| **Tickets per Team** | 5M | Add MySQL read replicas |
| **Sync Duration** | 5 min | Parallel processing, delta syncs |
| **WebSocket Connections** | 50K | Horizontal scaling with Redis pub/sub |
| **API Response Time** | 200ms p95 | Caching, database indexing |

---

## Monitoring & Observability

### Metrics to Track
- **API Latency** — Target: <200ms p95
- **WebSocket Latency** — Target: <500ms for updates
- **Sync Duration** — Target: <4 min
- **Error Rate** — Target: <0.1%
- **Database Query Time** — Target: <100ms p95

### Logging Strategy
- FastAPI logs: info level for API calls, error level for exceptions
- Celery logs: info for tasks, error for failures
- MySQL slow query log: queries >1s
- WebSocket events: connection/disconnection

### Health Checks
```
GET /health          — All systems up?
GET /ready           — Ready for traffic?
GET /live            — Process alive?
GET /metrics         — Prometheus metrics
```

---

## Key Design Decisions

| Decision | Why | Trade-off |
|----------|-----|-----------|
| **5-min sync** | Balance freshness vs. API quota | Data max 5min old |
| **WebSocket** | Real-time updates, no polling overhead | Stateful connections |
| **MySQL** | Mature, ACID, good for transactional data | Not ideal for time-series |
| **Celery** | Proven job scheduler, excellent error handling | Extra infrastructure (Redis) |
| **JWT** | Stateless, no session storage needed | Token lifetime trade-off |
| **Kubernetes** | Team expertise, multi-service orchestration | Higher ops complexity |

---

## Deployment Timeline

- **Weeks 1-2:** Infrastructure setup (K8s, MySQL, Redis)
- **Weeks 3-5:** Backend development (API, auth, sync)
- **Weeks 6-9:** Frontend development (UI, real-time)
- **Weeks 10-12:** Integration, testing, optimization
- **Weeks 13-14:** UAT, monitoring, production deployment

---

## Success Criteria

- [ ] All 4 dashboard metrics update within 5 seconds of Jira change
- [ ] API responds <200ms p95 with 100 concurrent users
- [ ] Zero data loss during deployment
- [ ] WebSocket reconnects automatically within 10 seconds
- [ ] Database handles 1M+ tickets with <1 second query time
- [ ] Accessibility: WCAG 2.1 AA compliant
- [ ] Sync completes in <4 minutes for typical team

---

## Next Steps

1. Review and approve this architecture
2. Proceed to **BACKEND-API.md** for endpoint specifications
3. See **DATABASE-SCHEMA.md** for detailed data model
4. Reference **KUBERNETES-DEPLOYMENT.md** for infrastructure

**Questions?** Contact engineering lead or refer to specific documentation files.
