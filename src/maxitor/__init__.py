# src/maxitor/__init__.py
"""
Maxitor — минимальная обвязка вокруг синтетического **test_domain** для ActionMachine.

Задача пакета: одним импортом получить маркер домена и фабрику координатора, чтобы
построить **статический граф** интентов (роли, действия, сущности, плагины и т.д.)
без отдельного ``graph_domain`` и без импорта из ``archive``.

AI-CORE-BEGIN
ROLE: Публичная точка входа для тестового графа ActionMachine.
EXPORTS: ``TestDomain``, ``build_test_coordinator``, ``export_test_domain_graph_graphml``.
ENTRY PATTERN: ``from maxitor import build_test_coordinator`` затем ``c = build_test_coordinator()``;
GraphML: ``from maxitor import export_test_domain_graph_graphml``.
INTERNAL FLOW: ``test_domain`` регистрирует декларации → ``CoreActionMachine.create_coordinator``.
AI-CORE-END
"""

from __future__ import annotations

from maxitor.graph_export import export_test_domain_graph_graphml
from maxitor.test_domain.build import build_test_coordinator
from maxitor.test_domain.domain import TestDomain

__all__ = [
    "TestDomain",
    "build_test_coordinator",
    "export_test_domain_graph_graphml",
]
