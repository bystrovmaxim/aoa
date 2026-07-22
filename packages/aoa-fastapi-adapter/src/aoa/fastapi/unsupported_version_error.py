# packages/aoa-fastapi-adapter/src/aoa/fastapi/unsupported_version_error.py
"""
``UnsupportedVersionError`` — a resolver request named a wire-language ``version`` this server does not speak.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS EXISTS
═══════════════════════════════════════════════════════════════════════════════

Chapter 3.5 rule 8: the "language" of questions and answers between client and
server has its own version number (``ResolveRequest.version``, echoed back on
``ResolveResponse.version`` and separately published as ``Manifest.version``) —
distinct from the manifest's own shape (``manifest_schema_version``) and from its
content hash (``manifest_version``). A client built against a version this server
no longer speaks must be told so plainly, before the server tries to "half
understand" a request shaped for a different contract — the most dangerous
failure mode, since fields can silently change meaning between versions.
``POST /permissions/resolve`` checks ``version`` first, before authentication, so
a client speaking the wrong language is never made to prove its identity just to
be told to upgrade.
"""

from __future__ import annotations


class UnsupportedVersionError(ValueError):
    """Raised when ``ResolveRequest.version`` is not the version this server speaks."""

    def __init__(self, requested_version: int, *, supported_version: int) -> None:
        super().__init__(
            f"version {requested_version} is not supported by this server (speaks "
            f"{supported_version}) — update the client."
        )
        self.requested_version = requested_version
        self.supported_version = supported_version
