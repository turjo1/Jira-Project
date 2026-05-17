# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Jira Team Performance Analytics** is a real-time dashboard platform that helps engineering managers track team velocity, identify bottlenecks, and measure developer performance through Jira data. The system ingests Jira ticket data every 5 minutes, calculates key metrics in real-time, and provides multiple dashboard views.

**Status:** Approved for implementation (12-14 week MVP)  
**Architecture:** React (frontend) + FastAPI (backend) + MySQL (database) + Celery (async jobs) + Kubernetes (infrastructure)

## Quick Navigation

Start here based on your role:

- **Full-stack/deciding scope:** Read `ARCHITECTURE.md` first (system overview, data flow, design decisions)
- **Frontend work:** Start with `FRONTEND-GUIDE.md`, then reference `DESIGN-SYSTEM-Guide.md` and the design prototypes in `jira-project/project/`
- **Backend work:** Start with `BACKEND-API.md` for endpoint specs, then `DATABASE-SCHEMA.md` for data model
- **Infrastructure/DevOps:** Follow `KUBERNETES-DEPLOYMENT.md` after reviewing `ARCHITECTURE.md`
- **Testing strategy:** See `TESTING-STRATEGY.md`
- **Real-time features:** See `WEBSOCKET-GUIDE.md` for connection lifecycle and message protocols
- **Security:** See `SECURITY-RUNBOOK.md` for Jira OAuth2 integration and credential storage

The `TECHNICAL-DOCUMENTATION-INDEX.md` file provides a complete roadmap for all developers.

## Project Structure

```
├── ARCHITECTURE.md                    # System design, data flow, tech rationale
├── BACKEND-API.md                     # FastAPI endpoint specifications
├── DATABASE-SCHEMA.md                 # MySQL schema, indexes, migrations
├── DESIGN-SYSTEM-Guide.md             # UI component specs (MetricsTile, DataTable, etc.)
├── DESIGN-HANDOFF-Components.md       # Component library from design tool
├── DESIGN-HANDOFF-README.md           # Design handoff instructions
├── PRD-Team-Performance-Analytics.md  # Product requirements document
├── TECHNICAL-DOCUMENTATION-INDEX.md   # Complete documentation index and phases
├── tailwind.config.js                 # Tailwind CSS configuration
├── jira-project/
│   └── project/                       # Design prototypes (HTML/CSS/JS)
│       ├── Workpulse.html            # Main prototype (read top-to-bottom)
│       ├── src/
│       │   ├── app.jsx               # Root component
│       │   ├── dashboard.jsx         # Dashboard view
│       │   ├── table.jsx             # Table view
│       │   ├── board.jsx             # Kanban board view
│       │   ├── modals.jsx            # Modal components
│       │   ├── shared.jsx            # Shared utilities
│       │   └── data.js               # Mock data
│       └── styles.css                # Styling
└── [Future: backend/, frontend/ directories for implementation]
```

## Key Architectural Decisions

### 5-Minute Sync Cycle
- **Why:** Balances freshness (real-time expectations) vs. Jira API quota constraints
- **Data flow:** Celery Beat → Fetch Jira → Calculate metrics → Broadcast via WebSocket
- **Implication:** Dashboard data max 5 minutes old; client sees updates within 5 seconds

### WebSocket for Real-Time Updates
- **Why:** Eliminates polling overhead, enables instant metric updates when new sync completes
- **Architecture:** Server registers connected clients in memory, broadcasts changes via Redis pub/sub (if scaled horizontally)
- **Implication:** Stateful connections require auto-reconnect logic client-side

### MySQL + Celery + Redis Stack
- **Why:** MySQL for audit trail & transactional data; Celery for proven job scheduling; Redis for WebSocket scaling
- **Implication:** Extra infrastructure complexity but supports 1-5M tickets per team with <1s queries

### JWT Authentication (24h) + Jira OAuth2
- **Why:** Stateless auth reduces session storage; OAuth2 uses Jira identity (no password handling)
- **Implication:** Token refresh logic required; credential encryption critical (AES-256) for stored Jira tokens

## Design Prototype Handoff

The `jira-project/project/` directory contains **HTML/CSS/JS prototypes** (not production code). When implementing:

1. **Read the primary design file** (`Workpulse.html`) top-to-bottom
2. **Follow its imports** — understand how shared components, CSS, and scripts fit together
3. **Implement as React components** — match the visual output pixel-perfectly, but structure the code for real data and interactivity
4. **Reference the design system** — see `DESIGN-SYSTEM-Guide.md` for component specs

Do NOT copy the prototype's internal structure unless it fits your target tech stack.

## Development Setup

### Frontend Development
```bash
# Install dependencies
npm install

# Start development server (typically port 3000)
npm run dev

# Build production bundle
npm run build

# Run tests
npm test
```

**Tech stack:** React 18, TypeScript 5, Tailwind CSS 3, TanStack Query, Zustand  
**Testing:** React Testing Library (unit), Playwright (E2E)

### Backend Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server (FastAPI, typically port 8000)
uvicorn app.main:app --reload

# Run tests
pytest

# Run single test
pytest tests/test_auth.py::test_jira_oauth -v
```

**Tech stack:** Python 3.11+, FastAPI 0.104+, SQLAlchemy 2.0+, Pydantic 2.x, pytest  
**Database:** MySQL 8.0+ (via docker-compose for local development)  
**Job scheduler:** Celery 5.3+ with Redis 7.x

### Full Stack (Docker Compose)
```bash
# Start all services locally
docker-compose up

# Services running:
# - FastAPI backend: http://localhost:8000
# - React frontend: http://localhost:3000
# - MySQL: localhost:3306
# - Redis: localhost:6379
# - Celery worker (background)
```

## Implementation Phases (12-14 weeks)

**Phase 1 (Weeks 1-2):** Infrastructure — Kubernetes, MySQL, Redis, CI/CD setup  
**Phase 2 (Weeks 3-5):** Core backend — FastAPI, Jira OAuth2, user management, API endpoints  
**Phase 3 (Weeks 5-7):** Data sync — Celery jobs, 5-minute sync, metric calculations  
**Phase 4 (Weeks 6-9):** Frontend — React setup, Dashboard/Table/Kanban views, WebSocket integration  
**Phase 5 (Weeks 8-10):** Testing — Unit/integration/E2E tests, real-time validation  
**Phase 6 (Weeks 11-12):** Deployment & monitoring — Prometheus metrics, ELK logging, performance optimization  
**Phase 7 (Weeks 13-14):** UAT & iteration — User acceptance testing, bug fixes, production readiness  

See `TECHNICAL-DOCUMENTATION-INDEX.md` § Implementation Phases for detailed checklist.

## Core Metrics & Calculations

**Dashboard KPIs (4 metrics):**
1. **Cycle Time** — Average days from creation to resolution (resolved tickets, last 30 days)
2. **Bounce Rate** — % of tickets transitioning back from Done to prior statuses
3. **Open Count** — Total unresolved tickets
4. **Bottleneck** — Status with slowest average time-in-status

**Data sources:** Jira ticket transitions, status history, created/resolved dates  
**Refresh:** Every 5 minutes; WebSocket broadcasts updates to all connected clients  
**Precision:** Real-time on client side (<1s database query), batch calculated server-side

## Security Posture

- **Authentication:** Jira OAuth2 (user identity) + JWT (API requests, 24h expiry)
- **Authorization:** Users view their own teams only; managers see team data; admins manage all
- **Credential storage:** Jira tokens encrypted at rest (AES-256)
- **Rate limiting:** 1000 req/min per user
- **HTTPS enforced** in production; JWT uses HS256 signing
- **See `SECURITY-RUNBOOK.md`** for detailed procedures (OAuth2 flow, token rotation, audit logging)

## Scalability Targets

| Component | Limit | Solution if exceeded |
|-----------|-------|----------------------|
| Concurrent users | 500 | Add FastAPI replicas (6+) |
| Tickets per team | 5M | MySQL read replicas + partitioning |
| Sync duration | 5 min | Parallel Jira API calls, delta syncs |
| WebSocket connections | 50K | Redis pub/sub + horizontal scaling |
| API response time p95 | 200ms | Query indexing, caching layer |

## Observability & Monitoring

**Key metrics to track:**
- API latency (target <200ms p95)
- WebSocket update latency (target <500ms)
- Sync job duration (target <4 min)
- Error rate (target <0.1%)
- Database query time (target <100ms p95)

**Logging:** FastAPI (info/error), Celery (info/error), slow query log (>1s), WebSocket events  
**Health checks:** `GET /health`, `GET /ready`, `GET /live`, `GET /metrics` (Prometheus)  
**Dashboards:** Prometheus (metrics), ELK Stack (logs), custom Grafana dashboards  

See `MONITORING-GUIDE.md` for setup details.

## Testing Strategy

- **Unit tests:** FastAPI endpoints (pytest), React components (React Testing Library)
- **Integration tests:** API + database, WebSocket handshake
- **E2E tests:** Full user flows (Playwright)
- **Fixtures:** Mock Jira API responses, test database seeding
- **Coverage targets:** 80%+ on critical paths (auth, sync, metrics)

See `TESTING-STRATEGY.md` for detailed approach and test organization.

## Important Files Reference

- **Design prototypes:** `jira-project/project/Workpulse.html` (primary), supporting JSX/CSS
- **System overview:** `ARCHITECTURE.md` (data flow, component breakdown, deployment)
- **API endpoints:** `BACKEND-API.md` (REST spec, auth flow, request/response schemas)
- **Database:** `DATABASE-SCHEMA.md` (ER diagram, indexes, Alembic migrations)
- **Real-time:** `WEBSOCKET-GUIDE.md` (connection lifecycle, message protocols, auto-reconnect)
- **Infrastructure:** `KUBERNETES-DEPLOYMENT.md` (K8s manifests, Docker, CI/CD)

## Success Criteria

When complete, verify:
- [ ] All 4 dashboard metrics update within 5 seconds of Jira change
- [ ] API responds <200ms p95 with 100 concurrent users
- [ ] Zero data loss during deployment
- [ ] WebSocket auto-reconnects within 10 seconds on disconnect
- [ ] Database handles 1M+ tickets with <1 second query time
- [ ] Sync completes in <4 minutes for typical team
- [ ] WCAG 2.1 AA accessibility compliance

## Notes for Future Contributors

This project emphasizes **quality over volume**: all Jira integrations should respect API quotas, all metric calculations must audit-trail transitions, and all user interactions must validate JWT before serving data. The real-time requirement (5-second metric updates) is load-bearing; design for eventual consistency across the WebSocket broadcast layer.

When adding features, check `ARCHITECTURE.md` § Key Design Decisions to understand the trade-offs that shaped the current approach.
