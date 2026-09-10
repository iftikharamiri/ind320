"""Store TA feedback as an inbox of JSON files on a branch of the GitHub repo.

The app never opens issues itself. It only appends raw, untriaged feedback to a
dedicated branch so the main branch stays clean; a separate agent reads that
inbox and turns it into GitHub issues.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

API = "https://api.github.com"
TIMEOUT = 15


class FeedbackError(RuntimeError):
    """Feedback could not be stored. The message is safe to show to the user."""


@dataclass(frozen=True)
class Inbox:
    """Append-only feedback inbox backed by the GitHub contents API."""

    repo: str
    token: str
    branch: str = "feedback"
    path: str = "feedback/inbox"

    @classmethod
    def from_config(cls, config) -> "Inbox":
        missing = [k for k in ("repo", "token") if not config.get(k)]
        if missing:
            raise FeedbackError(
                f"Missing {' and '.join(missing)} in the [feedback] secrets section."
            )
        return cls(
            repo=config["repo"],
            token=config["token"],
            branch=config.get("branch", "feedback"),
            path=config.get("path", "feedback/inbox"),
        )

    def _call(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        try:
            response = requests.request(
                method,
                f"{API}{endpoint}",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=TIMEOUT,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise FeedbackError(f"Could not reach GitHub: {exc}") from exc

        if response.status_code == 401:
            raise FeedbackError("GitHub rejected the token (401). Check the secret.")
        if response.status_code == 403:
            raise FeedbackError(
                "GitHub denied the request (403). The token needs write access to "
                f"{self.repo}."
            )
        return response

    def _ensure_branch(self) -> None:
        """Create the feedback branch off the default branch the first time."""
        if self._call("GET", f"/repos/{self.repo}/git/ref/heads/{self.branch}").ok:
            return

        repo_info = self._call("GET", f"/repos/{self.repo}")
        if not repo_info.ok:
            raise FeedbackError(f"Repository {self.repo} not found (or not visible).")
        default_branch = repo_info.json()["default_branch"]

        head = self._call("GET", f"/repos/{self.repo}/git/ref/heads/{default_branch}")
        if not head.ok:
            raise FeedbackError(f"Could not read {default_branch} to branch from.")

        created = self._call(
            "POST",
            f"/repos/{self.repo}/git/refs",
            json={
                "ref": f"refs/heads/{self.branch}",
                "sha": head.json()["object"]["sha"],
            },
        )
        # 422 means someone created it between our check and this call, which is fine.
        if not created.ok and created.status_code != 422:
            raise FeedbackError(f"Could not create branch {self.branch}.")

    def submit(self, topic: str, message: str, author: str = "") -> str:
        """Write one feedback item and return the path it was stored at."""
        message = message.strip()
        if not message:
            raise FeedbackError("Feedback message is empty.")

        now = datetime.now(timezone.utc)
        record = {
            "id": uuid.uuid4().hex[:8],
            "submitted_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "topic": topic,
            "author": author.strip(),
            "message": message,
            "status": "new",
        }
        filename = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{record['id']}.json"
        target = f"{self.path}/{filename}"

        self._ensure_branch()
        body = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
        response = self._call(
            "PUT",
            f"/repos/{self.repo}/contents/{target}",
            json={
                "message": f"feedback: {topic}",
                "content": base64.b64encode(body.encode()).decode(),
                "branch": self.branch,
            },
        )
        if not response.ok:
            detail = response.json().get("message", response.reason)
            raise FeedbackError(f"GitHub refused to save the feedback: {detail}")
        return target
