# src/maxitor/samples/build.py
"""Импорт всех модулей samples и сборка ``GraphCoordinator`` (как в проде — только сайд-эффекты)."""

from __future__ import annotations

import importlib
from typing import Final

from action_machine.legacy.core import Core
from graph.graph_coordinator import GraphCoordinator

_MODULES: Final[tuple[str, ...]] = (
    "maxitor.samples.roles",
    # billing — полный контур как у store
    "maxitor.samples.billing.domain",
    "maxitor.samples.billing.entities",
    "maxitor.samples.billing.dependencies",
    "maxitor.samples.billing.resources",
    "maxitor.samples.billing.plugins",
    "maxitor.samples.billing.actions",
    # messaging
    "maxitor.samples.messaging.domain",
    "maxitor.samples.messaging.entities",
    "maxitor.samples.messaging.dependencies",
    "maxitor.samples.messaging",
    "maxitor.samples.messaging.resources",
    "maxitor.samples.messaging.plugins",
    "maxitor.samples.messaging.actions",
    # catalog
    "maxitor.samples.catalog.domain",
    "maxitor.samples.catalog.entities",
    "maxitor.samples.catalog.dependencies",
    "maxitor.samples.catalog.resources",
    "maxitor.samples.catalog.plugins",
    # store (зависит от billing/messaging сервисов)
    "maxitor.samples.store.domain",
    "maxitor.samples.store.dependencies",
    "maxitor.samples.store.entities",
    "maxitor.samples.store.resources",
    "maxitor.samples.store.plugins",
    "maxitor.samples.catalog.actions",
    "maxitor.samples.store.actions",
    # support — @depends на BaseAction в том же домене и в store
    "maxitor.samples.support.domain",
    "maxitor.samples.support.actions",
)


def build_sample_coordinator() -> GraphCoordinator:
    for name in _MODULES:
        importlib.import_module(name)
    return Core.create_coordinator()
