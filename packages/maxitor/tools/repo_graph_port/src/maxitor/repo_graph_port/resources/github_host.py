# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/resources/github_host.py
"""
GitHubHost — what only GitHub knows about a repository, and the right to read a private one.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

git holds a history's commits, files and tags. GitHub holds the rest a version
shows — the pull request a commit came from and the release made of a tag — and
the token that opens a private repository. The port signs in as a GitHub App with
read-only rights, installed only on the chosen repositories; a public repository
is read with no token at all. The App's webhooks are signed with one secret, which
this resource checks.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    App id + private key ──JWT (RS256, 9 min)──► GET /repos/{r}/installation ──► POST /app/installations/{i}/access_tokens
                                                                                     └─► token, kept in memory, renewed 5 min before its hour ends
    public_token()        ──► GET /app/installations ──► the first installation's token, for public repositories' reads
    git_auth(r)            ──► {"http.https://github.com/.extraheader": "AUTHORIZATION: basic <x-access-token:token>"}
    pull_request_of(r, sha) ──► GET /repos/{r}/commits/{sha}/pulls ──► the merged one whose merge commit is sha, or the first
    open_pull_requests(r, b) ──► GET /repos/{r}/pulls?state=open&base=b, and each one's reviews ──► its state
    release_of(r, tag)      ──► GET /repos/{r}/releases/tags/{tag} ──► title and link, or None
    verify_webhook(body, s) ──► HMAC-SHA256 of the raw body with the webhook secret, compared in constant time

The token never reaches disk, a log, an error text or a remote URL: git gets it as
configuration of one call, the REST API in a request header.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from datetime import datetime
from typing import Any

import httpx
import jwt
from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_gateway import BaseGateway


@meta(description="GitHub: the App's token, a commit's pull request, a tag's release, the webhooks' signature", domain=RepoGraphDomain)
class GitHubHost(BaseGateway):
    """
    AI-CORE-BEGIN
    ROLE: Read from GitHub what git does not hold, and authenticate the port to it.
    CONTRACT: ``token_for`` gives an installation token for a repository the App is installed on, ``public_token`` one of any installation for reading public repositories (both ``None`` without an App); ``git_auth`` turns it into git configuration for one call; ``pull_request_of`` and ``release_of`` answer ``None`` when there is none; ``verify_webhook`` is false without a secret.
    INVARIANTS: The private key, the webhook secret and every token stay in memory; ``repr`` shows none of them.
    AI-CORE-END
    """

    def __init__(
        self,
        app_id: int | None = None,
        private_key: str | None = None,
        webhook_secret: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._app_id = app_id
        self._private_key = private_key
        self._webhook_secret = webhook_secret
        self._transport = transport
        self._tokens: dict[str, tuple[str, float]] = {}
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_settings(cls, settings: tuple[int, str, str] | None) -> GitHubHost:
        """
        The host as the config's ``[github]`` names it: the App's id, and its private key and webhook secret read
        from the environment variables the config names. A key kept on one line has its newlines written ``\\n``.
        """
        if settings is None:
            return cls()
        app_id, key_variable, secret_variable = settings
        private_key = os.environ.get(key_variable, "").replace("\\n", "\n") or None
        return cls(app_id, private_key, os.environ.get(secret_variable) or None)

    def __repr__(self) -> str:
        """Say whether an App is set, never its secrets."""
        return f"GitHubHost(app_id={self._app_id!r}, private_key={'set' if self._private_key else 'none'})"

    def get_wrapper_class(self) -> type[BaseGateway] | None:
        """Return ``None``: nested actions use this same host."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the host is not a rollup target."""
        return False

    async def token_for(self, repository: str) -> str | None:
        """An installation token that reads ``repository``, or ``None`` when no App is set."""
        return await self._installation_token(repository, f"/repos/{repository}/installation")

    async def public_token(self) -> str | None:
        """
        A token of any installation of the App, for the REST API's reads of public repositories.

        Anonymous calls get 60 an hour per address; an installation's token reads any public
        repository with that installation's far larger limit. ``None`` when no App is set.
        """
        return await self._installation_token("", "/app/installations")

    async def _installation_token(self, kept_as: str, find: str) -> str | None:
        """An installation's token, found through ``find`` and kept under ``kept_as`` until 5 minutes before it ends."""
        if self._app_id is None or not self._private_key:
            return None
        kept = self._tokens.get(kept_as)
        if kept is not None and kept[1] - time.time() > 300:
            return kept[0]
        now = int(time.time())
        app = jwt.encode({"iat": now - 60, "exp": now + 540, "iss": str(self._app_id)}, self._private_key, algorithm="RS256")
        headers = {"Authorization": f"Bearer {app}", "Accept": "application/vnd.github+json"}
        found = await self._call("GET", find, headers)
        installation = found[0] if isinstance(found, list) else found
        granted = await self._call("POST", f"/app/installations/{installation['id']}/access_tokens", headers)
        expires = datetime.fromisoformat(granted["expires_at"].replace("Z", "+00:00")).timestamp()
        self._tokens[kept_as] = (granted["token"], expires)
        return str(granted["token"])

    @staticmethod
    def git_auth(token: str | None) -> dict[str, str]:
        """git configuration that presents ``token`` to github.com for one call; nothing for no token."""
        if token is None:
            return {}
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        return {"http.https://github.com/.extraheader": f"AUTHORIZATION: basic {basic}"}

    async def pull_request_of(self, repository: str, sha: str, token: str | None) -> dict[str, str | int] | None:
        """The pull request the commit ``sha`` came from: number, title, body, url, its author's login and avatar; ``None`` when there is none."""
        pulls = await self._call("GET", f"/repos/{repository}/commits/{sha}/pulls", self._headers(token), missing=[])
        if not pulls:
            return None
        chosen = next((p for p in pulls if p.get("merge_commit_sha") == sha), pulls[0])
        user = chosen.get("user") or {}
        return {
            "number": chosen["number"],
            "title": chosen["title"],
            "body": chosen.get("body") or "",
            "url": chosen["html_url"],
            "author": user.get("login") or "",
            "avatar": user.get("avatar_url") or "",
        }

    async def open_pull_requests(self, repository: str, branch: str, token: str | None) -> list[dict[str, str | int]]:
        """The pull requests open into ``branch``: number, title, body, url, author, avatar, head and state — draft, changes_requested, approved or open."""
        pulls = await self._call("GET", f"/repos/{repository}/pulls?state=open&base={branch}&per_page=100", self._headers(token), missing=[])
        found: list[dict[str, str | int]] = []
        for pull in pulls:
            reviews = await self._call("GET", f"/repos/{repository}/pulls/{pull['number']}/reviews?per_page=100", self._headers(token), missing=[])
            # Each reviewer's last word counts.
            last = {review["user"]["login"]: review["state"] for review in reviews if review.get("user") and review.get("state") in ("APPROVED", "CHANGES_REQUESTED")}
            state = "draft" if pull.get("draft") else "changes_requested" if "CHANGES_REQUESTED" in last.values() else "approved" if "APPROVED" in last.values() else "open"
            user = pull.get("user") or {}
            found.append({
                "number": pull["number"],
                "title": pull["title"],
                "body": pull.get("body") or "",
                "url": pull["html_url"],
                "author": user.get("login") or "",
                "avatar": user.get("avatar_url") or "",
                "head": pull["head"]["sha"],
                "state": state,
            })
        return found

    async def release_of(self, repository: str, tag: str, token: str | None) -> dict[str, str] | None:
        """The release made of ``tag``: its title and link; ``None`` when the tag has none."""
        release = await self._call("GET", f"/repos/{repository}/releases/tags/{tag}", self._headers(token), missing=None)
        if release is None:
            return None
        return {"title": release.get("name") or tag, "url": release["html_url"]}

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        """Whether ``signature`` (``sha256=<hex>``) is the HMAC-SHA256 of ``body`` with the webhook secret."""
        if not self._webhook_secret or not signature.startswith("sha256="):
            return False
        expected = hmac.new(self._webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.removeprefix("sha256="))

    @staticmethod
    def _headers(token: str | None) -> dict[str, str]:
        """The REST API's headers, with the token when there is one."""
        headers = {"Accept": "application/vnd.github+json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _call(self, method: str, path: str, headers: dict[str, str], missing: Any = ...) -> Any:
        """One REST call; a ``404`` gives ``missing`` when one is given, any other failure raises without the headers."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url="https://api.github.com", timeout=20.0, transport=self._transport)
        answer = await self._client.request(method, path, headers=headers)
        if answer.status_code == 404 and missing is not ...:
            return missing
        if answer.status_code >= 400:
            raise httpx.HTTPStatusError(f"GitHub answered {answer.status_code} to {method} {path}", request=answer.request, response=answer)
        return answer.json()
