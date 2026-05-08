# src/graph/edge_relationship.py
"""
ArchiMate-style **relationship** descriptors for interchange edges.

Each relationship is a small immutable object: **how the line attaches at the source**,
**how at the target**, and **solid vs dashed line**. Renderers map
:class:`EndpointAttachment` and :class:`LineStyle` to concrete graphics.

Concrete subclasses (one per ArchiMate / UML connector kind) set the three values in code;
module-level singletons (``ASSOCIATION``, ``FLOW``, …) preserve stable identity for equality
and match prior enum-style usage.

Relationship reference (graphics + semantics)
═══════════════════════════════════════════════════════════════════════════════

**Association** — source ``NONE``, target ``OPEN_ARROW``, line ``SOLID``. Peer conceptual
link; the arrow marks **navigability / reference direction** in the interchange graph, not
that the source classifier is “above” the target. Use for schema-style links such as
``Action → Params`` and ``Action → Result``, or conceptual peers such as ``Order`` and
``Customer`` when one navigable role is drawn.

**Aggregation** — source ``HOLLOW_DIAMOND``, target ``NONE``, line ``SOLID``. Shared
aggregation: the whole groups parts that can outlive it. Example: a **Domain** grouping
**Actions** conceptually while actions remain reusable elsewhere.

**Assignment** — source ``NONE``, target ``OPEN_ARROW``, line ``SOLID``. Allocates meaning
or responsibility to the target. Examples: **Action → Role**; attaching a **Checker** to
an aspect field (when not modeled with a dedicated ``CHECKS_ASPECT``-style link).

**Composition** — source ``FILLED_DIAMOND``, target ``NONE``, line ``SOLID``. Strong
composition: the composite owns parts that do not stand alone in that relationship.
Examples: **Action → Aspect**, **Action → Error handler**, **Entity → Lifecycle**.

**Flow** — source ``NONE``, target ``OPEN_ARROW``, line ``SOLID``. Control, data, or
temporal sequence along the edge direction. Examples: hand-off between **aspects** in a
pipeline; **Action → Params / Result** when the edge denotes typed schema flow in the
interchange layer; data movement between **resources** (e.g. ``@connection``).

**Generalization** — source ``NONE``, target ``HOLLOW_TRIANGLE``, line ``SOLID``. The
**source** specializes the **target** (more specific → more general). Examples: role
hierarchy (**EditorRole → ViewerRole**); hypothetical domain specialization; **concrete
Action → BaseAction**.

**Realization** — source ``NONE``, target ``HOLLOW_TRIANGLE``, line ``DASHED``. The source
implements the abstract target. Examples: **Action → specification** artifact; **Sql
connection manager → Postgres connection manager**.

**Serving** — source ``NONE``, target ``OPEN_ARROW``, line ``SOLID``. The target serves the
source. Examples: **Action → @depends** targets; **Action → Resource manager**.

**Specialization** — source ``FILLED_TRIANGLE``, target ``NONE``, line ``SOLID``. Same
specialization story as generalization but with the triangle on the **specific** end;
prefer **Generalization** unless tooling requires this direction explicitly.

**Triggering** — source ``NONE``, target ``OPEN_ARROW``, line ``SOLID``. Event-like or
temporal trigger toward the target. Examples: **Compensator → Aspect**; **Error handler →
Aspect**.

**Access** — source ``NONE``, target ``OPEN_ARROW``, line ``DASHED``. Read access, query,
or light coupling to data or meaning (no ownership). Examples: **Checker → Aspect**
(validation reads aspect output); **Plugin → Action** (observation); **Aspect → Context
field** via ``@context_requires``; **Entity → Field**.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class EndpointAttachment(StrEnum):
    """
    Decoration at one end of a connector (ArchiMate / UML primitives + none).

    Renderers map each member to a concrete cap or arrowhead at that endpoint.
    """

    NONE = "none"
    OPEN_ARROW = "open_arrow"
    HOLLOW_DIAMOND = "hollow_diamond"
    FILLED_DIAMOND = "filled_diamond"
    HOLLOW_TRIANGLE = "hollow_triangle"
    FILLED_TRIANGLE = "filled_triangle"


class LineStyle(StrEnum):
    """
    Line stroke between the two endpoints.

    ``SOLID`` reads as structural or primary dependency; ``DASHED`` as auxiliary,
    influence, or access.
    """

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
    """
    **Graphics:** ``source = NONE``, ``target = OPEN_ARROW``, ``line = SOLID``.

    **Semantics:** A **peer** association between classifiers. The open arrow encodes
    **navigability / interchange direction**, not dominance of source over target—both ends
    remain conceptually equal unless another relationship says otherwise.

    **When to use:** Stable conceptual links where you still need a single directed edge in
    the graph API (e.g. schema endpoints). Typical interchange uses include **Action →
    Params**, **Action → Result**, and conceptual peers such as **Order** and **Customer**
    when one navigable reference is drawn.
    """

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
    """
    **Graphics:** ``source = HOLLOW_DIAMOND``, ``target = NONE``, ``line = SOLID``.

    **Semantics:** Shared aggregation—the aggregate groups parts that **may exist outside**
    that grouping (weak ownership).

    **When to use:** Whole/part language without lifecycle ownership. Examples: a **Domain**
    aggregating **Actions** while actions remain reusable; **Team → Member** when members
    are not strictly owned.
    """

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
    """
    **Graphics:** ``source = NONE``, ``target = OPEN_ARROW``, ``line = SOLID``.

    **Semantics:** Assignment of responsibility, role, or interpreted meaning to the target.

    **When to use:** **Action → Role**; binding a **Checker** to a specific aspect field when
    you do not model a dedicated ``CHECKS_ASPECT`` (or similar) edge type.
    """

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
    """
    **Graphics:** ``source = FILLED_DIAMOND``, ``target = NONE``, ``line = SOLID``.

    **Semantics:** Strong composition—the composite **owns** the part for the lifetime of
    that relationship; parts are not modeled as independent in that contract.

    **When to use:** **Action → Aspect**, **Action → Error handler**, **Entity → Lifecycle**
    when the child does not make sense without the parent in the product model.
    """

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
    """
    **Graphics:** ``source = NONE``, ``target = OPEN_ARROW``, ``line = SOLID``.

    **Semantics:** Transfer of control or data, or a **temporal / causal** ordering along
    the edge direction (pipeline semantics).

    **When to use:** **Aspect → Aspect** sequencing; **Action → Params / Result** when the
    edge denotes typed schema or execution flow in the interchange layer; data movement
    between **resources** (e.g. ``@connection``).
    """

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
    """
    **Graphics:** ``source = NONE``, ``target = HOLLOW_TRIANGLE``, ``line = SOLID``.

    **Semantics:** Generalization / inheritance: the **source** is the more **specific**
    classifier, the **target** the more **general** (UML arrow points to the general end).

    **When to use:** **EditorRole → ViewerRole**; a hypothetical domain hierarchy; **concrete
    Action → BaseAction**.
    """

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
class Realization(EdgeRelationship):
    """
    **Graphics:** ``source = NONE``, ``target = HOLLOW_TRIANGLE``, ``line = DASHED``.

    **Semantics:** Realization—the source **implements** or **materializes** the abstract
    target (interface, contract, or specification).

    **When to use:** **Action → specification** artifact when modeled separately; **SQL
    connection manager → Postgres connection manager** for implementation variants.
    """

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
    """
    **Graphics:** ``source = NONE``, ``target = OPEN_ARROW``, ``line = SOLID``.

    **Semantics:** Serving—the target **provides a service** consumed by the source.

    **When to use:** **Action → @depends** targets; **Action → Resource manager** when the
    manager supplies infrastructure the action needs.
    """

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
    """
    **Graphics:** ``source = FILLED_TRIANGLE``, ``target = NONE``, ``line = SOLID``.

    **Semantics:** Same specialization story as :class:`Generalization`, but the triangle sits
    on the **specific** end instead of the hollow triangle on the **general** end.

    **When to use:** Rarely—prefer :class:`Generalization` unless a notation or exporter
    requires this reversed decoration explicitly.
    """

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
    """
    **Graphics:** ``source = NONE``, ``target = OPEN_ARROW``, ``line = SOLID``.

    **Semantics:** Event-like or temporal **trigger** toward the target (cause activates the
    pointed element).

    **When to use:** **Compensator → Aspect** after failure; **Error handler → Aspect** when
    the handler is tied to a triggering aspect.
    """

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
    """
    **Graphics:** ``source = NONE``, ``target = OPEN_ARROW``, ``line = DASHED``.

    **Semantics:** Access to data or meaning (read / query), or light coupling without
    ownership—lighter than solid flow or composition.

    **When to use:** **Checker → Aspect** (validation reads aspect output); **Plugin → Action**
    when the plugin observes without owning; **Aspect → Context field** via
    ``@context_requires``; **Entity → Field** when modeling field-level reads.
    """

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
REALIZATION: EdgeRelationship = Realization()
SERVING: EdgeRelationship = Serving()
SPECIALIZATION: EdgeRelationship = Specialization()
TRIGGERING: EdgeRelationship = Triggering()
ACCESS: EdgeRelationship = Access()
