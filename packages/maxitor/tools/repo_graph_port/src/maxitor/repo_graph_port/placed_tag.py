# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/placed_tag.py
"""
PlacedTag — a tag as a version shows it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A version lists the tags placed on it, each with the release the host made of it
when there is one.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``place_tags`` ──tag names──► ``PlacedTag`` ──► ``VersionRecord.tags``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlacedTag(BaseModel):
    """A tag on a version, and its release."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="The tag's short name")
    release: dict[str, str] | None = Field(default=None, description="The host's release of the tag: title and url")
