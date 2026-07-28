"""HTTP client for the Ops API — the single integration path of the CLI.

Wraps any ``httpx.Client`` (the real one in production, Starlette's
``TestClient`` in tests) so the CLI is testable against the in-process API
without a network.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import httpx

from vpath_platform_mgmt.api.auth import DEV_ACTOR_HEADER, DEV_ROLE_HEADER

TERMINAL_STATES = ("succeeded", "failed")
DEFAULT_POLL_SECONDS = 0.2


class ApiError(Exception):
    """Non-2xx API answer; carries the HTTP status and server detail."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class Caller:
    """Who the CLI acts as (dev-auth identity until OIDC lands, decision 6)."""

    actor: str
    role: str


class OpsClient:
    """Typed calls against the Ops API endpoints.

    With a bearer token (from ``vpath login``) requests authenticate via
    OIDC; without one, dev headers are sent — which only a simulated-engine
    server accepts (docs/ACCESS_MECHANISM.md).
    """

    def __init__(
        self, http: httpx.Client, caller: Caller, bearer: str | None = None
    ) -> None:
        self._http = http
        self._caller = caller
        self._bearer = bearer

    @property
    def auth_source(self) -> str:
        """Which credential the client sends: 'oidc token' or 'dev headers'."""
        return "oidc token" if self._bearer else "dev headers"

    def _headers(self) -> dict[str, str]:
        if self._bearer:
            return {"Authorization": f"Bearer {self._bearer}"}
        return {
            DEV_ACTOR_HEADER: self._caller.actor,
            DEV_ROLE_HEADER: self._caller.role,
        }

    def _checked(self, response: httpx.Response) -> httpx.Response:
        if response.status_code >= 400:
            try:
                detail = str(response.json().get("detail", response.text))
            except ValueError:
                detail = response.text
            raise ApiError(response.status_code, detail)
        return response

    def state(self) -> dict[str, object]:
        """Full console snapshot: engine, jobs, locks, audit, health."""
        response = self._http.get("/api/state", headers=self._headers())
        return dict(self._checked(response).json())

    def submit(self, verb: str, app: str, confirm: str = "") -> str:
        """Submit a verb; returns the job id (server enforces every gate)."""
        response = self._http.post(
            "/api/jobs",
            json={"verb": verb, "app": app, "confirm": confirm},
            headers=self._headers(),
        )
        return str(self._checked(response).json()["job"])

    def push_source(
        self,
        app: str,
        archive: bytes,
        provenance: dict[str, str],
        replace: bool = False,
    ) -> dict[str, object]:
        """Upload app source for materialization into the server checkout."""
        headers = self._headers()
        headers["Content-Type"] = "application/octet-stream"
        headers["X-Source-Repo"] = provenance.get("repo", "")
        headers["X-Source-Ref"] = provenance.get("ref", "")
        headers["X-Source-Commit"] = provenance.get("commit", "")
        headers["X-Source-Dirty"] = provenance.get("dirty", "false")
        headers["X-Source-Replace"] = "true" if replace else "false"
        response = self._http.post(
            f"/api/apps/{app}/source", content=archive, headers=headers, timeout=120.0
        )
        return dict(self._checked(response).json())

    def job(self, job_id: str) -> dict[str, object]:
        """One job with its full log."""
        response = self._http.get(f"/api/jobs/{job_id}", headers=self._headers())
        return dict(self._checked(response).json())

    def wait(
        self,
        job_id: str,
        on_step: Callable[[str], None] | None = None,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        timeout_seconds: float = 600.0,
    ) -> dict[str, object]:
        """Poll a job to a terminal state, streaming new log lines."""
        seen = 0
        deadline = time.monotonic() + timeout_seconds
        while True:
            job = self.job(job_id)
            log = cast("list[object]", job.get("log", []))
            if on_step is not None:
                for line in log[seen:]:
                    on_step(str(line))
            seen = len(log)
            if str(job["state"]) in TERMINAL_STATES:
                return job
            if time.monotonic() > deadline:
                raise ApiError(408, f"timed out waiting for job {job_id}")
            time.sleep(poll_seconds)
