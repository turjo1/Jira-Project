# Deployment Checklist: Jira Team Performance Analytics

**Version:** 1.0  
**Status:** Ready for Implementation  
**Project:** Jira Team Performance Analytics  
**Stack:** Python FastAPI + React + MySQL + Celery + Kubernetes  
**Timeline:** 12-14 weeks MVP → Production  

---

## Overview

This checklist ensures readiness across all technical, operational, and organizational dimensions before go-live. Phases are sequential but can overlap for parallel workstreams.

---

## Phase 1: Pre-Deployment Readiness (End of Week 10)

**Owner:** Engineering Lead  
**Timeline:** T-14 days  
**Success Criteria:** All items checked, zero blockers

### Code Quality & Review
- [ ] All code merged to main branch with approved PRs
- [ ] Code review checklist completed (Python/JavaScript style guides, type safety, security)
- [ ] Linting and formatting pass (black, pylint for Python; ESLint for JavaScript)
- [ ] No outstanding TODOs or FIXMEs related to MVP features
- [ ] API documentation reviewed and matches BACKEND-API.md spec
- [ ] Frontend component implementation matches DESIGN-HANDOFF-Components.md

### Testing Coverage
- [ ] Unit tests: ≥80% coverage (pytest for backend, Jest for frontend)
- [ ] Integration tests: All API endpoints tested with real database
- [ ] E2E tests: Critical user flows tested (login → view dashboard → drill down → real-time updates)
- [ ] Test results: All passing in CI/CD pipeline (zero failures)
- [ ] Database migration tests: All Alembic migrations reversible and tested

### Documentation
- [ ] ARCHITECTURE.md reviewed by Tech Lead
- [ ] BACKEND-API.md matches implemented endpoints (no discrepancies)
- [ ] DATABASE-SCHEMA.md matches actual schema (run `SHOW CREATE TABLE` checks)
- [ ] KUBERNETES-DEPLOYMENT.md reviewed by DevOps Lead
- [ ] SECURITY-RUNBOOK.md reviewed by Security Lead
- [ ] README.md exists with setup instructions
- [ ] Runbook created for common ops tasks

### Database & Migrations
- [ ] All Alembic migrations created and tested locally
- [ ] Rollback migrations tested and verified
- [ ] Indexes exist and are properly named per DATABASE-SCHEMA.md
- [ ] Foreign key constraints verified
- [ ] Data retention policies configured (MySQL event scheduler for cleanup)
- [ ] Backup strategy tested (mysqldump or AWS RDS automated backups)

### Performance & Load Testing
- [ ] Baseline metrics established:
  - API response time: <200ms p95 (without WebSocket)
  - WebSocket latency: <500ms for metric updates
  - Database query time: <100ms p95
  - Sync job duration: <4 minutes for typical team (1M tickets)
  - Dashboard load time: <2 seconds (4 metric tiles)
- [ ] Load test with 100 concurrent users completed
- [ ] Load test with 5M ticket dataset completed
- [ ] Sync job tested with large ticket volumes
- [ ] Memory usage monitored (FastAPI + Celery workers)
- [ ] No memory leaks detected (check WebSocket connection growth)

### Security Review
- [ ] OAuth2 implementation reviewed (state parameter validation, CSRF protection)
- [ ] JWT token validation tested (expiry, signature, claims)
- [ ] Jira API token encryption verified (AES-256)
- [ ] Database credentials not in code or logs
- [ ] HTTPS enforced in staging (TLS 1.2+)
- [ ] CORS policy reviewed and restricted (frontend domain only)
- [ ] Rate limiting configured (1000 req/min per user)
- [ ] SQL injection tests passed (Pydantic validation prevents)
- [ ] XSS protection verified (React default escaping)
- [ ] OWASP Top 10 scan completed (no critical findings)

### Design Compliance
- [ ] All UI components match DESIGN-HANDOFF-Components.md
- [ ] Color tokens match DESIGN-SYSTEM-Guide.md (hex values verified)
- [ ] Typography matches (Inter font, font sizes, line heights)
- [ ] Spacing follows design scale (4px base unit)
- [ ] Responsive behavior tested (desktop 1200px, tablet 768px, mobile <768px)
- [ ] Accessibility audit passed (WCAG AA compliance):
  - [ ] Color contrast ratios ≥4.5:1
  - [ ] Focus rings visible on all interactive elements
  - [ ] Keyboard navigation works (Tab, Enter, Esc)
  - [ ] Screen reader announces all content (aria-labels, aria-live)

---

## Phase 2: Infrastructure Validation (End of Week 10)

**Owner:** DevOps Lead  
**Timeline:** T-14 to T-7 days  
**Success Criteria:** All systems healthy in staging

### Kubernetes Cluster Health
- [ ] Cluster version: ≥1.28 (upgrade if needed)
- [ ] All nodes healthy (`kubectl get nodes` → all Ready)
- [ ] Resource requests set for all deployments (CPU 500m, RAM 512Mi minimum)
- [ ] DNS resolves correctly (CoreDNS, *.default.svc.cluster.local)
- [ ] Network policies configured (restrict traffic between pods if needed)
- [ ] Storage class configured (for MySQL PV)
- [ ] Ingress controller running (nginx-ingress or similar)
- [ ] TLS certificates valid (ingress.tls.crt and key)

### MySQL StatefulSet
- [ ] MySQL pod running and healthy (`kubectl logs mysql-0`)
- [ ] Data persists across pod restarts (PV mounted correctly)
- [ ] Replication working (if HA configured: `SHOW REPLICA STATUS\G`)
- [ ] Binlog enabled for backups (`SHOW BINARY LOGS;`)
- [ ] Character set verified (utf8mb4 for emoji support)
- [ ] Max connections sufficient: `max_connections ≥ 100`
- [ ] Slow query log enabled (>1 second queries logged)
- [ ] Backup tested and restorable (restore to test database, verify data)

### Redis StatefulSet
- [ ] Redis pod running and healthy (`redis-cli ping` → PONG)
- [ ] Persistence enabled (RDB snapshots or AOF)
- [ ] Memory limit set per Redis specs (1Gi minimum)
- [ ] Key eviction policy configured (`maxmemory-policy allkeys-lru`)
- [ ] Replication if HA configured (`redis-cli info replication`)

### FastAPI Deployment
- [ ] Deployment replicas: ≥2 (rolling updates, no downtime)
- [ ] Health check configured (GET /health endpoint)
- [ ] Readiness check working (pod becomes Ready in <30s)
- [ ] Liveness check working (pod restarts if unhealthy)
- [ ] Environment variables set from ConfigMap (database URL, JWT secret, etc.)
- [ ] Secrets mounted correctly (Jira OAuth credentials)
- [ ] Image pulled successfully (check registry, image tags)
- [ ] Logs accessible (`kubectl logs fastapi-0`)

### Celery Workers
- [ ] Celery deployment replicas: ≥2
- [ ] Worker heartbeat healthy (`celery -A tasks inspect active_queues`)
- [ ] Redis connection working (test from pod)
- [ ] Task queue empty (no stuck jobs)
- [ ] Celery Beat scheduler running (5-minute sync enabled)
- [ ] Logs accessible (`kubectl logs celery-worker-0`)

### Frontend (React + Nginx)
- [ ] Frontend pod running and healthy
- [ ] Static assets served correctly (CSS, JS, images load)
- [ ] Environment file built in (API base URL, WebSocket URL)
- [ ] No 404s in console (inspect DevTools)
- [ ] Service load-balancer exposes port 80/443

### Networking & DNS
- [ ] Ingress DNS resolves to load balancer IP
- [ ] TLS certificate valid and not expired (`curl -vI https://your-domain`)
- [ ] CORS headers present in response (`Access-Control-Allow-Origin`)
- [ ] WebSocket upgrade works (test with wscat or browser DevTools)
- [ ] Cross-pod communication working (FastAPI → MySQL, FastAPI → Redis)

---

## Phase 3: Security & Credentials (End of Week 10)

**Owner:** Security Lead  
**Timeline:** T-14 to T-7 days  
**Success Criteria:** Zero security findings

### OAuth2 & JWT
- [ ] Jira OAuth2 app registered (client ID and secret generated)
- [ ] Redirect URI whitelisted in Jira: `https://your-domain/auth/callback`
- [ ] JWT signing key generated and stored in Kubernetes Secret
- [ ] Token lifetime correct: access_token 24h, refresh_token 14d
- [ ] Token validation tested (invalid tokens rejected with 401)
- [ ] Token refresh endpoint tested (refresh_token → new access_token)

### Credential Encryption
- [ ] AES-256 encryption key generated (32 bytes)
- [ ] Encryption key stored in Kubernetes Secret (not in code)
- [ ] Database credentials encrypted before storage:
  - [ ] Jira API tokens encrypted in `credentials.jira_token_encrypted` column
  - [ ] Test: insert, retrieve, decrypt, verify plaintext matches
- [ ] Encryption library used (cryptography.fernet.Fernet or equivalent)
- [ ] No credentials in application logs or error messages

### RBAC & Data Access
- [ ] Role-based access control enforced:
  - [ ] Members: see own team data only
  - [ ] Managers: see all team members' data
  - [ ] Admins: manage users, teams, and access
- [ ] Endpoint authorization tested for each role:
  - [ ] GET /teams/{team_id}/metrics → only manager/admin/team-member
  - [ ] POST /teams → admin only
  - [ ] GET /developers/{dev_id} → only manager/admin/self
- [ ] SQL queries use parameterized statements (SQLAlchemy prevents SQL injection)
- [ ] No direct SQL concatenation in code

### Audit Logging
- [ ] Audit log table created and indexed
- [ ] Events logged:
  - [ ] User login (successful and failed)
  - [ ] Credential creation/rotation
  - [ ] Team/developer access (who viewed what data, when)
  - [ ] Admin actions (user creation, role changes)
- [ ] Audit logs retained for ≥90 days
- [ ] Audit logs readable only by admins and security team
- [ ] Timestamps in UTC (no timezone confusion)

### Network Security
- [ ] Firewall rules:
  - [ ] MySQL port (3306) exposed only to FastAPI pod (not external)
  - [ ] Redis port (6379) exposed only to FastAPI + Celery pods
  - [ ] Ingress port (443) exposed to public internet
  - [ ] SSH/kubectl access restricted to admin IPs
- [ ] Network policies enforced in Kubernetes (`NetworkPolicy` resource)
- [ ] DDoS protection: rate limiting enabled (1000 req/min per user)
- [ ] Certificate validation: client trusts Jira API cert (or custom CA if internal)

---

## Phase 4: Data Preparation (End of Week 11)

**Owner:** Data Engineering + DevOps  
**Timeline:** T-7 to T-5 days  
**Success Criteria:** Historical data loaded, ready for go-live

### Historical Data Load
- [ ] Jira data extraction tested:
  - [ ] Can query Jira API for all projects
  - [ ] Rate limits handled (Jira allows 180 req/min)
  - [ ] Pagination working (load all tickets, not just first 50)
  - [ ] Transition history captured (for bounce detection)
- [ ] Initial load script written (or Celery task):
  - [ ] Fetch all teams' tickets from Jira
  - [ ] Insert into `tickets`, `ticket_transitions` tables
  - [ ] Calculate `cycle_time_days` for resolved tickets
- [ ] Data validation:
  - [ ] Row count matches Jira (`SELECT COUNT(*) FROM tickets` vs Jira API)
  - [ ] Date ranges correct (created_at matches Jira)
  - [ ] Cycle time calculations verified (sample checks: resolved_at - created_at)
  - [ ] No duplicate tickets in database

### Metrics Backfill
- [ ] Pre-calculation script written:
  - [ ] For each day in past 90 days:
    - [ ] SELECT AVG(cycle_time_days) for resolved tickets
    - [ ] SELECT COUNT(*) for bounces (status transitions back + forth)
    - [ ] SELECT status, COUNT(*) for bottleneck detection
  - [ ] INSERT into `metrics` table (team_id, date, avg_cycle_time_days, bounce_rate, etc.)
- [ ] Historical metrics populated for past 90 days
- [ ] Dashboard metrics query tested (retrieves latest metric, not null)

### Jira Integration Testing
- [ ] Test in staging with real Jira sandbox or test instance
- [ ] OAuth2 callback works with Jira (user can login)
- [ ] API token storage works (test create credential, retrieve, decrypt)
- [ ] 5-minute sync job tested:
  - [ ] Celery task runs without errors
  - [ ] Fetches updated tickets from Jira
  - [ ] Inserts/updates database
  - [ ] Broadcast to WebSocket clients (if connected)
- [ ] Large ticket load tested (1M+ tickets)
- [ ] Partial failure recovery tested (API timeout during sync, job retries)

---

## Phase 5: Monitoring & Alerting (End of Week 11)

**Owner:** DevOps + SRE  
**Timeline:** T-7 to T-5 days  
**Success Criteria:** All dashboards and alerts configured

### Prometheus Metrics
- [ ] Prometheus scraped and healthy (`curl localhost:9090/-/healthy`)
- [ ] Metrics collected from:
  - [ ] FastAPI (via Prometheus Python client):
    - `http_requests_total` (labeled by method, endpoint, status)
    - `http_request_duration_seconds` (histogram for latency)
    - `http_requests_in_progress` (gauge)
  - [ ] Celery (via Celery Prometheus exporter):
    - `celery_task_total` (by task name, status)
    - `celery_task_duration_seconds` (histogram)
  - [ ] MySQL (via mysqld_exporter):
    - `mysql_global_status_connections` (active connections)
    - `mysql_innodb_buffer_pool_bytes_free` (memory usage)
  - [ ] Redis (via redis_exporter):
    - `redis_memory_used_bytes`
    - `redis_connected_clients`
    - `redis_keyspace_hits_total`, `redis_keyspace_misses_total` (cache efficiency)
  - [ ] Kubernetes (via kube-state-metrics):
    - Pod resource usage (CPU, memory)
    - Pod restart count

### Grafana Dashboards
- [ ] Infrastructure Dashboard (created):
  - [ ] Kubernetes pod health (running/pending/failed)
  - [ ] CPU and memory usage per pod
  - [ ] Disk space (MySQL, Redis)
  - [ ] Network I/O
- [ ] API Performance Dashboard (created):
  - [ ] Request rate (requests/sec)
  - [ ] Response latency (p50, p95, p99)
  - [ ] Error rate (5xx, 4xx)
  - [ ] Endpoint breakdown (separate graph per endpoint)
  - [ ] WebSocket connections (active count)
- [ ] Business Metrics Dashboard (created):
  - [ ] Sync job duration (minutes)
  - [ ] Sync job success/failure rate
  - [ ] Metrics calculated (latest values: cycle_time, bounce_rate, open_tickets, bottleneck)
  - [ ] User activity (logins, API calls per team)
- [ ] Database Dashboard (created):
  - [ ] Query latency (p95)
  - [ ] Slow query log (queries >1s)
  - [ ] Connection count vs. max_connections
  - [ ] Replication lag (if HA configured)

### Alerting Rules
- [ ] Alert rules written in Prometheus (alert_rules.yml):
  - [ ] API Error Rate: `rate(http_requests_total{status=~"5.."}[5m]) > 0.01` → page on-call
  - [ ] API Latency: `histogram_quantile(0.95, http_request_duration_seconds) > 1` → warn
  - [ ] WebSocket Disconnections: `increase(websocket_disconnects_total[5m]) > 100` → page
  - [ ] Sync Job Failure: `celery_task_failed_total > 0` → alert
  - [ ] Database Slow Query: `mysql_global_status_slow_queries > 10` → warn
  - [ ] MySQL Connection Pool: `mysql_global_status_threads_connected / mysql_global_variables_max_connections > 0.8` → warn
  - [ ] Redis Memory: `redis_memory_used_bytes / redis_memory_max_bytes > 0.85` → page
  - [ ] Pod Restarts: `increase(kube_pod_container_status_restarts_total[15m]) > 0` → alert
- [ ] Alert notification configured (Slack webhook or PagerDuty)

### ELK Stack (Logging)
- [ ] Elasticsearch cluster healthy (`curl localhost:9200/_cluster/health`)
- [ ] Logstash ingests logs from:
  - [ ] FastAPI application logs (stdout/stderr captured via Kubernetes)
  - [ ] Celery worker logs
  - [ ] MySQL slow query log
  - [ ] Kubernetes events
- [ ] Kibana dashboards created:
  - [ ] Application logs searchable (filter by service, timestamp, level)
  - [ ] Error logs highlighted (ERROR, EXCEPTION)
  - [ ] Jira API call logs (request, response, latency)
  - [ ] Database query logs (slow queries)
- [ ] Log retention policy set (≥30 days for application logs, ≥7 days for access logs)

---

## Phase 6: Disaster Recovery (End of Week 11)

**Owner:** DevOps Lead  
**Timeline:** T-7 to T-5 days  
**Success Criteria:** Rollback procedures tested, recovery time <30 min

### Rollback Plan
- [ ] Previous version tagged and available (Docker image tags, git tags)
- [ ] Database rollback tested:
  - [ ] Backup from 24 hours before captured
  - [ ] Restore procedure documented (e.g., `mysql restore < backup.sql`)
  - [ ] Restore time measured (<10 minutes for typical backup)
  - [ ] Data integrity verified post-restore
- [ ] Kubernetes rollback tested:
  - [ ] Old Helm release available (or kubectl rollout undo)
  - [ ] Rollback command: `helm rollback jira-analytics 0` or `kubectl rollout undo deployment/fastapi`
  - [ ] Rollback time measured (<5 minutes)
- [ ] DNS and load balancer verified (old version accessible via same URL)

### Failure Scenarios
- [ ] Database unavailable:
  - [ ] Customers see "Service Temporarily Unavailable" (instead of error)
  - [ ] Request returns 503, not 500
  - [ ] Health check fails, pod restarts
  - [ ] Recovery: restore from backup (automatic or manual trigger)
- [ ] Redis unavailable:
  - [ ] Celery tasks queued but not processed
  - [ ] Metrics not broadcast to WebSocket clients
  - [ ] API continues working (non-real-time)
  - [ ] Recovery: restart Redis pod, Celery processes backlog
- [ ] Jira API unavailable:
  - [ ] Sync job fails and retries (Celery retry 3x with exponential backoff)
  - [ ] Dashboard shows stale metrics (last_synced timestamp notified to user)
  - [ ] No new data, but old data still accessible
  - [ ] Recovery: automatic once Jira recovers
- [ ] Pod crash loop:
  - [ ] Kubernetes auto-restarts (3 restarts, then backoff)
  - [ ] Alerts fire on restart count
  - [ ] Logs examined to identify issue
  - [ ] Fix deployed and pod healthy

### Recovery Time Targets (RTO)
- [ ] Database backup/restore: <15 minutes
- [ ] Kubernetes rollback: <5 minutes
- [ ] Jira API reconnect: <10 minutes (automatic)
- [ ] Full rollback to previous version: <20 minutes

---

## Phase 7: Pre-Launch UAT (End of Week 12)

**Owner:** QA Lead + Product Manager  
**Timeline:** T-5 to T-2 days  
**Success Criteria:** UAT sign-off from Product Manager, zero critical bugs

### Functional Testing (Test Plan)
- [ ] **Dashboard View:**
  - [ ] Metrics tiles display (cycle_time, bounce_rate, open_tickets, bottleneck)
  - [ ] Metrics update every 5 minutes (WebSocket refresh)
  - [ ] Click metric tile → drill-down view shows details
  - [ ] Team selector works (dropdown, switch between teams)
  - [ ] Metrics show correct values (manually verify against Jira)
  - [ ] Last synced timestamp displayed and accurate
  - [ ] No data from other teams visible (data isolation verified)

- [ ] **Table View:**
  - [ ] All tickets displayed (paginated, 100 per page)
  - [ ] Sorting works (click column header, ascending/descending)
  - [ ] Filtering works (status, assignee dropdowns)
  - [ ] Ticket key, title, assignee, status, days_in_status visible
  - [ ] Developer name clickable → opens developer detail modal
  - [ ] Pagination controls work (next, prev, skip to page)

- [ ] **Kanban Board:**
  - [ ] 4 columns: To Do, In Progress, QA, Done
  - [ ] Cards drag-drop between columns (optional: if implemented)
  - [ ] Card shows jira_key, title, assignee
  - [ ] Click card → detail modal or external Jira link

- [ ] **Developer Detail Modal:**
  - [ ] Shows dev name, email, role
  - [ ] Displays metrics: avg_cycle_time, completed_tickets, bounce_count, current_tickets
  - [ ] Recent tickets listed (last 5)
  - [ ] Close modal (X button, ESC key)

- [ ] **Authentication:**
  - [ ] Login via Jira (OAuth2 button)
  - [ ] Redirect to Jira consent screen
  - [ ] Return from Jira → user logged in, JWT set
  - [ ] Invalid Jira response → error shown, user not logged in
  - [ ] Logout → JWT cleared, redirected to login page
  - [ ] Token expiry: user logged out after 24 hours (verify with time-travel or manual wait)

- [ ] **Real-Time Updates:**
  - [ ] Modify ticket in Jira (change status)
  - [ ] Dashboard metric updates within 5 seconds (verify WebSocket ping)
  - [ ] No manual refresh needed
  - [ ] Browser DevTools → Network tab → WebSocket frames visible

### Performance Testing
- [ ] Dashboard load time: <2 seconds (measure with Lighthouse)
- [ ] Table view load (100 tickets): <1 second
- [ ] Developer detail modal: <500ms
- [ ] WebSocket update: <500ms latency (server → browser)
- [ ] No memory leaks: leave page open for 10 minutes, memory stable

### Accessibility Testing
- [ ] Keyboard navigation: Tab through all buttons, links, form fields
- [ ] Screen reader (NVDA or JAWS):
  - [ ] Page title announced
  - [ ] Metric tiles announced with aria-label (e.g., "Cycle Time metric, 18 point 5 days")
  - [ ] Focus ring visible on all interactive elements
  - [ ] Link text meaningful (not "click here")
- [ ] Color contrast: all text ≥4.5:1 (use axe DevTools browser extension)
- [ ] WCAG AA compliance verified (no errors in axe scan)

### Negative Testing (Boundary Cases)
- [ ] Large dataset: view 5M tickets (table loads, no hang)
- [ ] Empty state: team with no tickets (friendly message shown)
- [ ] Jira API error: return 500 from Jira (sync job retries, user sees stale data)
- [ ] Network disconnect: close browser network → WebSocket reconnects automatically
- [ ] Missing data: ticket without assignee (UI doesn't crash, shows "Unassigned")
- [ ] Concurrent users: 50 simultaneous users (no errors, performance acceptable)

### Browser/Device Compatibility
- [ ] Desktop (1920x1080): Chrome, Firefox, Safari, Edge latest versions
- [ ] Tablet (768x1024): iPad or Android tablet, portrait/landscape
- [ ] Mobile (375x667): iPhone or Android phone
- [ ] Dark mode: application readable in dark mode (if supported)

### UAT Sign-Off
- [ ] Product Manager tests all features and signs off
- [ ] No critical bugs remaining (P1 issues resolved)
- [ ] Non-critical bugs logged for post-launch (P2, P3)
- [ ] Performance acceptable (no complaints about slowness)
- [ ] Accessibility compliant per WCAG AA

---

## Phase 8: Monitoring Baseline (T-2 days)

**Owner:** DevOps + SRE  
**Timeline:** Immediately before go-live  
**Success Criteria:** Baseline metrics recorded, alert thresholds tuned

### Establish Baseline Metrics
- [ ] API latency p50/p95/p99 recorded (from staging load test):
  - [ ] GET /teams: p95 <50ms
  - [ ] GET /teams/{id}/metrics: p95 <100ms
  - [ ] GET /teams/{id}/tickets: p95 <200ms
  - [ ] GET /developers/{id}: p95 <100ms
- [ ] Error rate baseline: <0.1% (goal)
- [ ] WebSocket connection count: expected X concurrent users
- [ ] Sync job duration: average Y minutes (from test runs)
- [ ] Database query latency: p95 <100ms
- [ ] CPU/memory usage per pod recorded

### Alert Thresholds (Tuned)
- [ ] Critical (page on-call):
  - [ ] API error rate >1% for 5 minutes
  - [ ] API latency p95 >1000ms
  - [ ] WebSocket connection drop >50% in 2 minutes
  - [ ] Sync job failure 3x in a row
  - [ ] MySQL lag >5 minutes (replication)
- [ ] Warning (Slack notification):
  - [ ] API error rate >0.5% for 5 minutes
  - [ ] API latency p95 >500ms
  - [ ] Pod restart count >0 in 15 minutes
  - [ ] Database slow query count >10 in 5 minutes

---

## Phase 9: Go-Live Preparation (T-1 day)

**Owner:** Release Manager  
**Timeline:** 24 hours before launch  
**Success Criteria:** All teams briefed, rollback ready, communication plan confirmed

### Final Checks
- [ ] All pending PRs merged or deferred (no half-finished code)
- [ ] All tests passing in CI/CD (green checkmarks)
- [ ] Load balancer/DNS configured correctly (test URL in browser)
- [ ] SSL/TLS certificate valid and not expired
- [ ] Secrets/credentials verified in Kubernetes (no missing env vars)
- [ ] Database backups current (within 1 hour)
- [ ] On-call engineer available (check PagerDuty, Slack status)

### Team Briefing
- [ ] Engineering team briefed on deployment plan:
  - [ ] Deployment window: T to T+15 minutes
  - [ ] Canary rollout: 5% → 25% → 100% (2 min each)
  - [ ] Rollback trigger: error rate >1% → immediate rollback
  - [ ] On-call during rollout (no context switching)
- [ ] Product team briefed:
  - [ ] Launch time and expected downtime (none for canary)
  - [ ] Monitor for complaints (Slack channel)
  - [ ] Link to dashboard for real-time metrics
- [ ] Customer support briefed:
  - [ ] Known issues (if any)
  - [ ] Escalation contact (engineering on-call)
  - [ ] Frequently asked questions
- [ ] Executive team (optional):
  - [ ] Launch status: on-track
  - [ ] Key metrics to watch
  - [ ] Contingency plan (rollback)

### Communication Plan
- [ ] T-2h: "Launching in 2 hours" (Slack, internal)
- [ ] T-30m: "Starting deployment, may see temporary service interruptions" (public status page or not if canary)
- [ ] T-0: Deployment starts, on-call monitor begins
- [ ] T+5m: "Canary deployment 5% of traffic" (internal Slack)
- [ ] T+10m: "Canary deployment 25% of traffic" (internal Slack)
- [ ] T+15m: "Full production deployment, monitoring" (internal Slack)
- [ ] T+30m: "All metrics nominal, deployment complete" (public status, Slack)
- [ ] T+2h: "Post-deployment validation passed, launch successful" (all teams)

### Rollback Ready
- [ ] Rollback command tested in staging: `helm rollback jira-analytics 0` or equivalent
- [ ] On-call engineer knows rollback procedure by heart (or has printed runbook)
- [ ] Previous version (N-1) Docker image available and healthy
- [ ] Database backup available (within 1 hour of launch)

---

## Phase 10: Go-Live Deployment (T day)

**Owner:** Release Manager + On-Call Engineer  
**Timeline:** T to T+30 minutes  
**Success Criteria:** Full deployment, metrics nominal, zero critical incidents

### Canary Deployment (Gradual Rollout)
- [ ] **T+0 min:** Start canary (5% of traffic)
  - [ ] Deploy new FastAPI image (1 pod initially)
  - [ ] Ingress load balancer weight: 5% new, 95% old
  - [ ] Health checks pass (pod Ready)
  - [ ] Dashboard error rate monitored (should be <0.1%)
- [ ] **T+2 to T+7 min:** Monitor canary (watch for errors)
  - [ ] Error rate >1%? Rollback immediately
  - [ ] Latency >500ms? Investigate, rollback if sustained
  - [ ] WebSocket disconnections? Rollback
  - [ ] No issues? Proceed to next stage
- [ ] **T+7 min:** Expand to 25% (2 pods)
  - [ ] Deploy second FastAPI pod
  - [ ] Load balancer weight: 25% new, 75% old
  - [ ] Monitor again for 5 minutes
- [ ] **T+12 to T+17 min:** Monitor expanded canary
  - [ ] Same checks as before
  - [ ] Celery sync job completed? Check logs
  - [ ] Database queries responding? Spot-check latency
  - [ ] WebSocket connections stable? Check connection count
  - [ ] No issues? Proceed to full deployment
- [ ] **T+17 min:** Full deployment (100%)
  - [ ] Deploy remaining FastAPI pods (scale to 3)
  - [ ] Load balancer weight: 100% new, 0% old
  - [ ] Health checks pass
  - [ ] Smoke tests run automatically (in CI/CD or manually)

### Smoke Tests (Automated or Manual)
- [ ] API /health endpoint returns 200
- [ ] POST /auth/jira returns auth_url (not an error)
- [ ] GET /teams (authenticated) returns 200 + team list
- [ ] GET /teams/{id}/metrics returns metrics (not null)
- [ ] WebSocket /ws/metrics/{id} connects (test with wscat or curl)
- [ ] Celery sync job runs and completes within 4 minutes

### Real-Time Monitoring (T+5 to T+30 min)
- [ ] Grafana dashboards open (Infrastructure, API, Business, Database)
- [ ] Metrics checked every 2 minutes:
  - [ ] Error rate: <0.1% (critical if >1%)
  - [ ] Latency p95: <500ms (critical if >1000ms)
  - [ ] WebSocket connections: stable (critical if >50% drop)
  - [ ] Sync job: completed without error
  - [ ] Pod CPU: <500m per pod
  - [ ] Pod memory: <512Mi per pod
  - [ ] Database connections: <50 (not hitting limit)
  - [ ] MySQL replication lag: <1 minute

### Incident Response (If Issues Arise)
- [ ] Error rate >1%?
  - [ ] Check logs: `kubectl logs fastapi-0 | tail -50`
  - [ ] Identify root cause (code, config, infra)
  - [ ] If unfixable in <5 min: rollback immediately
  - [ ] Notify team in Slack (issue, impact, resolution)
- [ ] Latency spike >1000ms?
  - [ ] Check database slow query log: `SHOW ENGINE INNODB STATUS;`
  - [ ] Check Redis memory: `redis-cli info memory`
  - [ ] If sustained: investigate further or rollback
- [ ] WebSocket disconnections?
  - [ ] Check Pod logs for "connection reset" errors
  - [ ] Check Redis for dropped connections
  - [ ] Restart Redis if needed, monitor recovery

### Post-Deployment Validation
- [ ] All checks passed (metrics nominal)
- [ ] No alerts firing (false positives checked)
- [ ] User testing: PMs test critical flows in production
  - [ ] Login → view dashboard → metrics display
  - [ ] Click metric tile → drill-down detail
  - [ ] Switch teams → data changes
  - [ ] Real-time update → refresh without page reload
- [ ] Performance verified: dashboard <2 second load time
- [ ] Data integrity verified: sample ticket counts match Jira

---

## Phase 11: Post-Deployment Validation (T+2 to T+4 hours)

**Owner:** QA + Product  
**Timeline:** 4-hour window after full deployment  
**Success Criteria:** All validations pass, launch considered successful

### Functionality Verification
- [ ] All user flows tested in production:
  - [ ] Login (OAuth2 → JWT)
  - [ ] Dashboard (4 metrics visible, correct values)
  - [ ] Table view (sort, filter, paginate)
  - [ ] Developer drill-down (modal opens, data correct)
  - [ ] Kanban board (if implemented)
  - [ ] Real-time updates (edit ticket in Jira, see update in dashboard)
- [ ] No broken links or 404s
- [ ] Error messages user-friendly (not stack traces)
- [ ] No XSS or SQL injection vulnerabilities in user input (spot checks)

### Performance Validation (4-Hour Baseline)
- [ ] Dashboard load: average <2 seconds (check Lighthouse)
- [ ] API response: p95 <200ms (check Grafana)
- [ ] WebSocket latency: <500ms for updates (check browser DevTools)
- [ ] Sync job: completed 3x in 4 hours (every 5 min), all successful
- [ ] Pod CPU: stable <400m (no runaway threads)
- [ ] Pod memory: stable <400Mi (no memory leak)
- [ ] Database query latency: p95 <100ms
- [ ] No slow queries logged (>1 second)

### Data Integrity Validation
- [ ] Row counts match:
  - [ ] `SELECT COUNT(*) FROM users` vs. team roster
  - [ ] `SELECT COUNT(*) FROM tickets` vs. Jira project (allow small variance for time sync)
  - [ ] Cycle time calculations spot-checked (sample 10 tickets, verify math)
- [ ] No orphaned records (ticket with no team_id, user with no team)
- [ ] No duplicate tickets in database
- [ ] Metrics calculated correctly:
  - [ ] Bounce rate = bounced_count / total_completed (sample check)
  - [ ] Bottleneck = status with max avg(days_in_status) (verify logic)

### User Acceptance
- [ ] Product Manager confirms launch success (email or Slack)
- [ ] No critical bugs reported by early users (monitor support channel)
- [ ] User feedback on features (optional: survey or 1:1 calls)
- [ ] Team celebration (acknowledge launch milestone)

---

## Phase 12: Stabilization (T+7 days)

**Owner:** DevOps + On-Call Rotation  
**Timeline:** Week 1 post-launch  
**Success Criteria:** System stable, incident-free, runbook effective

### Daily Monitoring (T+1 to T+7 days)
- [ ] Daily metrics check (same metrics as Phase 11)
- [ ] No critical incidents (page response <30 min)
- [ ] No recurring errors (pattern-based alerts)
- [ ] Sync job success rate: ≥95% (1 failure acceptable in 7 days)
- [ ] User complaints: <5 per day (target for mature products)

### Incident Logging
- [ ] Any incident (even minor) documented:
  - [ ] Time and duration
  - [ ] Impact (users affected, data affected)
  - [ ] Root cause identified
  - [ ] Resolution and time-to-recovery
  - [ ] Preventive actions (code fix, monitoring, runbook)
- [ ] Post-mortems scheduled for critical incidents (P1)

### Runbook Validation
- [ ] All runbook procedures tested by on-call:
  - [ ] Restart procedure (if MySQL hangs)
  - [ ] Rollback procedure (if deployment needed)
  - [ ] Database recovery (from backup)
  - [ ] Escalation contacts (who to page for what)
- [ ] Feedback on runbook: are steps clear? Any missing steps?

### Known Issues & Backlog
- [ ] P2/P3 bugs from UAT logged in tracking system (Jira, Linear, etc.)
- [ ] Feature requests collected from user feedback
- [ ] Documentation updated (ARCHITECTURE.md, runbooks, etc.)
- [ ] Next sprint planned based on feedback

---

## Success Criteria Summary

| Metric | Target | Owner |
|--------|--------|-------|
| **Pre-Deploy** | All tests passing, zero critical bugs | Engineering Lead |
| **Infrastructure** | All systems healthy, zero connectivity issues | DevOps Lead |
| **Security** | Zero critical findings, OAuth2 verified | Security Lead |
| **Monitoring** | Dashboards live, alerts configured, baseline established | DevOps + SRE |
| **Deployment** | Canary 5%→25%→100%, error rate <1%, latency <500ms | Release Manager |
| **Post-Deploy** | All flows work, data integrity verified, UAT signed off | QA + Product |
| **Stabilization** | 7 days incident-free, runbook effective, backlog captured | On-Call Team |

---

## Rollback Criteria

**Immediate Rollback (No Discussion) If:**
- API error rate >1% for 5 consecutive minutes
- API latency p95 >1000ms for 10 consecutive minutes
- WebSocket connections drop >50% in 2 minutes (indicates widespread disconnections)
- Critical business logic broken (e.g., metrics showing wrong data)
- Data loss detected (e.g., missing tickets post-sync)

**Investigation Before Rollback (10 min max) If:**
- API error rate 0.5%-1% (investigate root cause)
- Sporadic errors in logs (not systematic)
- User complaints but metrics look good

**No Rollback If:**
- Minor UI issues (cosmetic)
- Non-critical features unavailable
- Performance slightly degraded but acceptable

---

## Sign-Off Matrix

| Role | Responsibility | Sign-Off Required |
|------|---|---|
| **Release Manager** | Deployment coordination, timeline | ✅ Yes (launch approval) |
| **Engineering Lead** | Code quality, testing, no blockers | ✅ Yes (technical go/no-go) |
| **DevOps Lead** | Infrastructure health, deployment safety | ✅ Yes (deployment execution) |
| **Product Manager** | Feature completeness, UAT | ✅ Yes (product go/no-go) |
| **Security Lead** | Security review, OAuth2 verified | ✅ Yes (security go/no-go) |
| **QA Lead** | Testing coverage, critical bugs zero | ✅ Yes (QA go/no-go) |
| **On-Call Engineer** | Incident response ready | ✅ Acknowledge (runbook reviewed) |

**Launch Decision:** All 6 sign-offs required (Engineering, DevOps, Product, Security, QA, Release). Default: Launch blocked until all sign-offs received.

---

## Communication Timeline

| Time | Audience | Message | Channel |
|------|----------|---------|---------|
| **T-7d** | Internal | Soft launch reminder, team briefing | Email + Slack |
| **T-2d** | Internal | Final checklist, on-call assigned | Slack |
| **T-1d** | All teams | Launch window confirmed, rollback plan | Email |
| **T-2h** | Internal | "Launching in 2 hours" | Slack |
| **T-30m** | Internal + Status Page | "Deployment in progress" | Slack + status page |
| **T+0** | Engineering | Deployment started, canary 5% | Slack (internal channel) |
| **T+7m** | Engineering | Canary 25% | Slack (internal channel) |
| **T+17m** | Engineering | Full deployment 100% | Slack (internal channel) |
| **T+30m** | Status Page | "Launch complete, nominal metrics" | Status page + Twitter/blog |
| **T+4h** | Product + Execs | "Validation passed, launch successful" | Email + Slack |
| **T+7d** | All | Retrospective summary, feedback | Email + wiki |

---

## Appendices

### Appendix A: Escalation Contacts

| Severity | Primary | Secondary | Tertiary |
|----------|---------|-----------|----------|
| P1 (Critical) | On-Call Engineer | Engineering Lead | CTO |
| P2 (High) | DevOps On-Call | SRE | Engineering Lead |
| P3 (Medium) | Slack #incidents | Assigned Engineer | — |
| P4 (Low) | Backlog | — | — |

### Appendix B: Environment Checklist

**Staging (Pre-Launch):**
- [ ] All PRs merged, no branches pending
- [ ] Docker image tagged: `jira-analytics:v1.0.0`
- [ ] Kubernetes secrets applied (OAuth, database, JWT keys)
- [ ] MySQL backup taken
- [ ] Monitoring dashboards created

**Production (Go-Live):**
- [ ] Docker image pulled and running
- [ ] All pods healthy (Ready state)
- [ ] Database replicated (if HA)
- [ ] DNS pointing to new load balancer
- [ ] SSL certificates installed (not expired)
- [ ] Backups scheduled and tested

---

**Version:** 1.0  
**Last Updated:** 2026-05-16  
**Status:** Ready for Implementation  
**Approved By:** [To be signed during deployment]
