"""Two entities form a specialization cycle.

Can two individually consistent relationships form a cycle?
Run from the repository root:
    uv run python examples/step_21_relations/37_error_cycle.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import (
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class MusicDomain(BaseDomain):
    """Group the cycle experiment."""

    name = "music"
    description = "Cycle experiment"


@entity(description="First level", domain=MusicDomain)
class ASpecEntity(BaseSpecEntity):
    """Declare the first level of detail."""

    id: str = Field(description="Identifier")
    kind: str = Field(description="Detail code")
    detail: Annotated[Specialization[BSpecEntity], Classifier("kind", Literal["b"]), Inverse(field_name="back")] = Rel(
        description="Next level"
    )
    back: Annotated[Generalization[BSpecEntity], Classifier("back", Literal["a"]), Inverse(BSpecEntity, "detail")] = Rel(
        description="Return to B"
    )


@entity(description="Second level", domain=MusicDomain)
class BSpecEntity(BaseSpecEntity):
    """Declare the second level of detail."""

    id: str = Field(description="Identifier")
    kind: str = Field(description="Detail code")
    back: Annotated[Generalization[ASpecEntity], Classifier("back", Literal["b"]), Inverse(ASpecEntity, "detail")] = Rel(
        description="Return to A"
    )
    detail: Annotated[Specialization[ASpecEntity], Classifier("kind", Literal["a"]), Inverse(field_name="back")] = Rel(
        description="Next level"
    )


ASpecEntity.model_rebuild()
BSpecEntity.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
    from aoa.action_machine.graph.validators.entity_specialization_validator import validate_entity_specializations

    try:
        validate_entity_specializations()
    except SpecializationDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The broken declaration was accepted")


if __name__ == "__main__":
    main()
