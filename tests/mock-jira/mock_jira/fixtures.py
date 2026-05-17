"""Fixture data for mock Jira server."""
from datetime import datetime, timedelta
from typing import Dict, List
from .models import (
    JiraIssue,
    JiraField,
    JiraIssueStatus,
    JiraUser,
    JiraChangeHistory,
    JiraHistoryItem,
)

# Fake users
FAKE_USERS = {
    "jira-user-123": JiraUser(
        accountId="jira-user-123",
        displayName="Test User",
        emailAddress="testuser@example.com",
    ),
    "jira-user-456": JiraUser(
        accountId="jira-user-456",
        displayName="Another User",
        emailAddress="another@example.com",
    ),
    "jira-user-789": JiraUser(
        accountId="jira-user-789",
        displayName="Manager User",
        emailAddress="manager@example.com",
    ),
}

# Fake statuses
FAKE_STATUSES = {
    "open": JiraIssueStatus(id="10000", name="Open"),
    "in_progress": JiraIssueStatus(id="10001", name="In Progress"),
    "in_review": JiraIssueStatus(id="10002", name="In Review"),
    "done": JiraIssueStatus(id="10003", name="Done"),
}

# Sample issues
def generate_fake_issues(team_key: str = "TEST", count: int = 100) -> List[JiraIssue]:
    """Generate realistic fake Jira issues."""
    issues = []
    now = datetime.utcnow()

    statuses = [
        FAKE_STATUSES["open"],
        FAKE_STATUSES["in_progress"],
        FAKE_STATUSES["in_review"],
        FAKE_STATUSES["done"],
    ]
    users = list(FAKE_USERS.values())

    for i in range(count):
        created_at = now - timedelta(days=(i % 60))
        updated_at = created_at + timedelta(days=(i % 10))

        status = statuses[i % len(statuses)]
        assignee = users[i % len(users)] if i % 2 == 0 else None

        issue = JiraIssue(
            key=f"{team_key}-{i+1}",
            id=f"jira-id-{i+1}",
            fields=JiraField(
                summary=f"Test Issue {i+1} - {['Bug', 'Feature', 'Improvement'][i % 3]}",
                status=status,
                assignee=assignee,
                created=created_at.isoformat() + "Z",
                updated=updated_at.isoformat() + "Z",
                key=f"{team_key}-{i+1}",
            ),
        )
        issues.append(issue)

    return issues


def generate_fake_changelog(issue_key: str) -> List[JiraChangeHistory]:
    """Generate realistic fake issue changelog."""
    now = datetime.utcnow()
    base_time = now - timedelta(days=30)

    # Typical transition flow: Open -> In Progress -> In Review -> Done
    transitions = [
        {
            "time_offset": 0,
            "from": "Open",
            "to": "In Progress",
        },
        {
            "time_offset": 3,
            "from": "In Progress",
            "to": "In Review",
        },
        {
            "time_offset": 7,
            "from": "In Review",
            "to": "Done",
        },
    ]

    # Add bounce for some issues
    if hash(issue_key) % 5 == 0:
        transitions.append({
            "time_offset": 10,
            "from": "Done",
            "to": "In Progress",
        })

    histories = []
    for trans in transitions:
        history = JiraChangeHistory(
            id=f"history-{len(histories)+1}",
            created=(base_time + timedelta(days=trans["time_offset"])).isoformat() + "Z",
            items=[
                JiraHistoryItem(
                    field="status",
                    fromString=trans["from"],
                    toString=trans["to"],
                ),
            ],
        )
        histories.append(history)

    return histories
