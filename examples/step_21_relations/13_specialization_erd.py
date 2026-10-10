"""Producing the Maxitor diagram data.

How are three alternative edges represented in the ERD data?
Run from the repository root:
    uv run python examples/step_21_relations/13_specialization_erd.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Classifier, Generalization, Inverse, Rel, Specialization
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="Pressing identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressEntity(BaseEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="Pressing identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["repress"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressEntity(BaseEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="Pressing identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["test"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


for model in (VinylRecordEntity, FirstPressEntity, RepressEntity, TestPressEntity):
    model.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    import json
    from pathlib import Path

    from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
    from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

    machine = ActionProductMachine(loggers=[])
    graph = json.loads(machine.graph_coordinator.to_json())
    store = DuckDBGraphResource.build_from_json(graph)
    domain_id = next(node.node_id for node in machine.graph_coordinator.get_all_nodes() if node.label == "MusicDomain")
    diagram = ListEntitiesAction._slice_payload(store, domain_id, include_neighbors=False)
    head = next(item for item in diagram["entities"] if item["label"] == "VinylRecordEntity")
    field = next(item for item in head["fields"] if item["name"] == "pressing (by media)")
    print(field["name"])
    print(field["type"])
    print("Groups:", len(diagram["groups"]))
    print("Alternatives:", len(diagram["groups"][0]["members"]))
    print("Group links:", sum(item.get("relationship_kind") == "specialization" for item in diagram["relations"]))
    output = Path("examples/step_21_relations/02_specialization_erd.json")
    output.write_text(json.dumps(diagram, indent=2) + "\n")
    print("Saved:", output.as_posix())


if __name__ == "__main__":
    main()
