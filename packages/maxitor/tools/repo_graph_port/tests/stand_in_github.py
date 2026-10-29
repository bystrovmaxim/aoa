# packages/maxitor/tools/repo_graph_port/tests/stand_in_github.py
"""A stand-in for GitHub's REST API over ``httpx.MockTransport``: an App, its installation, pull requests and releases."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

APP_ID = 4242
TOKEN = "ghs_standinTOKEN0123456789abcdefghijklmnop"


def app_key() -> tuple[str, Any]:
    """A fresh RSA key pair for the App: the private key as PEM text, and the public key."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return pem, private.public_key()


@dataclass
class StandInGitHub:
    """What the stand-in knows, and every request it was asked."""

    public_key: Any
    pulls: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    releases: dict[str, dict[str, Any]] = field(default_factory=dict)
    asked: list[str] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        """The transport a ``GitHubHost`` is built with."""
        return httpx.MockTransport(self._answer)

    def _answer(self, request: httpx.Request) -> httpx.Response:
        """One answer, as GitHub's REST API gives it."""
        path = request.url.path
        self.asked.append(f"{request.method} {path}")
        authorization = request.headers.get("authorization", "")
        if path.endswith("/installation") or path.startswith("/app/"):
            claims = jwt.decode(authorization.removeprefix("Bearer "), self.public_key, algorithms=["RS256"])
            assert claims["iss"] == str(APP_ID)
            if path.endswith("/installation"):
                return httpx.Response(200, json={"id": 7})
            return httpx.Response(201, json={"token": TOKEN, "expires_at": "2099-01-01T00:00:00Z"})
        if "/commits/" in path and path.endswith("/pulls"):
            sha = path.split("/commits/")[1].split("/")[0]
            return httpx.Response(200, json=self.pulls.get(sha, []))
        if "/releases/tags/" in path:
            tag = path.split("/releases/tags/")[1]
            release = self.releases.get(tag)
            return httpx.Response(200, json=release) if release else httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(404, content=json.dumps({"message": "Not Found"}))
