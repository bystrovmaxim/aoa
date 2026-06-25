# packages/aoa-otel/tests/support/__init__.py
"""
Test-support facade for aoa-otel.

Re-exports the scenario symbols the otel tests import by name, so test bodies
need only change their import path (``from .support import ...``) and keep using
``PingAction`` / ``TestDomain`` unchanged.
"""

from .domain_model import PingAction, SystemDomain, TestDomain

__all__ = [
    "PingAction",
    "SystemDomain",
    "TestDomain",
]
