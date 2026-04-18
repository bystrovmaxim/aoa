# src/maxitor/samples/roles/__init__.py
"""Роли приложения для примеров в :mod:`maxitor.samples` (магазин, граф, ACL)."""

from maxitor.samples.roles.editor import EditorRole
from maxitor.samples.roles.legacy import DeprecatedRole
from maxitor.samples.roles.viewer import ViewerRole

__all__ = ["DeprecatedRole", "EditorRole", "ViewerRole"]
