from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

jira_sync_duration_seconds = Histogram(
    "jira_sync_duration_seconds",
    "Duration of a single Jira sync run, in seconds",
    labelnames=("team_id",),
    buckets=(1, 5, 15, 30, 60, 120, 240, 300, 600),
)

jira_sync_errors_total = Counter(
    "jira_sync_errors_total",
    "Count of failed Jira sync runs",
    labelnames=("team_id", "reason"),
)

api_request_latency_ms = Histogram(
    "api_request_latency_ms",
    "API request latency in milliseconds",
    labelnames=("method", "route", "status"),
    buckets=(5, 10, 25, 50, 100, 200, 500, 1000, 2000, 5000),
)

jwt_refresh_total = Counter(
    "jwt_refresh_total",
    "Count of JWT refresh operations",
    labelnames=("result",),
)

tickets_in_db_total = Gauge(
    "tickets_in_db_total",
    "Tickets stored in DB per team",
    labelnames=("team_id",),
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
