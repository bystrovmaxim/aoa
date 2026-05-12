# packages/aoa-examples/src/aoa/examples/model/roles/__init__.py
"""Application roles for :mod:`aoa.examples.model` (store, graph, ACL)."""

from aoa.examples.model.roles.editor import EditorRole
from aoa.examples.model.roles.legacy import DeprecatedRole
from aoa.examples.model.roles.viewer import ViewerRole

__all__ = ["DeprecatedRole", "EditorRole", "ViewerRole"]
