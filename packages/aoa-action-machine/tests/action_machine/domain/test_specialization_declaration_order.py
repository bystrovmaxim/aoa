# packages/aoa-action-machine/tests/action_machine/domain/test_specialization_declaration_order.py
"""
A file with a specialization loads the same way whatever the order of its classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Issue #415. A head with two kinds, kinds that link to another entity, and that entity
declared after the kinds: importing such a file used to recurse until ``RecursionError``.
Each module is imported in a fresh process, as a real module, because a module run
through ``exec()`` does not show the bug and a module imported once stays imported.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_SUPPORT = Path(__file__).resolve().parents[2] / "support"

_LOADS = """
import importlib, sys
module = importlib.import_module(sys.argv[1])
head = module.HeadCoreEntity
print(head.model_fields["kind"].annotation.__name__)
print(sorted(module.PartCoreEntity.model_fields))
"""


def _import_in_a_fresh_process(module: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _LOADS, f"specialization_order.{module}"],
        cwd=_SUPPORT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("module", ["declared_late", "declared_first"])
def test_a_specialization_loads_whatever_the_order_of_its_classes(module: str) -> None:
    """Before, ``declared_late`` ended with RecursionError; ``declared_first`` loaded."""
    ran = _import_in_a_fresh_process(module)
    assert ran.returncode == 0, ran.stderr[-2000:]
    assert ran.stdout.splitlines() == [
        "Specialization[Union[VariantSpecEntity, OtherSpecEntity], KindEnumEntity]",
        "['id', 'others', 'variants']",
    ]
