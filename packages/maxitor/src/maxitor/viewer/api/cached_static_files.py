# packages/maxitor/src/maxitor/viewer/api/cached_static_files.py
"""
CachedStaticFiles — serve the built client with the cache lifetime each file's name earns.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The client is built by Vite, which puts a content hash into every asset's name and none
into ``index.html``. That shape is what makes caching safe: a file whose name changes
with its content can be kept for a year and never revalidated, while the page has to be
revalidated on every open so a new release is picked up on the next visit.

This class is the static mount with that one decision spelled out in ``file_response``,
the single place every static answer passes through.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /assets/index-<hash>.js ─► file_response ─► Cache-Control: public, max-age=31536000, immutable
    GET /  or  /index.html      ─► file_response ─► Cache-Control: no-cache (with the etag FileResponse sets)
    GET /anything-else          ─► file_response ─► no Cache-Control, as before

The ``etag`` and ``last-modified`` of ``FileResponse`` are untouched, so ``no-cache`` costs one
conditional request (a ``304``) on a repeat open rather than a download.
"""

from __future__ import annotations

import os
from os import PathLike
from pathlib import Path

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

_IMMUTABLE = "public, max-age=31536000, immutable"
_PAGE = "no-cache"


class CachedStaticFiles(StaticFiles):
    """
    Static files whose ``Cache-Control`` follows the name of the file.

    AI-CORE-BEGIN
    ROLE: The static mount of the built client, adding one cache lifetime per served file.
    CONTRACT: ``file_response`` sets ``Cache-Control`` and changes nothing else in the answer.
    INVARIANTS: a hashed asset is immutable; ``index.html`` is always revalidated.
    AI-CORE-END
    """

    def file_response(
        self,
        full_path: str | PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """Answer one file, with the cache lifetime its name earns."""
        response = super().file_response(full_path, stat_result, scope, status_code)
        relative = self._relative_path(full_path)
        if relative is None:
            return response
        if relative.name == "index.html":
            response.headers["Cache-Control"] = _PAGE
        elif relative.parts and relative.parts[0] == "assets":
            response.headers["Cache-Control"] = _IMMUTABLE
        return response

    def _relative_path(self, full_path: str | PathLike[str]) -> Path | None:
        """Return the served file's path inside the mount, or ``None`` when it is outside it."""
        directory = self.directory
        if directory is None:
            return None
        try:
            return Path(full_path).resolve().relative_to(Path(directory).resolve())
        except ValueError:
            return None
