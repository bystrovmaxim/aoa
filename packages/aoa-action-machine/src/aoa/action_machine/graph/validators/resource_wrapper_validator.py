# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/resource_wrapper_validator.py
"""
ResourceWrapperValidator — validate wrapper declarations before resource construction.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every resource declares its wrapper through a class method. Model build checks
its descriptor, result kind and name without creating resources or connections.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Graph resource classes -> class-method declarations -> reachable wrappers
                                      |                         |
                                   None ends              visited set ends cycles
"""

from collections.abc import Iterable
from inspect import getattr_static
from typing import Any

from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.resources.base_resource import BaseResource, resource_kind


def validate_resource_wrappers(nodes: Iterable[Any]) -> None:
    """
    Validate every resource and reachable wrapper before runtime.

    AI-CORE-BEGIN
    ROLE: Guard wrapper declarations at model build.
    CONTRACT: Accept class methods returning None or same-kind wrapper classes.
    INVARIANTS: No resource construction; every distinct reachable class is checked once; getter errors propagate.
    AI-CORE-END
    """
    visited: set[type] = set()
    for node in nodes:
        resource = node.node_obj
        if not isinstance(resource, type) or not issubclass(resource, BaseResource):
            continue
        while resource not in visited:
            visited.add(resource)
            descriptor = getattr_static(resource, "get_wrapper_class")
            if not isinstance(descriptor, classmethod):
                raise DeclarationStructureError(f"{resource.__name__}.get_wrapper_class must be a class method.")
            wrapper = resource.get_wrapper_class()
            if wrapper is None:
                break
            if not isinstance(wrapper, type) or not issubclass(wrapper, BaseResource):
                raise DeclarationStructureError(f"{resource.__name__}.get_wrapper_class must return a resource class or None.")
            kind = resource_kind(resource)
            if resource_kind(wrapper) != kind:
                raise DeclarationStructureError(
                    f"{resource.__name__}.get_wrapper_class names '{wrapper.__name__}': a wrapper must have the same resource kind."
                )
            suffix = f"{kind}Wrapper"
            if not wrapper.__name__.endswith(suffix):
                raise NamingSuffixError(
                    f"{resource.__name__}.get_wrapper_class names '{wrapper.__name__}', which lacks the '{suffix}' suffix."
                )
            resource = wrapper
