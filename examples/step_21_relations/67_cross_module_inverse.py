"""Resolve reciprocal inverse fields after importing independent modules.
Run: .venv/bin/python examples/step_21_relations/67_cross_module_inverse.py
"""

from examples.step_21_relations.inverse_model.offer import OfferCoreEntity
from examples.step_21_relations.inverse_model.region import RegionCoreEntity

from aoa.action_machine.domain import AssociationMany
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses


def main() -> None:
    """Rebuild both endpoints before validating or constructing them."""
    namespace = {"OfferCoreEntity": OfferCoreEntity, "RegionCoreEntity": RegionCoreEntity}
    OfferCoreEntity.model_rebuild(_types_namespace=namespace)
    RegionCoreEntity.model_rebuild(_types_namespace=namespace)
    validate_entity_fields([OfferCoreEntity, RegionCoreEntity])
    validate_entity_inverses([OfferCoreEntity, RegionCoreEntity])
    offer = OfferCoreEntity(regions=AssociationMany(ids=("region-1",)))
    assert offer.regions.ids == ("region-1",)
    print("Cross-module reciprocal pair: accepted")


if __name__ == "__main__":
    main()
