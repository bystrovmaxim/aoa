# tests/action_machine/domain/test_value_export.py
"""
Tests for ``value`` as the public declaration surface of the domain package.

The alias left with the metaclass and the namespace, so this module asserts the
two halves of that removal: the factory is exported and usable from the package,
and nothing anywhere still names the machinery that used to hide it.
"""

from __future__ import annotations

from pathlib import Path

import aoa.action_machine.domain as domain
from aoa.action_machine.domain import BaseEnumEntity, BaseStateEntity, declared_values, value
from aoa.action_machine.domain.declared_values import ValueSpec

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_SCANNED_ROOTS = ("packages", "examples")
_REMOVED_NAMES = ("DeclaredValuesMeta", "_DeclaredValuesNamespace")


def test_value_is_a_public_import_of_the_domain_package() -> None:
    """``value`` is exported by name and listed in ``__all__``."""
    assert domain.value is value
    assert "value" in domain.__all__
    assert domain.__all__.count("value") == 1


def test_value_returns_a_placeholder_outside_a_class_body() -> None:
    """The factory is usable on its own, and what it returns is not a model."""
    placeholder = value(code="x", display_name="X")
    assert isinstance(placeholder, ValueSpec)
    assert placeholder.kwargs == {"code": "x", "display_name": "X"}
    assert not isinstance(placeholder, (BaseEnumEntity, BaseStateEntity))


def test_the_removed_machinery_is_gone_from_the_module() -> None:
    """The namespace and the metaclass are not attributes of ``declared_values`` any more."""
    for removed in _REMOVED_NAMES:
        assert not hasattr(declared_values, removed), f"{removed} still exists"


def test_no_file_names_the_removed_machinery() -> None:
    """No module under ``packages/`` or ``examples/`` mentions the removed names."""
    own_path = Path(__file__).resolve()
    offenders = [
        str(path.relative_to(_REPOSITORY_ROOT))
        for root in _SCANNED_ROOTS
        for path in (_REPOSITORY_ROOT / root).rglob("*.py")
        if "__pycache__" not in path.parts and path.resolve() != own_path
        for name in _REMOVED_NAMES
        if name in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []
