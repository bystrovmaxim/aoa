"""Reproduce dictionary schema and reciprocal-declaration gaps through public APIs.
Run: .venv/bin/python docs/reports/evidence/endpoint_dictionary_boundaries.py
"""

from copy import deepcopy
from typing import Annotated

from jsonschema import Draft202012Validator
from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    Inverse,
    NoInverse,
    value,
)
from aoa.action_machine.intents.entity import entity


class BoundaryDomain(BaseDomain):
    """Group the dictionary boundary reproductions."""

    name = "dictionary-boundaries"
    description = "Dictionary boundaries"


@entity(description="Dictionary", domain=BoundaryDomain)
class CountEnumEntity(BaseEnumEntity):
    """Declare an integer custom property."""

    count: int = Field(description="Count")
    ONE = value(code="one", display_name="One", count=1)


@entity(description="Host", domain=BoundaryDomain)
class HostCoreEntity(BaseCoreEntity):
    """Select one and many members with the same property contract."""

    chosen: Annotated[AssociationOne[CountEnumEntity], NoInverse()] = Field(description="Chosen member")
    choices: Annotated[AssociationMany[CountEnumEntity], NoInverse()] = Field(description="Chosen members")


def schema_gap() -> None:
    """Show that the relationship schema accepts a wrong custom-property type."""
    host = HostCoreEntity(chosen=AssociationOne(id="one"), choices=AssociationMany(ids=("one",)))
    output = host.model_dump(mode="json")
    schema = HostCoreEntity.model_json_schema(mode="serialization")
    Draft202012Validator(schema).validate(output)
    malformed = deepcopy(output)
    malformed["chosen"]["properties"]["count"] = "wrong"
    malformed["choices"][0]["properties"]["count"] = "wrong"
    Draft202012Validator(schema).validate(malformed)
    assert (
        CountEnumEntity.model_json_schema(mode="serialization")["properties"]["properties"]["properties"]["count"][
            "type"
        ]
        == "integer"
    )
    assert schema["properties"]["chosen"]["properties"]["properties"] == {"type": "object"}
    assert schema["properties"]["choices"]["items"]["properties"]["properties"] == {"type": "object"}
    print("Wrong custom-property types accepted by One and Many export schemas (defect)")


def reciprocal_gap() -> None:
    """Show the earlier catalogue-property refusal blocking an explicit reverse."""

    @entity(description="Reverse owner", domain=BoundaryDomain)
    class ReverseOwnerCoreEntity(BaseCoreEntity):
        """Declare the matching forward endpoint before the catalogue exists."""

        reverse: Annotated[AssociationOne["ReverseEnumEntity"], Inverse(field_name="host")] = Field(
            description="Catalogue"
        )

    try:

        @entity(description="Reciprocal dictionary", domain=BoundaryDomain)
        class ReverseEnumEntity(BaseEnumEntity):
            """Attempt an ordinary reverse field on a dictionary value."""

            host: Annotated[AssociationOne[ReverseOwnerCoreEntity], Inverse(field_name="reverse")] = Field(
                description="Host"
            )
            ITEM = value(code="item", display_name="Item", host=AssociationOne(id="host-1"))
    except ValueError as error:
        assert "field 'host' is AssociationOne" in str(error)
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The catalogue property restriction changed; recheck this gap")


def main() -> None:
    """Run the schema and reciprocal-endpoint reproductions."""
    schema_gap()
    reciprocal_gap()


if __name__ == "__main__":
    main()
