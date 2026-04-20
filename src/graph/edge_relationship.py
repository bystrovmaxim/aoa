# src/graph/edge_relationship.py
"""
ArchiMate-style **relationship** descriptors for interchange edges.

Each relationship is a small immutable object: **how the line attaches at the source**,
**how at the target**, and **solid vs dashed line**. Renderers map
:class:`EndpointAttachment` and :class:`LineStyle` to concrete graphics.

Concrete subclasses (one per ArchiMate / UML connector kind) set the three values in code;
module-level singletons (``ASSOCIATION``, ``FLOW``, …) preserve stable identity for equality
and match prior enum-style usage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class EndpointAttachment(StrEnum):
    """Decoration at one end of a connector (ArchiMate / UML primitives + none)."""

    NONE = "none"
    OPEN_ARROW = "open_arrow"
    HOLLOW_DIAMOND = "hollow_diamond"
    FILLED_DIAMOND = "filled_diamond"
    HOLLOW_TRIANGLE = "hollow_triangle"
    FILLED_TRIANGLE = "filled_triangle"


class LineStyle(StrEnum):
    """Line stroke for the connector between the two endpoints."""

    SOLID = "solid"
    DASHED = "dashed"


class EdgeRelationship(ABC):
    """
    Abstract interchange edge relationship (docking at source, at target, line style).

    Subclasses are frozen dataclasses with fixed ``source_attachment``, ``target_attachment``,
    and ``line_style``. Use module singletons (``ASSOCIATION``, …) for stable references.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def source_attachment(self) -> EndpointAttachment:
        """Graphic at the **source** node end of the edge."""

    @property
    @abstractmethod
    def target_attachment(self) -> EndpointAttachment:
        """Graphic at the **target** node end of the edge."""

    @property
    @abstractmethod
    def line_style(self) -> LineStyle:
        """Solid or dashed connector between the two ends."""

    @property
    @abstractmethod
    def archimate_name(self) -> str:
        """Stable ArchiMate-style label (matches former ``StrEnum`` string values)."""

    def __str__(self) -> str:
        """Same string as former ``StrEnum`` values (e.g. ``\"Association\"``)."""
        return self.archimate_name


@dataclass(frozen=True, slots=True)
class Association(EdgeRelationship):
    """Undirected association with navigability toward the target (open arrow)."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.OPEN_ARROW

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Association"


@dataclass(frozen=True, slots=True)
class Aggregation(EdgeRelationship):
    """Shared aggregation: hollow diamond at the source (aggregate) end."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.HOLLOW_DIAMOND

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Aggregation"


@dataclass(frozen=True, slots=True)
class Assignment(EdgeRelationship):
    """Assignment of meaning or responsibility: directed solid link to target."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.OPEN_ARROW

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Assignment"


@dataclass(frozen=True, slots=True)
class Composition(EdgeRelationship):
    """Composite aggregation: filled diamond at the source (composite) end."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.FILLED_DIAMOND

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Composition"


@dataclass(frozen=True, slots=True)
class Flow(EdgeRelationship):
    """Transfer, sequence, or causal flow: solid arrow at target."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.OPEN_ARROW

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Flow"


@dataclass(frozen=True, slots=True)
class Generalization(EdgeRelationship):
    """UML/ArchiMate generalization: hollow triangle toward the generalized (target) end."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.HOLLOW_TRIANGLE

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Generalization"


@dataclass(frozen=True, slots=True)
class Influence(EdgeRelationship):
    """Influence without strict semantics: dashed arrow at target."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.OPEN_ARROW

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.DASHED

    @property
    def archimate_name(self) -> str:
        return "Influence"


@dataclass(frozen=True, slots=True)
class Realization(EdgeRelationship):
    """Realizes a more abstract element: dashed line, hollow triangle at target."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.HOLLOW_TRIANGLE

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.DASHED

    @property
    def archimate_name(self) -> str:
        return "Realization"


@dataclass(frozen=True, slots=True)
class Serving(EdgeRelationship):
    """Serving dependency: solid arrow at target (served end)."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.OPEN_ARROW

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Serving"


@dataclass(frozen=True, slots=True)
class Specialization(EdgeRelationship):
    """Specialization toward a more specific classifier: filled triangle at source."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.FILLED_TRIANGLE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Specialization"


@dataclass(frozen=True, slots=True)
class Triggering(EdgeRelationship):
    """Event or temporal trigger: solid arrow at target."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.OPEN_ARROW

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.SOLID

    @property
    def archimate_name(self) -> str:
        return "Triggering"


@dataclass(frozen=True, slots=True)
class Access(EdgeRelationship):
    """Access to meaning or data: dashed navigability toward target."""

    @property
    def source_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.NONE

    @property
    def target_attachment(self) -> EndpointAttachment:
        return EndpointAttachment.OPEN_ARROW

    @property
    def line_style(self) -> LineStyle:
        return LineStyle.DASHED

    @property
    def archimate_name(self) -> str:
        return "Access"


ASSOCIATION: EdgeRelationship = Association()
AGGREGATION: EdgeRelationship = Aggregation()
ASSIGNMENT: EdgeRelationship = Assignment()
COMPOSITION: EdgeRelationship = Composition()
FLOW: EdgeRelationship = Flow()
GENERALIZATION: EdgeRelationship = Generalization()
INFLUENCE: EdgeRelationship = Influence()
REALIZATION: EdgeRelationship = Realization()
SERVING: EdgeRelationship = Serving()
SPECIALIZATION: EdgeRelationship = Specialization()
TRIGGERING: EdgeRelationship = Triggering()
ACCESS: EdgeRelationship = Access()
