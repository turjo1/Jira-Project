# Backend API Reference: Jira Team Performance Analytics

**Status:** Implementation Ready  
**Version:** 1.0  
**Tech Stack:** Python FastAPI + Pydantic  
**Last Updated:** 2026-05-16

---

## Overview

Complete REST API and WebSocket specification for the backend service. All endpoints require JWT authentication via Jira OAuth2.

**Base URL:** `https://api.example.com/v1`

---

## Authentication: JWT + Jira OAuth2

### OAuth2 Login Flow
```
1. GET /auth/jira → Returns auth_url
2. User redirects to Jira OAuth2 consent
3. Jira redirects back with code → POST /auth/callback
4. Server exchanges code for token, returns JWT
```

### Using JWT
```bash
curl -H "Authorization: Bearer <jwt_token>" \
     https://api.example.com/v1/teams
```

**Token Lifetime:** 24 hours (refresh token: 14 days)

---

## Core Endpoints

### Authentication (Public)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/jira` | Start OAuth2 flow |
| POST | `/auth/callback` | Handle OAuth2 callback |
| POST | `/auth/logout` | Clear tokens |

### Teams (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/teams` | List user's teams |
| GET | `/teams/{team_id}` | Get team details |

### Metrics (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/teams/{team_id}/metrics` | Dashboard KPIs |

### Tickets (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/teams/{team_id}/tickets` | Paginated tickets (sortable, filterable) |

### Developers (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/developers/{dev_id}` | Developer performance stats |

### WebSocket (Authenticated)

| Protocol | Path | Description |
|----------|------|-------------|
| WS | `/ws/metrics/{team_id}` | Real-time metric updates |

---

## Endpoint Details

### POST /auth/jira
Initiate Jira OAuth2 login.

**Response:**
```json
{
  "auth_url": "https://auth.atlassian.com/authorize?...",
  "state": "random_string"
}
```

---

### POST /auth/callback
Handle OAuth2 redirect from Jira.

**Query Parameters:**
- `code` — Authorization code from Jira
- `state` — State parameter for verification

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "user123",
    "email": "user@company.com",
    "team_id": "team456"
  }
}
```

**Sets Cookies:**
- `jwt` — Bearer token (24h)
- `refresh` — Refresh token (14d)

---

### GET /teams
List teams authenticated user manages.

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 50, max: 100)

**Response:**
```json
{
  "teams": [
    {
      "id": "team123",
      "name": "Platform Team",
      "jira_project_key": "PLAT",
      "member_count": 8,
      "manager": {
        "id": "user456",
        "name": "Manager Name"
      }
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 50
}
```

---

### GET /teams/{team_id}/metrics
Get 4 dashboard metrics for a team.

**Response:**
```json
{
  "team_id": "team123",
  "metrics": {
    "cycle_time": {
      "value": 8.5,
      "unit": "days",
      "status": "success",
      "trend": {
        "direction": "up",
        "percent": 5
      }
    },
    "bounce_rate": {
      "value": 12,
      "unit": "percent",
      "status": "warning"
    },
    "open_tickets": {
      "value": 24,
      "unit": "tickets",
      "status": "success"
    },
    "bottleneck": {
      "value": "QA",
      "avg_days": 3.2
    }
  },
  "last_synced_at": "2026-05-16T14:30:00Z"
}
```

---

### GET /teams/{team_id}/tickets
Get team's tickets with filtering and sorting.

**Query Parameters:**
- `status` — Filter by status (To Do, In Progress, QA, Done)
- `assignee_id` — Filter by developer
- `sort_by` — Column to sort by (key, title, assignee, status, days_in_status)
- `sort_order` — asc or desc
- `skip` (default: 0)
- `limit` (default: 100, max: 500)

**Example:**
```
GET /teams/team123/tickets?status=QA&sort_by=days_in_status&sort_order=desc
```

**Response:**
```json
{
  "tickets": [
    {
      "jira_key": "PLAT-456",
      "title": "Fix auth bug",
      "assignee": {
        "id": "user789",
        "name": "Developer Name"
      },
      "status": "QA",
      "created_at": "2026-05-10T08:00:00Z",
      "days_in_status": 3.5,
      "cycle_time_days": 5.2,
      "bounced": 1
    }
  ],
  "total": 24,
  "skip": 0,
  "limit": 100
}
```

---

### GET /developers/{dev_id}
Get individual developer's performance stats.

**Response:**
```json
{
  "id": "user789",
  "name": "Developer Name",
  "email": "dev@company.com",
  "metrics": {
    "avg_cycle_time_days": 7.3,
    "completed_tickets": 45,
    "bounce_count": 3,
    "current_tickets": 2
  },
  "recent_tickets": [
    {
      "jira_key": "PLAT-456",
      "title": "Fix auth bug",
      "status": "QA",
      "cycle_time_days": 5.2
    }
  ]
}
```

---

### WS /ws/metrics/{team_id}
Real-time metric updates via WebSocket.

**Subscribe:**
```json
{
  "type": "subscribe",
  "team_id": "team123"
}
```

**Metric Update (server-sent, every 5 min):**
```json
{
  "type": "metrics_update",
  "timestamp": "2026-05-16T14:35:00Z",
  "metrics": {
    "cycle_time": 8.5,
    "bounce_rate": 12,
    "open_tickets": 24,
    "bottleneck": "QA"
  }
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "sort_by parameter invalid",
    "details": {
      "field": "sort_by",
      "value": "invalid",
      "valid_values": ["key", "title", "assignee"]
    }
  }
}
```

### HTTP Status Codes
- `200` — Success
- `400` — Bad request (validation error)
- `401` — Unauthorized (missing/invalid JWT)
- `403` — Forbidden (not allowed to access)
- `404` — Not found
- `429` — Rate limited
- `500` — Server error

---

## Rate Limiting

**Limit:** 1000 requests/minute per user

**Headers:**
- `X-RateLimit-Limit: 1000`
- `X-RateLimit-Remaining: 999`
- `X-RateLimit-Reset: 1716100030`

**Exceeded:** Returns 429 with `Retry-After` header

---

## Pagination

All list endpoints paginate results.

**Query Params:**
- `skip` (default: 0)
- `limit` (default: 50, max varies by endpoint)

**Response:**
```json
{
  "items": [...],
  "total": 350,
  "skip": 50,
  "limit": 100,
  "pages": 4,
  "current_page": 1
}
```

---

## Implementation Checklist

- [ ] FastAPI app with async support
- [ ] Pydantic models for all endpoints
- [ ] JWT token generation/validation
- [ ] Jira OAuth2 integration
- [ ] SQLAlchemy ORM queries
- [ ] WebSocket manager
- [ ] Rate limiting middleware
- [ ] CORS configuration
- [ ] Error handling/logging
- [ ] Request validation
- [ ] Unit tests
- [ ] Integration tests

---

**See also:** ARCHITECTURE.md, DATABASE-SCHEMA.md, SECURITY-RUNBOOK.md
