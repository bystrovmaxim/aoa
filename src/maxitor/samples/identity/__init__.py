# src/maxitor/samples/identity/__init__.py
"""Identity bounded context stubs (entities only; no downstream actions wired)."""

from maxitor.samples.identity.domain import IdentityDomain

__all__ = ["IdentityDomain"]
