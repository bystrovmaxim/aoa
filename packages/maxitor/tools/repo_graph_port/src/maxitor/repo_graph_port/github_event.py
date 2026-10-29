# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/github_event.py
"""
GitHubEvent — the part of a GitHub webhook's body the port reads, and what kind of event it is.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

GitHub sends a large body with every event; the port needs a few fields of it.
This model takes those and ignores the rest, and ``as_params`` says which of the
three events the App is subscribed to it is — a push, a new tag, a pull request —
from the body's own shape, so the action receives a small, strict ``Params``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    POST body ──► GitHubEvent (unknown fields ignored) ──as_params──► ReceiveHostEventParams
       push:          ref, before, after          ──► kind "push"
       create:        ref_type "tag", master_branch ──► kind "tag"
       pull_request:  action, pull_request         ──► kind "pull_request" (edited, or closed and merged)
       anything else                               ──► kind "other"
"""

from __future__ import annotations

from typing import Any

from maxitor.repo_graph_port.actions.receive_host_event_action import ReceiveHostEventParams
from pydantic import BaseModel, ConfigDict


class GitHubEvent(BaseModel):
    """The fields of a GitHub webhook's body the port reads; the rest is ignored."""

    model_config = ConfigDict(extra="ignore")

    repository: dict[str, Any] = {}
    ref: str | None = None
    before: str | None = None
    after: str | None = None
    ref_type: str | None = None
    master_branch: str | None = None
    action: str | None = None
    pull_request: dict[str, Any] | None = None

    def kind(self) -> str:
        """``push``, ``tag``, ``pull_request`` (edited, or closed and merged), or ``other``."""
        if self.pull_request is not None:
            merged = self.action == "closed" and bool(self.pull_request.get("merged"))
            return "pull_request" if self.action == "edited" or merged else "other"
        if self.ref_type == "tag" and self.master_branch is not None:
            return "tag"
        if self.ref and self.before and self.after:
            return "push"
        return "other"

    def as_params(self) -> ReceiveHostEventParams:
        """The action's ``Params``: the kind, the repository, and what that kind needs."""
        pull = self.pull_request or {}
        return ReceiveHostEventParams(
            kind=self.kind(),
            repository=str(self.repository.get("full_name", "")),
            ref=self.ref or "",
            before=self.before or "",
            after=self.after or "",
            merge_commit_sha=str(pull.get("merge_commit_sha") or ""),
        )
