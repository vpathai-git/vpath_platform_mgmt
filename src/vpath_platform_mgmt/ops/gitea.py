"""Gitea contents-API client — the only writer into the Deploy-of-Record.

Scoped deliberately to the four calls the GitOps verbs need (read a file,
write a file, delete a file, test a path). Every non-2xx is an error: there
is no "assume missing on failure" path, because a swallowed 500 here would
look exactly like an app that is not installed.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

DEFAULT_BRANCH = "main"
TIMEOUT_SECONDS = 30.0


class GiteaError(Exception):
    """A Gitea call failed, or its response was not what the API promises."""


@dataclass(frozen=True)
class GiteaFile:
    """A file's decoded content plus the blob sha its update must carry."""

    text: str
    sha: str


class GiteaClient:
    """Reads and writes one repository through Gitea's contents API."""

    def __init__(
        self,
        base_url: str,
        owner: str,
        repo: str,
        token: str,
        branch: str = DEFAULT_BRANCH,
        verify_tls: bool = True,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url:
            raise GiteaError("Gitea base URL is required")
        if not token:
            raise GiteaError("a Gitea API token is required to write the record")
        self._owner = owner
        self._repo = repo
        self._branch = branch
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            verify=verify_tls,
            timeout=TIMEOUT_SECONDS,
            headers={"Authorization": f"token {token}"},
        )

    @property
    def repo_slug(self) -> str:
        """``owner/repo`` — used in job logs and audit lines."""
        return f"{self._owner}/{self._repo}"

    def _contents_url(self, path: str) -> str:
        return f"/api/v1/repos/{self._owner}/{self._repo}/contents/{path}"

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            return self._client.request(
                method, self._contents_url(path), params=params, json=json
            )
        except httpx.HTTPError as exc:
            raise GiteaError(f"Gitea {method} {path} failed: {exc}") from exc

    def get_file(self, path: str) -> GiteaFile:
        """Read a file, or fail hard if it is absent or not a file."""
        response = self._request("GET", path, params={"ref": self._branch})
        if response.status_code == 404:
            raise GiteaError(f"{self.repo_slug}: {path} not found on {self._branch}")
        if response.status_code != 200:
            raise GiteaError(
                f"{self.repo_slug}: GET {path} returned {response.status_code}"
            )
        body = response.json()
        if not isinstance(body, dict) or body.get("type") != "file":
            raise GiteaError(f"{self.repo_slug}: {path} is not a file")
        encoded = body.get("content")
        sha = body.get("sha")
        if not isinstance(encoded, str) or not isinstance(sha, str):
            raise GiteaError(f"{self.repo_slug}: {path} response lacks content/sha")
        return GiteaFile(base64.b64decode(encoded).decode("utf-8"), sha)

    def exists(self, path: str) -> bool:
        """Whether a path (file or directory) is present on the branch."""
        response = self._request("GET", path, params={"ref": self._branch})
        if response.status_code == 404:
            return False
        if response.status_code != 200:
            raise GiteaError(
                f"{self.repo_slug}: GET {path} returned {response.status_code}"
            )
        return True

    def update_file(self, path: str, text: str, sha: str, message: str) -> str:
        """Replace a file's content; returns the new commit sha."""
        payload = {
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "sha": sha,
            "message": message,
            "branch": self._branch,
        }
        response = self._request("PUT", path, json=payload)
        if response.status_code not in (200, 201):
            raise GiteaError(
                f"{self.repo_slug}: PUT {path} returned {response.status_code}: "
                f"{response.text[:200]}"
            )
        return self._commit_sha(response, path)

    def create_file(self, path: str, text: str, message: str) -> str:
        """Create a file that does not exist yet; returns the commit sha.

        Distinct from ``update_file``: Gitea's contents API creates with POST
        and no blob sha, and rejects a PUT that carries none.
        """
        payload = {
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "message": message,
            "branch": self._branch,
        }
        response = self._request("POST", path, json=payload)
        if response.status_code not in (200, 201):
            raise GiteaError(
                f"{self.repo_slug}: POST {path} returned {response.status_code}: "
                f"{response.text[:200]}"
            )
        return self._commit_sha(response, path)

    def write_file(self, path: str, text: str, message: str) -> str:
        """Create the file, or replace it if it is already there.

        Uninstall/install cycles revisit the same paths, so a create-only
        write fails the second time round with "file already exists".
        """
        if self.exists(path):
            return self.update_file(path, text, self.get_file(path).sha, message)
        return self.create_file(path, text, message)

    def delete_path(self, path: str, message: str) -> str:
        """Delete a file by resolving its blob sha first; returns commit sha."""
        current = self.get_file(path)
        payload = {"sha": current.sha, "message": message, "branch": self._branch}
        response = self._request("DELETE", path, json=payload)
        if response.status_code != 200:
            raise GiteaError(
                f"{self.repo_slug}: DELETE {path} returned {response.status_code}"
            )
        return self._commit_sha(response, path)

    def _commit_sha(self, response: httpx.Response, path: str) -> str:
        body = response.json()
        commit = body.get("commit") if isinstance(body, dict) else None
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(sha, str):
            raise GiteaError(f"{self.repo_slug}: {path} write returned no commit sha")
        return sha
