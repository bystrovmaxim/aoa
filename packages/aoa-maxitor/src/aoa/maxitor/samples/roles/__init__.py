# packages/aoa-maxitor/src/aoa/maxitor/samples/roles/__init__.py
"""Application roles for :mod:`aoa.maxitor.samples` (store, graph, ACL)."""

from aoa.maxitor.samples.roles.editor import EditorRole
from aoa.maxitor.samples.roles.legacy import DeprecatedRole
from aoa.maxitor.samples.roles.viewer import ViewerRole

__all__ = ["DeprecatedRole", "EditorRole", "ViewerRole"]
