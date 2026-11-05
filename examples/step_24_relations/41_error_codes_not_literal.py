"""Classifier accepts a value, not a list.

Pass a list of code strings to Classifier.
Run: uv run python examples/step_24_relations/41_error_codes_not_literal.py
"""

from aoa.action_machine.domain import BaseDomain, BaseEnumEntity, Classifier, value
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class MediaDomain(BaseDomain):
    """Group the declarations this experiment needs."""

    name = "media"
    description = "Media"


@meta(description="Stores the media entities", domain=MediaDomain)
class MediaStorage(BaseStorage):
    """Hold the media entities."""


@entity(description="Media kind", resource=MediaStorage)
class MediaKindEnumEntity(BaseEnumEntity):
    """Declare the codes an axis borrows, in the class body."""

    VINYL = value(code="vinyl", display_name="Vinyl")


def main() -> None:
    """Run this one learning experiment."""
    try:
        Classifier(["first"])  # a list is not a value, and the marker no longer names a field
    except TypeError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The invalid marker was accepted")

    marker = Classifier(variant=MediaKindEnumEntity.VINYL)
    print("A dictionary value, not a code list:", marker.variant.code)
    print("Declared:", MediaKindEnumEntity.codes())


if __name__ == "__main__":
    main()
