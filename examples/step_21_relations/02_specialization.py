"""
02_specialization.py — Entity specialization: one head field, N extension tables

A head row often continues in one of several tables, and which one depends on a value
the row itself carries: an event is created, updated, deleted, moved or assigned, and
each of those has its own table with its own columns. A relation as chapter 21 describes
it cannot say this — a field's target type is exactly one, whichever container is chosen.

Specialization declares it. The head's field is parameterised by the union of its
alternatives, and a marker names the field that chooses among them:

    pressed: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(FirstPressEntity, "record"),
    ] = Rel(description="How this record was pressed")

Every extension declares the way back, with its own code:

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")

Both containers are pydantic models, so subscripting one gives a real class: the type
argument is what pydantic validates, and a class the union does not list is refused.
The value carries the identifier, which variant it is, and the hydrated row when one
was loaded — so an id-only link is expressible, and reading a link tells you which
table to go to.

What it prints, run from the repository root:

    1) The axis the framework parsed:
       field        : pressing
       chosen by    : media
       alternatives : ['FirstPressEntity', 'RepressEntity', 'TestPressEntity']
       codes        : ['first', 'repress', 'test']
       code -> class: {'first': 'FirstPressEntity', 'repress': 'RepressEntity', 'test': 'TestPressEntity'}
       paired field : record

    2) A hydrated link:
       pressing         = id='rec-1' variant='first'
       .variant         = first
       .entity          = FirstPressEntity
       .entity.stamper  = 1A

    3) Another alternative in the same field:
       .variant = repress | .entity = RepressEntity

    4) What each row holds:
       rec-1: first press, stamper 1A
       rec-2: repress from 1997, remastered=True

    5) A link without a loaded row:
       built: id='rec-3' variant='test' | .entity: None

    6) What the model refuses:
       a string instead of a row    -> refused
       a class outside the union    -> refused

    7) What the built graph carries for the head:
       entity_specialization   first    -> FirstPressEntity
       entity_specialization   repress  -> RepressEntity
       entity_specialization   test     -> TestPressEntity
       entity_field columns   : ['id', 'title', 'media', 'pressing']

The rendered ERD is `02_specialization_erd.svg`, and its Graphviz source is
`02_specialization_erd.dot` — both beside this file. In the picture the three pressings sit inside
a dashed container labelled `pressing (by media)`, the head is outside it, and one line with a
`vee` arrowhead leads from the head into the container. That container is the part no test can
check, because the client has no test runner, so the picture is the evidence.

The graph the diagram is built from, in DOT — Graphviz source of the ERD above:

    digraph ERD {
      graph [rankdir=LR fontname="Helvetica" bgcolor=transparent pad="0.5" nodesep="0.8" ranksep="1.2"]
      node  [shape=none fontname="Helvetica" fontsize=11 margin="0"]
      edge  [fontname="Helvetica" fontsize=9 color="#94a3b8" arrowsize=0.7]

      subgraph "cluster_ex.VinylRecordEntity:pressing" {
        label="pressing (by media)";
        style="rounded,dashed";
        color="#94a3b8";
        fontsize=10;
        margin=12;
      "ex.FirstPressEntity" [label=…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">stamper</TD><TD BGCOLOR="#ffffff" A…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">year</TD><TD BGCOLOR="#ffffff" ALIG…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">record</TD><TD BGCOLOR="#ffffff" AL…>>]
      "ex.RepressEntity" [label=…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">year</TD><TD BGCOLOR="#ffffff" ALIG…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">remastered</TD><TD BGCOLOR="#ffffff…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">record</TD><TD BGCOLOR="#ffffff" AL…>>]
      "ex.TestPressEntity" [label=…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">approved_by</TD><TD BGCOLOR="#fffff…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">record</TD><TD BGCOLOR="#ffffff" AL…>>]
      }
      "ex.VinylRecordEntity" [label=…>>]
          <TR><TD BGCOLOR="#dbeafe" ALIGN="CENTER" WIDTH="28"><FONT POINT-SIZE="9"><B>FK</B></FONT></TD><TD BGCOLOR="#dbea…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">title</TD><TD BGCOLOR="#ffffff" ALI…>>]
          <TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">media</TD><TD BGCOLOR="#ffffff" ALI…>>]

      "ex.VinylRecordEntity" -> "ex.VinylRecordEntity:pressing" [label="by media" fontsize=9 arrowhead=vee]
    }

Tutorial: ../../docs/tutorials/step-21-relations.md  ·  topic: Entity specialization

Run:
    uv run python examples/step_21_relations/02_specialization.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, ValidationError

from aoa.action_machine.domain import (
    BaseEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class MusicDomain(BaseDomain):
    name = "music"
    description = "A music library"


# ─────────────────────────────────────────────────────────────────────────────
# The extensions. Each holds the continuation of a record row, has its own
# columns, and declares its own code beside the reverse link.
# ─────────────────────────────────────────────────────────────────────────────


@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    id: str = Field(description="Same id as the record")
    stamper: str = Field(description="Stamper code")
    year: int = Field(description="Year of the first press")

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressEntity(BaseEntity):
    id: str = Field(description="Same id as the record")
    year: int = Field(description="Year of the re-press")
    remastered: bool = Field(description="Whether the audio was remastered")

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["repress"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressEntity(BaseEntity):
    id: str = Field(description="Same id as the record")
    approved_by: str = Field(description="Who signed it off")

    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["test"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record this pressing belongs to")


# ─────────────────────────────────────────────────────────────────────────────
# The head. One field, parameterised by the union of its alternatives; the
# codes are declared in the same order as the alternatives are written.
# ─────────────────────────────────────────────────────────────────────────────


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    id: str = Field(description="Record id")
    title: str = Field(description="Album title")
    media: str = Field(description="Classifier: which pressing this is")

    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(FirstPressEntity, "record"),
    ] = Rel(description="How this record was pressed")


for _cls in (FirstPressEntity, RepressEntity, TestPressEntity, VinylRecordEntity):
    _cls.model_rebuild()


def _axis():
    """Return the axis the framework parsed off the head — not a hand-read annotation."""
    axes = EntityIntentResolver.resolve_entity_specializations(VinylRecordEntity)
    assert len(axes) == 1
    return axes[0]


def main() -> None:
    # 1) What the framework reads off the head. This is the parser, not the example:
    #    the graph and the build rules consume exactly these rows.
    axis = _axis()
    print("1) The axis the framework parsed:")
    print("   field        :", axis.field_name)
    print("   chosen by    :", axis.classifier_field)
    print("   alternatives :", [cls.__name__ for cls in axis.alternatives])
    print("   codes        :", list(axis.codes))
    print("   code -> class:", {code: cls.__name__ for code, cls in axis.code_to_target.items()})
    print("   paired field :", axis.inverse_field)

    # 2) Writing a link, reading it back. The value carries the id, the variant
    #    and — when the row was loaded — the row itself.
    first = FirstPressEntity(id="rec-1", stamper="1A", year=1959)
    record = VinylRecordEntity(
        id="rec-1",
        title="Kind of Blue",
        media="first",
        pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
            id="rec-1",
            variant="first",
            entity=first,
        ),
    )
    print()
    print("2) A hydrated link:")
    print("   pressing         =", record.pressing)
    print("   .variant         =", record.pressing.variant)
    print("   .entity          =", type(record.pressing.entity).__name__)
    print("   .entity.stamper  =", record.pressing.entity.stamper)

    # 3) The same field, another alternative — same entity class, other table.
    repress = RepressEntity(id="rec-2", year=1997, remastered=True)
    other = VinylRecordEntity(
        id="rec-2",
        title="Kind of Blue",
        media="repress",
        pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
            id="rec-2",
            variant="repress",
            entity=repress,
        ),
    )
    print()
    print("3) Another alternative in the same field:")
    print("   .variant =", other.pressing.variant, "| .entity =", type(other.pressing.entity).__name__)

    # 4) Reading the variant you got — plain isinstance, no framework call.
    print()
    print("4) What each row holds:")
    for item in (record, other):
        linked = item.pressing.entity
        if isinstance(linked, FirstPressEntity):
            print(f"   {item.id}: first press, stamper {linked.stamper}")
        elif isinstance(linked, RepressEntity):
            print(f"   {item.id}: repress from {linked.year}, remastered={linked.remastered}")
        else:
            print(f"   {item.id}: another pressing")

    # 5) A link whose row is not loaded: the id and the variant are still there.
    print()
    print("5) A link without a loaded row:")
    unloaded = Specialization[FirstPressEntity | RepressEntity | TestPressEntity](id="rec-3", variant="test")
    print("   built:", unloaded, "| .entity:", unloaded.entity)

    # 6) The type argument is what the model enforces.
    print()
    print("6) What the model refuses:")
    for label, value in (
        ("a string instead of a row", "not an entity"),
        ("a class outside the union", VinylRecordEntity(id="rec-9", title="Other", media="first")),
    ):
        try:
            Specialization[FirstPressEntity | RepressEntity | TestPressEntity](id="x", variant="v", entity=value)
            print(f"   {label:28} -> accepted")
        except ValidationError:
            print(f"   {label:28} -> refused")

    # 7) What the graph makes of it: one column for the field, one edge per
    #    alternative. Both are needed — the column says the row has a continuation,
    #    the edges say where that continuation can live.
    machine = ActionProductMachine()
    head_node = next(node for node in machine.graph_coordinator.get_all_nodes() if node.label == "VinylRecordEntity")
    print()
    print("7) What the built graph carries for the head:")
    for edge in head_node.get_all_edges():
        if edge.edge_name == "entity_specialization":
            print(f"   entity_specialization   {edge.properties['classifier_value']:8} -> {edge.target_node_id}")
    columns = [e.target_node.label for e in head_node.get_all_edges() if e.edge_name == "entity_field"]
    print("   entity_field columns   :", [name for name in columns if name is not None])


if __name__ == "__main__":
    main()
