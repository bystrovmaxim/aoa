# src/maxitor/test_domain/actions/__init__.py
"""Регистрация тестовых действий (импорт подмодулей с побочным эффектом)."""

from maxitor.test_domain.actions.full_graph import (
    TestFullGraphAction,
    TestFullGraphParams,
    TestFullGraphResult,
)
from maxitor.test_domain.actions.legacy import (
    TestLegacyAction,
    TestLegacyParams,
    TestLegacyResult,
)
from maxitor.test_domain.actions.ping import (
    TestPingAction,
    TestPingParams,
    TestPingResult,
)
from maxitor.test_domain.actions.read import (
    TestReadAction,
    TestReadParams,
    TestReadResult,
)

__all__ = [
    "TestFullGraphAction",
    "TestFullGraphParams",
    "TestFullGraphResult",
    "TestLegacyAction",
    "TestLegacyParams",
    "TestLegacyResult",
    "TestPingAction",
    "TestPingParams",
    "TestPingResult",
    "TestReadAction",
    "TestReadParams",
    "TestReadResult",
]
