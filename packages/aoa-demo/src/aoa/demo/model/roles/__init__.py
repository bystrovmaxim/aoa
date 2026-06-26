# packages/aoa-demo/src/aoa/demo/model/roles/__init__.py
"""Application roles for :mod:`aoa.demo.model` (store, graph, ACL)."""

from aoa.demo.model.roles.editor import EditorRole
from aoa.demo.model.roles.legacy import DeprecatedRole
from aoa.demo.model.roles.viewer import ViewerRole

__all__ = ["DeprecatedRole", "EditorRole", "ViewerRole"]
