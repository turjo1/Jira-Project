# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository. This document blends **behavioral principles** (how to work effectively) with **project specifics** (what to build).

## Core Collaboration Principles

These principles minimize mistakes and rework:

### 1. Think Before Coding
- **State assumptions explicitly.** If a request is ambiguous, ask clarifying questions before implementing.
- **Surface uncertainties.** Don't proceed silently with guesses; flag what's unclear.
- **Present alternatives.** When multiple valid interpretations exist, show them and let the user choose.
- **Example:** Instead of assuming "add validation" means input sanitization, ask: "Do you want client-side validation, server-side validation, or both? What should happen on invalid input?"

### 2. Simplicity First
- **Minimize code.** If you write 200 lines and it could be 50, rewrite it.
- **No speculative features.** Don't add "just in case" functionality; build only what's requested.
- **No premature abstractions.** Three similar lines is better than a helper that isn't proven necessary.
- **No over-engineering.** Match the scope of the request, not hypothetical future requirements.
- **Example:** A one-shot data migration script doesn't need error recovery; a production sync job does.

### 3. Surgical Changes
- **Touch only what's necessary.** When editing code, change what's needed for the request; leave everything else untouched.
- **No unnecessary refactoring.** Don't improve adjacent code unless it's blocking the current task.
- **No reformatting unless changing.** Style fixes are separate commits, not bundled into feature work.
- **Remove only what you broke.** Safe to delete unused imports/variables that YOUR changes created.
- **Example:** Fixing a bug in `processPayment()` doesn't mean refactoring `validateUser()` in the same file, even if it looks improvable.

### 4. Goal-Driven Execution
- **Define verifiable success criteria first.** Convert vague requests into testable objectives.
- **Make it testable.** "Add validation" becomes "Write tests for invalid inputs, then make them pass."
- **Measure before claiming done.** Run the feature, confirm it works, check for regressions.
- **Example:** Instead of "Make the dashboard faster," specify "Reduce p95 API response time from 500ms to <200ms, test with 100 concurrent users."

**How to request tasks:** Be specific. Instead of "improve the auth flow," say "the login button redirects to settings instead of dashboard—fix this and verify OAuth token refreshes correctly." Concrete requests prevent wasted implementation.

---

## ⚠️ CRITICAL: Design Source of Truth

**The frontend must match `Workpulse.html` EXACTLY.** This is a standalone HTML file (open in browser, no build step). It is NOT a production architecture blueprint—it is the visual design spec.

❌ **Do NOT interpret Workpulse.html as "this should become a TypeScript/Vite app"**  
✅ **Do interpret it as "build HTML/React that looks and works exactly like this when opened in a browser"**

For questions on implementation approach, read `IMPLEMENTATION-BRIEFING.md` first.

---

## Project Overview

**Jira Team Performance Analytics** is a real-time dashboard platform that helps engineering managers track team velocity, identify bottlenecks, and measure developer performance through Jira data. The system ingests Jira ticket data every 5 minutes, calculates key metrics in real-time, and provides multiple dashboard views.

**Status:** Approved for implementation (12-14 week MVP)  
**Architecture:** React (frontend) + FastAPI (backend) + MySQL (database) + Celery (async jobs) + Kubernetes (infrastructure)

## Quick Navigation

Pick your entry point:

| Task | Start with |
|------|------------|
| **Unclear what to build?** | Ask for clarification first (see Principle 1) |
| **Full-stack scope decisions** | `ARCHITECTURE.md` (data flow, design rationale, trade-offs) |
| **Frontend implementation** | `FRONTEND-GUIDE.md` → `DESIGN-SYSTEM-Guide.md` → `jira-project/project/Workpulse.html` |
| **Backend endpoints** | `BACKEND-API.md` (REST specs, auth, schemas) → `DATABASE-SCHEMA.md` |
| **Real-time features** | `WEBSOCKET-GUIDE.md` (lifecycle, protocols) + `BACKEND-API.md` |
| **Infrastructure/DevOps** | `KUBERNETES-DEPLOYMENT.md` after reviewing `ARCHITECTURE.md` |
| **Security questions** | `SECURITY-RUNBOOK.md` (OAuth2 flow, token storage, audit logging) |
| **Testing approach** | `TESTING-STRATEGY.md` (unit/integration/E2E with fixtures) |
| **Missing docs?** | Check `TECHNICAL-DOCUMENTATION-INDEX.md` for the complete roadmap |

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

The frontend is served as a **standalone HTML prototype** from `jira-project/project/` (no build step).

```bash
# Serve the Workpulse prototype on port 3000
cd jira-project/project
python3 -m http.server 3000

# Then open: http://localhost:3000/Workpulse.html
```

All frontend source files are in `jira-project/project/`:
- `Workpulse.html` — main entry point (loads React + Babel via CDN, no build required)
- `styles.css` — all styling and design system
- `src/app.jsx` — root app component, nav bar, view routing
- `src/data.js` — mock data (team members, tickets, metrics)
- `src/dashboard.jsx`, `src/board.jsx`, `src/table.jsx` — the three views
- `src/modals.jsx`, `src/ai-search.jsx`, `src/shared.jsx` — modal and component library

**Tech stack:** React 18 (via CDN), Babel (browser JSX transpilation), Vanilla CSS (no Tailwind or build tools)  
**Testing:** Manual testing in browser (no automated test suite yet)

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

### Quick Start (Development)
```bash
# Run the start script (starts backend + frontend)
./start-dev.sh

# Or manually start each service:

# Backend (terminal 1)
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd jira-project/project
python3 -m http.server 3000

# Then open: http://localhost:3000/Workpulse.html
```

**Running services:**
- Frontend: `http://localhost:3000/Workpulse.html`
- Backend: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

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

## Common Pitfalls to Avoid

These mistakes happen when skipping the principles above:

| Pitfall | Why it's costly | Prevention |
|---------|-----------------|-----------|
| **Building before clarifying** | Implement feature A when user meant feature B; wasted hours. | Ask ambiguous questions up-front (Principle 1) |
| **Over-engineering** | Add 3 abstraction layers for a one-off job; code is hard to debug later. | Build exactly what's asked; no "future-proofing" (Principle 2) |
| **Refactoring while fixing** | Fix a bug in one function, "improve" two adjacent functions; 3× the review surface. | Change only what's needed; leave untouched code alone (Principle 3) |
| **Calling it "done" without testing** | Code merges, breaks production, then requires emergency revert. | Verify success criteria before reporting done (Principle 4) |
| **Vague feature requests** | "Make it faster" → implement caching everywhere → still slow in wrong place. | Specify testable goals: "Reduce p95 latency from 500ms to <200ms, test with 100 users" (Principle 4) |

---

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

---

## How to Request Features & Changes

**Vague requests waste time.** To work efficiently, apply Principle 4 (Goal-Driven Execution):

| Request type | ❌ Vague | ✅ Specific (testable) |
|--------------|---------|----------------------|
| **Fix a bug** | "The dashboard is broken" | "The Cycle Time metric shows NaN after a team member resolves a ticket. Expected: metric should update to reflect 30-day average. Test: resolve a ticket, verify metric within 5 seconds" |
| **Add feature** | "Implement filtering" | "Add a status filter dropdown to Dashboard view. Clicking 'In Progress' should update all 4 metrics to show only tickets in that status. Verify with Playwright E2E test." |
| **Improve perf** | "Make it faster" | "Reduce Dashboard API response time from 800ms to <200ms p95 when 100 concurrent users request data. Measure with 5-minute baseline before/after." |
| **Code cleanup** | "Refactor auth.py" | "The `validate_jira_token()` function repeats error handling 3 times. Extract common logic, write unit tests, ensure all existing auth tests still pass." |

**Success = user confirms the feature works as described.** Always test before reporting "done."

---

## Verification Checklist

When completing a feature or fix, verify against these criteria (Goal-Driven Execution):

### Frontend Changes
- [ ] Feature works as requested (manual test in browser)
- [ ] No regressions in other views (Dashboard, Table, Kanban)
- [ ] Responsive on mobile (resize to 375px width)
- [ ] Tests pass: `npm test`
- [ ] Build succeeds: `npm run build`

### Backend Changes
- [ ] New endpoint tested with curl/Postman or existing test suite
- [ ] Database query time <1s (check slow query log if added queries)
- [ ] All existing tests pass: `pytest`
- [ ] New functionality has unit + integration tests
- [ ] JWT validation enforced on protected routes

### Real-Time (WebSocket) Changes
- [ ] Data syncs within 5 seconds of Jira change
- [ ] Client auto-reconnects on disconnect
- [ ] No memory leaks with 100+ concurrent connections (check process memory)

### Before Calling "Done"
- [ ] Ran the feature end-to-end locally
- [ ] Checked for regressions in related features
- [ ] Code review would be straightforward (minimal, surgical changes)

---

## Project Philosophy

This project emphasizes **quality over volume** and **clarity over cleverness**:

- **All Jira integrations respect API quotas.** Don't implement features that spam the Jira API.
- **All metric calculations audit-trail transitions.** If a number seems wrong, the calculation and source data must be auditable.
- **All user interactions validate JWT before serving data.** No exceptions for convenience.
- **Real-time updates (5-second target) are load-bearing.** Design WebSocket broadcasts for eventual consistency, not strong consistency.

When adding features, read `ARCHITECTURE.md` § Key Design Decisions to understand the trade-offs that shaped the current approach. Ask questions before implementing.
