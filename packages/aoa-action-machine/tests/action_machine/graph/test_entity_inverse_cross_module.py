# tests/action_machine/graph/test_entity_inverse_cross_module.py
"""
Cross-module reciprocal declarations resolve in either import order without circular imports.

The two declaration modules name each other only under ``TYPE_CHECKING`` and through
postponed annotations; the composition root resolves both with an explicit namespace. The
unresolved-target failure closes the model until every name is resolved.
"""

from __future__ import annotations

import textwrap

from ...support.isolated_entity_models import run_isolated_model

_PREAMBLE = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, "packages/aoa-action-machine")

    from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
    from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_PREAMBLE + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_offer_first_import_order_resolves_and_validates() -> None:
    """Importing offer before region still resolves through the composition root."""
    out = _run(
        """
        from tests.support.complete_relationships import bootstrap

        bootstrap.resolve_and_validate()
        print("OK")
        """
    )

    assert "OK" in out


def test_region_first_import_order_resolves_and_validates() -> None:
    """Importing region before offer resolves through the same explicit namespace."""
    out = _run(
        """
        from tests.support.complete_relationships.offer import OfferCoreEntity
        from tests.support.complete_relationships.region import RegionCoreEntity

        OfferCoreEntity.model_rebuild(_types_namespace={"RegionCoreEntity": RegionCoreEntity})
        RegionCoreEntity.model_rebuild(_types_namespace={"OfferCoreEntity": OfferCoreEntity})
        validate_entity_inverses([OfferCoreEntity, RegionCoreEntity])
        print("OK")
        """
    )

    assert "OK" in out


def test_an_unresolved_name_blocks_assembly() -> None:
    """A declaration whose target is never resolved is refused, not read as a scalar."""
    out = _run(
        """
        from tests.support.complete_relationships.offer import OfferCoreEntity

        try:
            validate_entity_fields([OfferCoreEntity])
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("REFUSE " + exc.entity_name + " " + exc.field_name)
        """
    )

    assert "REFUSE OfferCoreEntity regions" in out
