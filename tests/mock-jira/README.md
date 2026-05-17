# Mock Jira API Server

Fake Jira API server for testing authentication, syncing, and error scenarios without hitting the real Jira instance.

## Features

- **OAuth2 token endpoint** — exchange authorization codes for JWT tokens
- **Issue search endpoint** — JQL queries with pagination (100 fake issues per team)
- **Issue changelog endpoint** — status transition history for bounce rate calculation
- **Error injection** — simulate rate limits (429), server errors (500), and invalid codes (401)
- **Admin endpoints** — reset state, enable/disable error scenarios for testing

## Running Locally

### Option 1: Docker Compose

```bash
cd tests/mock-jira
docker-compose up
```

Server runs on `http://localhost:8001`

### Option 2: Direct Python

```bash
cd tests/mock-jira
pip install -r requirements.txt
python -m mock_jira.server
```

Server runs on `http://localhost:8001`

### Option 3: In-Memory for Tests

```python
import pytest
from httpx import ASGITransport, AsyncClient
from mock_jira.server import app as mock_jira_app

@pytest_asyncio.fixture
async def mock_jira():
    transport = ASGITransport(app=mock_jira_app)
    async with AsyncClient(transport=transport, base_url="http://mock-jira") as client:
        yield client

async def test_oauth_token(mock_jira):
    response = await mock_jira.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "test-auth-code",
            "client_id": "test-client",
            "client_secret": "test-secret",
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## API Endpoints

### OAuth2

#### `POST /oauth/token`

Exchange authorization code for access token.

**Request:**
```json
{
  "grant_type": "authorization_code",
  "code": "test-auth-code",
  "client_id": "test-client-id",
  "client_secret": "test-client-secret",
  "redirect_uri": "http://localhost:8000/auth/callback"
}
```

**Response:**
```json
{
  "access_token": "jira-token-test-auth-code-test-client-id",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh-jira-token-..."
}
```

**Error Injection:**
- Use `code="INVALID_CODE"` to trigger 401 Unauthorized
- Use `code="RATE_LIMITED"` to trigger 429 Rate Limit
- Use `code="SERVER_ERROR"` to trigger 500 Server Error
- Or enable via admin endpoint: `POST /admin/error/RATE_LIMIT`

---

#### `GET /oauth/authorize/accessible-resources`

Get list of Jira instances accessible with token.

**Headers:**
```
Authorization: Bearer jira-access-token
```

**Response:**
```json
[
  {
    "id": "jira-cloud-id",
    "url": "https://my-jira.atlassian.net",
    "name": "My Jira Cloud",
    "scopes": ["read:me", "read:jira-work"],
    "avatarUrl": "https://..."
  }
]
```

---

#### `GET /oauth/authorize/user-profile`

Get authenticated user profile.

**Headers:**
```
Authorization: Bearer jira-access-token
```

**Response:**
```json
{
  "accountId": "jira-user-123",
  "emailAddress": "user@example.com",
  "displayName": "Test User",
  "active": true,
  "timeZone": "UTC"
}
```

---

### Issues

#### `GET /rest/api/3/issues/search`

Search for issues using JQL.

**Query Parameters:**
- `jql` — JQL query (e.g., `assignee=user-123 AND status!=Done`)
- `startAt` — pagination start (default: 0)
- `maxResults` — max results (default: 50)

**Response:**
```json
{
  "startAt": 0,
  "maxResults": 50,
  "total": 100,
  "issues": [
    {
      "key": "TEST-1",
      "id": "jira-issue-id-1",
      "fields": {
        "summary": "Test Issue 1",
        "status": {
          "id": "10000",
          "name": "Open"
        },
        "assignee": {
          "accountId": "jira-user-123",
          "displayName": "Test User",
          "emailAddress": "testuser@example.com"
        },
        "created": "2026-01-01T00:00:00.000Z",
        "updated": "2026-05-17T12:00:00.000Z"
      }
    }
  ]
}
```

---

#### `GET /rest/api/3/issues/{issue_key}/changelog`

Get status transition history (bounce detection).

**Path Parameters:**
- `issue_key` — issue key (e.g., `TEST-1`)

**Query Parameters:**
- `startAt` — pagination start
- `maxResults` — max results

**Response:**
```json
{
  "startAt": 0,
  "maxResults": 50,
  "total": 3,
  "histories": [
    {
      "id": "1",
      "created": "2026-01-01T00:00:00.000Z",
      "items": [
        {
          "field": "status",
          "fromString": "Open",
          "toString": "In Progress"
        }
      ]
    }
  ]
}
```

---

### Admin (Test Control)

#### `POST /admin/reset`

Reset all server state (clear tokens, errors, cache).

#### `POST /admin/error/{error_type}`

Enable error scenario: `RATE_LIMIT`, `SERVER_ERROR`, etc.

#### `DELETE /admin/error/{error_type}`

Disable error scenario.

#### `DELETE /admin/errors`

Clear all error scenarios.

#### `POST /admin/token`

Add a valid token for testing.

**Request:**
```json
{
  "token": "custom-token-123"
}
```

---

## Testing Backend Auth Flow

### 1. Test OAuth token exchange

```python
async def test_oauth_exchange(mock_jira):
    response = await mock_jira.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "test-auth-code",
            "client_id": "test-client",
            "client_secret": "test-secret",
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token.startswith("jira-token-")
```

### 2. Test accessible resources

```python
async def test_accessible_resources(mock_jira, app_client):
    # Get token first
    token_response = await mock_jira.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "test-auth-code",
            "client_id": "test-client",
            "client_secret": "test-secret",
        }
    )
    token = token_response.json()["access_token"]

    # Get accessible resources
    response = await mock_jira.get(
        "/oauth/authorize/accessible-resources",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    resources = response.json()
    assert len(resources) > 0
```

### 3. Test issue sync with error injection

```python
async def test_sync_with_rate_limit(mock_jira):
    # Enable rate limit
    await mock_jira.post("/admin/error/RATE_LIMIT")

    # Try to search issues — should get 429
    response = await mock_jira.get(
        "/rest/api/3/issues/search",
        params={"jql": "PROJECT=TEST"}
    )
    assert response.status_code == 429

    # Clear errors
    await mock_jira.delete("/admin/errors")

    # Now it works
    response = await mock_jira.get(
        "/rest/api/3/issues/search",
        params={"jql": "PROJECT=TEST"}
    )
    assert response.status_code == 200
```

## Integration with Backend Tests

### Configuration

Set `JIRA_API_URL` environment variable to point to mock server:

```bash
export JIRA_API_URL=http://localhost:8001
pytest tests/test_auth.py -v
```

Or in `pytest.ini`:

```ini
[pytest]
env =
    JIRA_API_URL=http://localhost:8001
```

### Backend Service Configuration

Update `app.core.config.py` to use mock Jira for testing:

```python
if settings.environment == "test":
    settings.jira_oauth_token_url = "http://localhost:8001/oauth/token"
    settings.jira_accessible_resources_url = "http://localhost:8001/oauth/authorize/accessible-resources"
```

## Test Scenarios

### Scenario 1: Happy Path OAuth

```python
async def test_full_oauth_flow(app_client, mock_jira):
    # 1. User initiates login (calls /auth/jira)
    response = await app_client.get("/auth/jira")
    assert response.status_code == 302
    
    # 2. User gets redirected to Jira, authorizes, Jira redirects back with code
    # Simulate: /auth/callback?code=test-auth-code&state=xxx
    response = await app_client.get(
        "/auth/callback",
        params={"code": "test-auth-code", "state": "test-state"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Scenario 2: Rate Limit During Sync

```python
async def test_sync_backoff_on_rate_limit(app_client, mock_jira):
    # Enable rate limit on Jira
    await mock_jira.post("/admin/error/RATE_LIMIT")
    
    # Sync should handle 429 gracefully
    response = await app_client.post("/api/sync/jira")
    assert response.status_code in [202, 503]  # Accepted or retry-after
```

### Scenario 3: Bounce Rate Calculation

```python
async def test_bounce_rate_from_changelog(seeded_transitions):
    # Check that bounces (Done -> In Progress) are detected
    bounces = [t for t in seeded_transitions if t.from_status == "Done"]
    assert len(bounces) > 0  # At least some bounces in dataset
```

## Troubleshooting

- **Port 8001 already in use:** Kill the process or change port
  ```bash
  lsof -i :8001
  kill -9 <PID>
  ```

- **Module not found errors:** Install requirements
  ```bash
  pip install -r tests/mock-jira/requirements.txt
  ```

- **Tests timeout:** Increase timeout or check if mock server is running
  ```bash
  curl http://localhost:8001/health
  ```

## Next Steps

- Integrate mock Jira into CI/CD pipeline (docker-compose up for tests)
- Add fixture data for specific test scenarios
- Extend mock server with additional endpoints as needed
