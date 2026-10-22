"""A code list is not how an axis is classified.

What does the marker check before any model is built, and what replaced the code list?
Run from the repository root:
    uv run python examples/step_21_relations/41_error_codes_not_literal.py
"""

from aoa.action_machine.domain import BaseDomain, BaseEnumEntity, Classifier
from aoa.action_machine.intents.entity import entity


class MediaDomain(BaseDomain):
    """Group the declarations this experiment needs."""

    name = "media"
    description = "Media"


@entity(description="Media kind", domain=MediaDomain)
class MediaKindEnumEntity(BaseEnumEntity):
    """Declare the codes an axis borrows, in the class body."""

    VINYL = MediaKindEnumEntity(code="vinyl", display_name="Vinyl")  # noqa: F821


def main() -> None:
    """Run this one learning experiment."""
    try:
        Classifier("media", ["first"])  # a list is not a value
    except TypeError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The invalid marker was accepted")

    marker = Classifier(field="record", variant=MediaKindEnumEntity.VINYL)
    print("A dictionary value, not a code list:", marker.variant.code)
    print("Declared:", MediaKindEnumEntity.codes())


if __name__ == "__main__":
    main()
