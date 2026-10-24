# tests/action_machine/graph/test_relationship_compatibility_regressions.py
"""
Compatibility regressions: the complete-declaration and inverse changes add no ownership matrix.

FR-010 preserves the existing compatibility and classifier checks and forbids the new
ownership/container-pair matrix. These tests pin that a complete reciprocal declaration
passes for every container pairing, and that the existing field/specialization refusals and
the accepted unchanged-inheritance behavior are retained. Nothing here derives an expected
refusal from the discarded matrix.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from ...support.isolated_entity_models import run_isolated_model

_REPO_ROOT = Path(__file__).resolve().parents[5]

_IMPORTS = textwrap.dedent(
    """
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        AggregateMany,
        AggregateOne,
        AssociationMany,
        AssociationOne,
        BaseCoreEntity,
        BaseDomain,
        CompositeMany,
        CompositeOne,
        Inverse,
        NoInverse,
    )
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
    from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
    from aoa.action_machine.intents.entity import entity


    class CompatDomain(BaseDomain):
        name = "compat"
        description = "Compatibility"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


_CONTAINER_PAIRS = [
    ("CompositeOne", "CompositeOne"),
    ("CompositeMany", "CompositeOne"),
    ("CompositeOne", "AssociationMany"),
    ("AggregateOne", "AggregateOne"),
    ("CompositeOne", "AggregateOne"),
    ("AssociationOne", "AssociationMany"),
]


def _pair_body(container_a: str, container_b: str) -> str:
    return f"""
        @exclude_graph_model
        @entity(description="First", domain=CompatDomain)
        class FirstCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            second: Annotated[{container_a}[SecondCoreEntity], Inverse(field_name="first")] = Field(description="Second")

        @exclude_graph_model
        @entity(description="Second", domain=CompatDomain)
        class SecondCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            first: Annotated[{container_b}[FirstCoreEntity], Inverse(field_name="second")] = Field(description="First")

        FirstCoreEntity.model_rebuild()
        SecondCoreEntity.model_rebuild()
        validate_entity_inverses([FirstCoreEntity, SecondCoreEntity])
        print("ACCEPT")
    """


def test_no_ownership_matrix_is_enforced() -> None:
    """Every container pairing passes the reciprocal check; none is refused by a matrix."""
    for container_a, container_b in _CONTAINER_PAIRS:
        out = _run(_pair_body(container_a, container_b))
        assert "ACCEPT" in out, f"{container_a} <-> {container_b} was refused"


def test_an_unchanged_inherited_pair_keeps_the_base_endpoint() -> None:
    """The accepted unchanged-inheritance behavior is retained."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Item", domain=CompatDomain)
        class ItemCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            owner: Annotated[AssociationOne[BaseHostCoreEntity], Inverse(field_name="items")] = Field(description="Owner")

        @exclude_graph_model
        @entity(description="Base", domain=CompatDomain)
        class BaseHostCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            items: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(description="Items")

        @exclude_graph_model
        @entity(description="Child", domain=CompatDomain)
        class ChildHostCoreEntity(BaseHostCoreEntity):
            extra: str = Field(description="Extra")

        ItemCoreEntity.model_rebuild()
        BaseHostCoreEntity.model_rebuild()
        validate_entity_inverses([BaseHostCoreEntity, ItemCoreEntity, ChildHostCoreEntity])
        print("ACCEPT")
        """
    )

    assert "ACCEPT" in out


def test_the_baseline_docstring_claims_stay_unimplemented() -> None:
    """The recorded docstring-only claims (ownership matrix, inverse existence) stay unbuilt."""
    baseline_path = _REPO_ROOT / "specs/019-complete-annotated-relationships/evidence/compatibility-baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    claims = [check for check in baseline["checks"] if check["category"] == "docstring-claim"]
    assert claims, "the baseline should record the docstring-only claims"

    for claim in claims:
        assert claim["implemented"] is False, claim["id"]
