"""Service for interacting with Jira API."""
import httpx
from typing import Optional, List
import structlog
from datetime import datetime

log = structlog.get_logger(__name__)


class JiraAPIService:
    """Service for fetching data from Jira API."""

    def __init__(self, jira_instance_url: str, access_token: str):
        """
        Initialize Jira API service.

        Args:
            jira_instance_url: Base URL of Jira instance (e.g., https://company.atlassian.net)
            access_token: OAuth2 access token for Jira API
        """
        self.base_url = jira_instance_url.rstrip("/")
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def fetch_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
    ) -> List[dict]:
        """
        Fetch issues from Jira using JQL query.

        Args:
            jql: JQL query string (e.g., "project = PROJ AND assignee in (user1, user2)")
            max_results: Maximum number of results per request (API limit ~100)
            start_at: Starting index for pagination

        Returns:
            List of issue dictionaries with full details including changelog
        """
        issues = []
        current_start = start_at

        try:
            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        f"{self.base_url}/rest/api/3/search",
                        params={
                            "jql": jql,
                            "maxResults": max_results,
                            "startAt": current_start,
                            "expand": "changelog",
                            "fields": (
                                "summary,status,assignee,created,resolutiondate,"
                                "resolution,issuetype,key"
                            ),
                        },
                        headers=self.headers,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Add issues to result
                    batch = data.get("issues", [])
                    issues.extend(batch)

                    # Check if we have more results
                    total = data.get("total", 0)
                    current_start += len(batch)

                    if current_start >= total or len(batch) == 0:
                        break

                    log.info(
                        "fetched_issue_batch",
                        count=len(batch),
                        total=total,
                        fetched=current_start,
                    )

            log.info("jira_fetch_complete", total_issues=len(issues))
            return issues

        except httpx.HTTPError as e:
            log.error(
                "jira_api_error",
                error=str(e),
                jql=jql,
            )
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Get user details by Jira user ID.

        Args:
            user_id: Jira user account ID

        Returns:
            User dictionary with email, name, etc.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/user",
                    params={"accountId": user_id},
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            log.warning("jira_user_fetch_failed", user_id=user_id, error=str(e))
            return None

    async def verify_credentials(self) -> bool:
        """
        Verify that credentials are valid by fetching current user.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/myself",
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                log.info("jira_credentials_valid")
                return True
        except httpx.HTTPError as e:
            log.warning("jira_credentials_invalid", error=str(e))
            return False

    @staticmethod
    def parse_jira_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
        """
        Parse Jira ISO 8601 timestamp string to datetime.

        Args:
            timestamp_str: ISO 8601 formatted string (e.g., "2024-05-18T10:30:45.123-0500")

        Returns:
            datetime object or None if invalid
        """
        if not timestamp_str:
            return None

        try:
            # Jira returns ISO 8601 with timezone; fromisoformat handles it in Python 3.11+
            # For earlier versions, use dateutil or manual parsing
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            log.warning("failed_to_parse_timestamp", timestamp=timestamp_str)
            return None
