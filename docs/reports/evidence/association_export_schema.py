"""Reproduce the missing typed property schema on a dictionary association.
Run: .venv/bin/python docs/reports/evidence/association_export_schema.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class SchemaDomain(BaseDomain):
    """Group the schema reproduction."""

    name = "schema"
    description = "Association schema reproduction"


@entity(description="Dictionary", domain=SchemaDomain)
class NumberEnumEntity(BaseEnumEntity):
    """Declare a typed custom property."""

    count: int = Field(description="Count")
    ONE = value(code="one", display_name="One", count=1)


@entity(description="Host", domain=SchemaDomain)
class HostCoreEntity(BaseCoreEntity):
    """Select the dictionary through an association."""

    selection: Annotated[AssociationOne[NumberEnumEntity], NoInverse()] = Field(description="Selection")


def main() -> None:
    """Inspect actual export and serialization schemas."""
    host = HostCoreEntity(selection=AssociationOne(id="one"))
    print("Export:", host.model_dump(mode="json"))
    association = HostCoreEntity.model_json_schema(mode="serialization")["properties"]["selection"]["properties"][
        "properties"
    ]
    standalone = NumberEnumEntity.model_json_schema(mode="serialization")["properties"]["properties"]
    assert association == {"type": "object"}
    assert standalone["properties"]["count"]["type"] == "integer"
    print("Association properties schema:", association)
    print("Standalone count type:", standalone["properties"]["count"]["type"])


if __name__ == "__main__":
    main()
