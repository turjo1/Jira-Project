# Backend — Jira Team Performance Analytics

FastAPI + SQLAlchemy 2.0 (async) + Celery + Redis + MySQL 8.

## Local

```bash
cp .env.example .env
docker-compose up --build
```

- API: http://localhost:8000
- Health: `/health` `/ready` `/live`
- Prometheus: `/metrics`
- OpenAPI: `/docs`

## Tests

```bash
pip install -r requirements.txt
pytest
```

Coverage gate: 80% on `app/`.

## Layout

```
app/
  core/        # config, logging, metrics, middleware
  models/      # SQLAlchemy ORM + Pydantic schemas
  routers/     # FastAPI endpoints
  services/    # Jira client, auth, metric calc
  websocket/   # ConnectionManager + handlers
  tasks/       # Celery sync jobs
alembic/       # migrations
tests/
```

See `../ARCHITECTURE.md`, `../BACKEND-API.md`, `../DATABASE-SCHEMA.md`.
