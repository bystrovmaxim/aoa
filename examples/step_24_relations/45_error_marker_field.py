"""Classifier names a value, not a field.

The marker sits on the extension's reverse field, so the field is already known: passing a
field name is an unknown keyword and the marker refuses it.
Run: uv run python examples/step_24_relations/45_error_marker_field.py
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain, BaseEnumEntity, Classifier, value
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@meta(description="Where MusicStorage keeps its rows")
class MusicDataSource(InMemoryDataSource):
    """The store MusicStorage works with."""


@meta(description="Stores the music entities", domain=MusicDomain)
class MusicStorage(BaseStorage[MusicDataSource]):
    """Hold the music entities."""


@entity(description="Kind of VinylRecordCoreEntity", resource=MusicStorage)
class VinylRecordKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    FIRST = value(code="first", display_name="First")


def main() -> None:
    """Run this one learning experiment."""
    try:
        Classifier(field="record", variant=VinylRecordKindEnumEntity.FIRST)  # type: ignore[call-arg]
    except TypeError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The invalid marker was accepted")

    marker = Classifier(variant=VinylRecordKindEnumEntity.FIRST)
    print("A value, and no field name:", marker.variant.code, repr(marker))


if __name__ == "__main__":
    main()
