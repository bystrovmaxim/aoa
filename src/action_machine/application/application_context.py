# src/action_machine/application/application_context.py
"""
Canonical interchange anchor for the logical **application**.

Every ``BaseDomain`` subclass is linked to this vertex via informational
``belongs_to`` edges (see ``ApplicationContextInspector``). The type exists only
as a stable ``class_ref`` / ``node_name`` source for that single graph node.
"""


class ApplicationContext:
    """Marker class for the coordinator ``Application`` facet vertex."""

    __slots__ = ()
