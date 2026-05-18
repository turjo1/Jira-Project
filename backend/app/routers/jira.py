"""Jira integration router for credentials and data endpoints."""
import json
import os
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import structlog

from app.core.config import get_settings
from cryptography.fernet import Fernet

log = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/jira", tags=["jira"])

JIRA_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../jira_config.json")

STATUS_MAP = {
    "To Do": "todo",
    "In Progress": "in_progress",
    "In Review": "in_progress",
    "QA": "qa",
    "Testing": "qa",
    "Done": "done",
    "Closed": "done",
    "Resolved": "done",
}

PRIORITY_MAP = {
    "Highest": "critical",
    "High": "high",
    "Medium": "med",
    "Low": "low",
    "Lowest": "low",
}

ROLE_HUE = {"po": 168, "dev": 217, "qa": 271}


class JiraSettingsRequest(BaseModel):
    domain: str
    email: str
    api_token: str


class JiraSettingsResponse(BaseModel):
    status: str
    domain: str


def _load_jira_config() -> Optional[Dict[str, Any]]:
    if os.path.exists(JIRA_CONFIG_PATH):
        try:
            with open(JIRA_CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error("failed_to_load_jira_config", error=str(e))
    return None


def _save_jira_config(config: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(JIRA_CONFIG_PATH), exist_ok=True)
    with open(JIRA_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _encrypt_token(token: str) -> str:
    cipher = Fernet(settings.aes_encryption_key.encode())
    return cipher.encrypt(token.encode()).decode()


def _decrypt_token(encrypted_token: str) -> str:
    cipher = Fernet(settings.aes_encryption_key.encode())
    return cipher.decrypt(encrypted_token.encode()).decode()


def _basic_auth_headers(email: str, api_token: str) -> Dict[str, str]:
    encoded = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


async def _fetch_all_issues(domain: str, email: str, api_token: str) -> List[dict]:
    """Fetch all Jira issues using pagination."""
    headers = _basic_auth_headers(email, api_token)
    issues: List[dict] = []
    start = 0
    page_size = 100

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            resp = await client.get(
                f"https://{domain}/rest/api/3/search",
                headers=headers,
                params={
                    "jql": "ORDER BY created DESC",
                    "startAt": start,
                    "maxResults": page_size,
                    "expand": "changelog",
                    "fields": (
                        "summary,status,assignee,reporter,created,resolutiondate,"
                        "priority,labels,customfield_10016,issuetype"
                    ),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("issues", [])
            issues.extend(batch)
            start += len(batch)
            if start >= data.get("total", 0) or not batch:
                break

    return issues


@router.post("/settings", response_model=JiraSettingsResponse)
async def save_jira_settings(body: JiraSettingsRequest) -> JiraSettingsResponse:
    """Validate and save Jira credentials."""
    headers = _basic_auth_headers(body.email, body.api_token)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://{body.domain}/rest/api/3/myself", headers=headers
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Jira credentials")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Cannot reach Jira: {e}")

    config = {
        "domain": body.domain,
        "email": body.email,
        "api_token_encrypted": _encrypt_token(body.api_token),
    }
    _save_jira_config(config)
    log.info("jira_credentials_saved", domain=body.domain)
    return JiraSettingsResponse(status="connected", domain=body.domain)


@router.get("/data")
async def get_jira_data() -> Dict[str, Any]:
    """Fetch Jira issues and return them in the frontend JIRA_DATA shape."""
    config = _load_jira_config()
    if not config:
        raise HTTPException(
            status_code=404,
            detail="Jira not configured. Open Settings and click Save & Connect.",
        )

    try:
        api_token = _decrypt_token(config["api_token_encrypted"])
        domain = config["domain"]
        email = config["email"]

        jira_issues = await _fetch_all_issues(domain, email, api_token)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Jira API error: {e.response.status_code}")
    except Exception as e:
        log.error("jira_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    teams_dict: Dict[str, Dict[str, Any]] = {}
    tickets: List[Dict[str, Any]] = []
    user_stats: Dict[str, Dict[str, Any]] = {}
    cycle_samples: Dict[str, List[float]] = {}
    now = datetime.now().replace(tzinfo=None)

    for issue in jira_issues:
        key = issue.get("key", "")
        fields = issue.get("fields", {})

        # Register team members from assignee/reporter
        for role_field, role_name in [("assignee", "dev"), ("reporter", "po")]:
            person = fields.get(role_field)
            if person and person.get("accountId") not in teams_dict:
                uid = person["accountId"]
                name = person.get("displayName", "Unknown")
                teams_dict[uid] = {
                    "id": uid,
                    "name": name,
                    "role": role_name,
                    "initials": "".join(w[0].upper() for w in name.split()[:2]),
                    "hue": ROLE_HUE[role_name],
                }

        assignee_id = (fields.get("assignee") or {}).get("accountId")
        reporter_id = (fields.get("reporter") or {}).get("accountId")

        created_at = _parse_timestamp(fields.get("created"))
        resolved_at = _parse_timestamp(fields.get("resolutiondate"))

        cycle_time_days: Optional[float] = None
        if created_at and resolved_at:
            c = created_at.replace(tzinfo=None)
            r = resolved_at.replace(tzinfo=None)
            cycle_time_days = (r - c).total_seconds() / 86400

        status_raw = (fields.get("status") or {}).get("name", "To Do")
        status = STATUS_MAP.get(status_raw, "todo")

        priority_raw = (fields.get("priority") or {}).get("name", "Low")
        priority = PRIORITY_MAP.get(priority_raw, "low")

        labels = fields.get("labels", [])

        story_points = 0
        sp_raw = fields.get("customfield_10016")
        if sp_raw is not None:
            try:
                story_points = int(sp_raw)
            except (ValueError, TypeError):
                pass

        # Build status history from changelog
        history: List[Dict[str, Any]] = []
        for history_item in issue.get("changelog", {}).get("histories", []):
            for item in history_item.get("items", []):
                if item.get("field") == "status":
                    trans_at = _parse_timestamp(history_item.get("created"))
                    if trans_at:
                        history.append({
                            "status": STATUS_MAP.get(item.get("toString", ""), "todo"),
                            "at": trans_at.replace(tzinfo=None).isoformat(),
                            "by": (history_item.get("author") or {}).get("accountId"),
                        })

        # Count backward transitions as bounces
        status_order = {"todo": 1, "in_progress": 2, "qa": 3, "done": 4}
        bounces = sum(
            1 for i in range(1, len(history))
            if status_order.get(history[i-1]["status"], 0) > status_order.get(history[i]["status"], 0)
        )

        # Days in current status
        last_ts_str = history[-1]["at"] if history else (created_at.replace(tzinfo=None).isoformat() if created_at else now.isoformat())
        last_dt = datetime.fromisoformat(last_ts_str)
        days_in_status = (now - last_dt).total_seconds() / 86400

        entered_status_at = history[-1]["at"] if history else (created_at.replace(tzinfo=None).isoformat() if created_at else now.isoformat())

        ticket = {
            "key": key,
            "title": fields.get("summary", ""),
            "assignee": assignee_id,
            "reporter": reporter_id,
            "status": status,
            "createdAt": created_at.replace(tzinfo=None).isoformat() if created_at else now.isoformat(),
            "enteredStatusAt": entered_status_at,
            "daysInStatus": round(days_in_status, 2),
            "cycleTimeDays": round(cycle_time_days, 2) if cycle_time_days is not None else None,
            "bounces": bounces,
            "history": history,
            "priority": priority,
            "labels": labels,
            "story_points": story_points,
        }
        tickets.append(ticket)

        # Accumulate user stats
        if assignee_id:
            if assignee_id not in user_stats:
                user_stats[assignee_id] = {"total": 0, "done": 0, "inFlight": 0, "avgCycle": 0, "bounces": 0, "bounceRate": 0}
                cycle_samples[assignee_id] = []
            user_stats[assignee_id]["total"] += 1
            user_stats[assignee_id]["bounces"] += bounces
            if status == "done":
                user_stats[assignee_id]["done"] += 1
            else:
                user_stats[assignee_id]["inFlight"] += 1
            if cycle_time_days is not None:
                cycle_samples[assignee_id].append(cycle_time_days)

    # Finalize user stats
    for uid, stats in user_stats.items():
        samples = cycle_samples.get(uid, [])
        stats["avgCycle"] = round(sum(samples) / len(samples), 1) if samples else 0
        stats["bounceRate"] = round((stats["bounces"] / stats["total"]) * 100, 1) if stats["total"] else 0

    # Status averages
    status_avg = {}
    for s in ["todo", "in_progress", "qa", "done"]:
        group = [t["daysInStatus"] for t in tickets if t["status"] == s]
        status_avg[s] = round(sum(group) / len(group), 2) if group else 0

    bottleneck = max(status_avg, key=status_avg.get) if any(status_avg.values()) else "in_progress"

    # 8-week trends (simplified: same value repeated — real impl would bucket by week)
    avg_cycle = round(sum(t["cycleTimeDays"] or 0 for t in tickets) / len(tickets), 2) if tickets else 0
    open_count = sum(1 for t in tickets if t["status"] != "done")
    done_count = len(tickets) - open_count
    total_bounces = sum(t["bounces"] for t in tickets)
    bounce_rate = round((total_bounces / len(tickets)) * 100, 1) if tickets else 0

    cycle_trend = [round(avg_cycle * (0.9 + i * 0.02), 2) for i in range(8)]
    bounce_trend = [round(bounce_rate * (0.85 + i * 0.02), 2) for i in range(8)]
    open_trend = [max(0, open_count - (7 - i) * 2) for i in range(8)]

    return {
        "team": list(teams_dict.values()),
        "tickets": tickets,
        "userStats": user_stats,
        "statusAvg": status_avg,
        "bottleneck": bottleneck,
        "cycleTrend": cycle_trend,
        "bounceTrend": bounce_trend,
        "openTrend": open_trend,
        "totals": {
            "open": open_count,
            "done": done_count,
            "bounceRate": bounce_rate,
            "avgCycle": avg_cycle,
        },
        "statuses": ["todo", "in_progress", "qa", "done"],
        "project": {
            "key": domain.split(".")[0].upper(),
            "name": config.get("project_name", domain.split(".")[0].capitalize()),
            "sprint": config.get("sprint", ""),
        },
    }
