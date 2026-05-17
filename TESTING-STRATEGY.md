# Testing Strategy: Jira Team Performance Analytics

**Status:** Approved v1.0 — circulating to backend + frontend
**Owner:** QA Engineer
**Version:** 1.0
**Last Updated:** 2026-05-16

---

## Purpose

Define how every success criterion in `CLAUDE.md` and `ARCHITECTURE.md` is verified, from a unit test up through a chaos drill in staging. This document is the contract between QA and the implementing teams: backend, frontend, and infra agree to ship code that satisfies the gates below.

---

## Success criteria → verification

| # | Criterion (from CLAUDE.md) | Verification layer | Gate |
|---|---|---|---|
| 1 | 4 dashboard metrics update within 5s of Jira change | E2E + integration | Playwright timer from Celery `sync_jira_data` start to DOM patch < 5000 ms p95 |
| 2 | API responds <200ms p95 with 100 concurrent users | Load | k6 soak, p95 < 200 ms, p99 < 500 ms, error rate < 0.1% |
| 3 | Zero data loss during deployment | Chaos integration | Rolling restart while sync runs; pre/post ticket and transition counts reconcile exactly |
| 4 | WebSocket auto-reconnects within 10s | E2E | Forced disconnect (net offline, 1006, idle timeout) → first `metrics_update` frame within 10 s |
| 5 | DB handles 1M+ tickets with <1s query | DB load | `EXPLAIN ANALYZE` + repeated runs on seeded 1M / 5M datasets; p95 < 1 s |
| 6 | Sync completes in <4 min for typical team | Integration | Wall-clock timing on 5M-ticket fixture < 240 s, no Celery retries |
| 7 | WCAG 2.1 AA compliance | A11y | axe-core in Playwright = 0 critical/serious violations, plus screen reader and keyboard pass |

Each gate must be green in CI before a release tag is cut.

---

## Test pyramid and coverage targets

| Layer | Share of suite | Tooling | Coverage target |
|---|---|---|---|
| Unit | ~60% | pytest, Vitest + React Testing Library | **≥80% on critical paths**: auth, sync, metric calculations, WebSocket manager |
| Integration | ~25% | pytest + testcontainers (MySQL, Redis), `respx`/`pytest-httpx` against mock Jira, FastAPI `TestClient` + `websockets` | All API endpoints, sync task, WS handshake covered at least once |
| End-to-end | ~15% | Playwright (TS) | 12 critical user flows enumerated below |

Coverage is reported per-layer (backend, frontend). The 80% gate applies only to the four critical-path modules; ancillary code is best-effort. CI fails if critical-path coverage drops below 80%.

---

## Critical user flows (E2E)

Run on every PR to `main` against the `docker-compose` stack; run against staging on every release candidate.

1. Jira OAuth2 login — happy path → JWT issued → cookie set → dashboard renders
2. OAuth2 state mismatch or replay → 400, no token issued
3. Expired JWT → 401 → refresh-token exchange → request retried
4. Refresh token older than 14 days → re-auth required, no silent failure
5. Dashboard load — 4 metric tiles + last-synced timestamp render
6. Live metric update — Celery sync → WS `metrics_update` → tile DOM patch within 5 s
7. WS disconnect → reconnect within 10 s with no duplicate frames
8. Table view sort (`days_in_status` desc) + filter (`status=QA`) + pagination boundary (`skip=100`)
9. Kanban view — column counts equal `GET /tickets?status=…` aggregate
10. Developer modal opens within 1 s with recent tickets and stats
11. Team scoping — user without membership gets 403 on `/teams/{other}/metrics`
12. Rate limit — 1001st request inside 60 s returns 429 with `Retry-After`

---

## Real-time / WebSocket test matrix

Authored alongside `WEBSOCKET-GUIDE.md` (task #31). All items confirmed.

- ✓ Auth: JWT passed via query param at handshake; missing or invalid token rejected before upgrade
- ✓ Reconnect: exponential backoff with jitter, max 10 s to first frame after reconnect
- ✓ Heartbeat: ping/pong every **30 s** prevents idle proxy disconnects
- Subscribe protocol: `{type:"subscribe", team_id}` → server ack; subscribing to an unauthorized team rejected
- Message types covered: `metrics_update`, `ticket_transition`, `sync_started`, `sync_completed`
- Broadcast fan-out: N clients on the same team all receive `metrics_update` within 500 ms (per ARCHITECTURE target)
- Backpressure: a slow client does not block fan-out to others
- Multi-tab: same user, two tabs, both receive updates; logout in one closes the other's WS
- Horizontal scale: when FastAPI is scaled, Redis pub/sub delivers to clients on different pods (staging only)

---

## Error and chaos scenarios

Integration suite must cover each, with assertions on system state, not just response codes:

- **Jira API outage** — 5xx for the full sync window → task retries with backoff, no partial writes, stale-data banner surfaced to UI
- **Jira rate limit (429)** — sync honors `Retry-After`, does not burn quota on retry storm
- **Jira token revoked mid-sync** — sync fails cleanly, user gets re-auth prompt on next request, `credentials.jira_token_encrypted` row is not corrupted
- **MySQL pool exhausted** — graceful 503 with retry hint, never 500
- **Redis down** — Celery degrades, WS broadcast skipped, HTTP API still serves last-cached metrics
- **Clock skew** — JWT `iat`/`exp` validated with **±60 s** tolerance (approved)
- **Malformed Jira payload** — rejected at the Pydantic boundary, logged, no task crash
- **Bounce edge cases** — `created → Done → reopened` counts as one bounce; `Done → Done` does not; reassignment mid-flow preserves audit trail

Chaos drills (staging only): pod kill during sync, network partition between FastAPI and Redis, MySQL primary failover.

---

## Load test profiles

Tooling: k6 for HTTP, a Python `websockets` harness for connection scale.

- **API soak** — 100 VUs × 10 min, mix 70% `GET /metrics`, 20% `GET /tickets`, 10% `GET /developers`. Pass: p95 < 200 ms, p99 < 500 ms, error rate < 0.1%.
- **API spike** — 0 → 500 VUs in 30 s, hold 2 min. Pass: no 5xx, p95 stays < 400 ms during spike.
- **WS scale** — ramp to 5 000 concurrent connections, broadcast every 60 s. Pass: p95 frame delivery < 500 ms.
- **DB stress** — 1 M and 5 M ticket fixtures, run the three sample queries from `DATABASE-SCHEMA.md` at 50 QPS. Pass: p95 < 1 s.

---

## Accessibility (WCAG 2.1 AA)

Automated, every PR:

- axe-core via Playwright on Dashboard, Table, Kanban, and developer modal — zero critical or serious violations
- Color contrast ≥ 4.5:1 for text, ≥ 3:1 for UI components

Manual, every release candidate:

- Keyboard-only walk-through of all 12 critical flows
- NVDA (Windows) and VoiceOver (macOS) announcement check on Dashboard live updates
- `prefers-reduced-motion` respected; no motion-only animation exceeds 5 s without pause

Live region: incoming `metrics_update` frames must be announced via `aria-live=polite` so screen-reader users hear changes without losing context.

---

## Fixtures and test data

Shared, deterministic, generated by a fixture script that backend and QA both depend on:

- **Seed datasets**: 1 K, 100 K, 1 M, 5 M tickets with realistic status distributions and transition density
- **JWT generator**: configurable claims, expiry, signing key, used for negative auth tests
- **WS test harness**: multi-client orchestrator that opens N connections, subscribes, and records latency per frame
- **Mock Jira API server**: Pydantic-typed; supports OAuth2, search/issues, changelogs, rate-limit injection, 5xx injection, token-revoked mode. Reused by backend devs for local development.

**Ownership:** QA owns the seed fixture generator. Backend must sign off on the fixture schema (ticket shape, transition shape, OAuth2 token format) **before Phase 3 starts** — schema changes after that point require a coordinated migration.

**Locations:**
- Mock Jira server: `tests/mock-jira/` (repo root, shipped as a docker-compose service)
- Backend fixtures: `backend/tests/fixtures/`
- Frontend fixtures: `frontend/tests/e2e/fixtures/`

---

## CI gating rules

A PR cannot merge into `main` unless:

- All unit and integration tests pass
- Critical-path coverage ≥ 80%
- Contract tests against `BACKEND-API.md` pass (schema drift = fail)
- Playwright critical-flow suite passes against `docker-compose` stack
- axe-core reports zero critical or serious violations

Load and chaos suites run on a nightly job against staging; failures page QA on call but do not block PR merges.

---

## Test environments

| Env | Purpose | Data | Trigger |
|---|---|---|---|
| Local | Developer iteration | Mock Jira + 1 K tickets | `docker-compose up` |
| CI | PR validation | Mock Jira + 1 K tickets | Every PR |
| Staging | Load, chaos, manual UAT | Mock Jira + 1 M / 5 M tickets | Nightly + release candidates |
| Production | Real users | Real Jira | Read-only canary checks only |

---

## Reporting

- **Coverage** — **Codecov** (approved), per layer, posted as a PR comment; critical-path 80% gate enforced as a required check
- **Load** — k6 summary uploaded to artifact store; trend graph in Grafana
- **A11y** — axe-core JSON diffed against baseline; new violations block the PR
- **Bugs** — Jira project `QA`, linked to failing test ID

---

## Decisions (resolved by team lead 2026-05-16)

| # | Question | Decision |
|---|---|---|
| 1 | Heartbeat cadence | **30 s** (balances 60 s proxy idle timeout vs. frame overhead) |
| 2 | JWT clock-skew tolerance | **±60 s** (covers NTP drift + K8s clock variance) |
| 3 | Coverage tool | **Codecov** |
| 4 | Mock Jira server location | **`tests/mock-jira/`** |
| 5 | Seed fixture generator ownership | **QA owns, backend reviews schema before Phase 3** |

---

**Approved by:** Engineering lead, 2026-05-16. Circulating to backend-engineer and frontend-engineer.

---

**See also:** `ARCHITECTURE.md`, `BACKEND-API.md`, `DATABASE-SCHEMA.md`, `WEBSOCKET-GUIDE.md` (pending), `SECURITY-RUNBOOK.md` (pending)
