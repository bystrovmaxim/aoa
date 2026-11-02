# packages/aoa-action-machine/tests/action_machine/model/test_import_order.py
"""
No first import closes a cycle through ``BaseEvent``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseEvent`` needs the logging package, and the logging package needs ``Context``. Each
case starts a fresh process, because a cycle shows only in the order of the first import.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

FIRST_IMPORTS = (
    "context.context",
    "context",
    "auth",
    "model",
    "model.base_action",
    "model.base_event",
    "domain",
    "domain.base_domain",
    "logging",
    "runtime.tools_box",
    "runtime.action_product_machine",
    "intents.aspects",
    "graph.node_graph_coordinator_factory",
    "testing.bench",
)


@pytest.mark.parametrize("module", FIRST_IMPORTS)
def test_the_first_import_closes_no_cycle(module: str) -> None:
    code = f"import aoa.action_machine.{module}\nfrom aoa.action_machine.model.base_event import BaseEvent\n"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
