# src/maxitor/test_domain/__init__.py
"""
Синтетический домен для построения полного статического графа ActionMachine.

Не предназначен для вызова в продукте — только ``build_test_coordinator()`` / дамп графа.
"""

from maxitor.test_domain.build import build_test_coordinator
from maxitor.test_domain.domain import TestDomain

__all__ = ["TestDomain", "build_test_coordinator"]
