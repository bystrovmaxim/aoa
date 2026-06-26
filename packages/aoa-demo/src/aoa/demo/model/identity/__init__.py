# packages/aoa-demo/src/aoa/demo/model/identity/__init__.py
"""Identity bounded context stubs (entities only; no downstream actions wired)."""

from aoa.demo.model.identity.domain import IdentityDomain

__all__ = ["IdentityDomain"]
