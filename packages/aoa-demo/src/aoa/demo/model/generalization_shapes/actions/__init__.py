# packages/aoa-demo/src/aoa/demo/model/generalization_shapes/actions/__init__.py
"""Generalization action fixtures — parent and children drawn as parent_action edges."""

from aoa.demo.model.generalization_shapes.actions.generalization_actions import (
    GeneralizationFirstChildAction,
    GeneralizationParentAction,
    GeneralizationSecondChildAction,
)

__all__ = [
    "GeneralizationFirstChildAction",
    "GeneralizationParentAction",
    "GeneralizationSecondChildAction",
]
