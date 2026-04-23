# src/action_machine/legacy/interchange_vertex_labels.py
"""
Interchange / facet kind strings (``node_type``) for graph visualization labels.

Kept dependency-free so visualization modules can import labels without pulling
``graph`` (whose package ``__init__`` loads the coordinator).
"""

from __future__ import annotations

from typing import Final

# Structural ``BaseAction`` primary vertex (depends / connection / facets merged here).
ACTION_VERTEX_TYPE: Final[str] = "Action"

# Logical root from :mod:`action_machine.legacy.application_context`; domains ``belongs_to`` here.
APPLICATION_VERTEX_TYPE: Final[str] = "Application"

# Bounded-context domain vertices from application inspector / ``belongs_to`` stubs.
DOMAIN_VERTEX_TYPE: Final[str] = "Domain"

# Entity model vertices from ``EntityIntentInspector`` (``@entity``).
ENTITY_VERTEX_TYPE: Final[str] = "Entity"

# Per-method aspect vertices from ``AspectIntentInspector`` (decorator ``type``).
REGULAR_ASPECT_VERTEX_TYPE: Final[str] = "RegularAspect"
SUMMARY_ASPECT_VERTEX_TYPE: Final[str] = "SummaryAspect"

# Per-result-field checker vertices from ``CheckerIntentInspector``.
CHECKER_VERTEX_TYPE: Final[str] = "Checker"

# Per-method compensator vertices from ``CompensateIntentInspector`` (``@compensate``).
COMPENSATOR_VERTEX_TYPE: Final[str] = "Compensator"

# Class-dependency stubs from ``DependencyIntentInspector`` (non-``BaseAction`` @depends).
SERVICE_VERTEX_TYPE: Final[str] = "Service"
