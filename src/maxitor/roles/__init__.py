# src/maxitor/roles/__init__.py
"""Тестовые роли Maxitor (общие для test_domain и графа)."""

from maxitor.roles.editor import TestEditorRole
from maxitor.roles.legacy import TestLegacyRole
from maxitor.roles.viewer import TestViewerRole

__all__ = ["TestEditorRole", "TestLegacyRole", "TestViewerRole"]
