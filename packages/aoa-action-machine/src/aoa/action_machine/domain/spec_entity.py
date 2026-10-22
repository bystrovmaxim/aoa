# packages/aoa-action-machine/src/aoa/action_machine/domain/spec_entity.py
"""
BaseSpecEntity — the base class of the spec kind: variant-specific data of the same object.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the six base classes a real entity inherits from. It states what an
instance represents in the domain, declares its kind as one word, and holds its
descendants to the kind's name suffix. The other five are declared beside it in this
package, one file each, and the entity base holds the hierarchy rules.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Organisation-specific counterparty data", domain=ShopDomain)
    class OrganisationSpecEntity(BaseSpecEntity):
        id: str = Field(description="The head counterparty identifier")
        registration: str = Field(description="Registration number")

    This field excerpt omits the paired Specialization/Generalization declaration;
    see examples/step_20_entity/06_specialization.py for the complete model.
"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.specialization_containers import Classifier
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


def declared_value(entity_cls: type[Any]) -> Any:
    """
    Return the dictionary value ``entity_cls`` declares, read from its own marker.

    Read on demand rather than stored at class creation: an extension declared before its
    head is a forward reference, so the field metadata only exists after ``model_rebuild``.
    Reading the marker each time keeps the answer true whichever order the module declared
    its classes in.
    """
    for info in getattr(entity_cls, "model_fields", {}).values():
        for meta in info.metadata:
            if isinstance(meta, Classifier) and meta.variant is not None:
                return meta.variant
    return None


@exclude_graph_model
class BaseSpecEntity(BaseEntity, ABC):
    """
    Variant-specific data sharing the identity of its general entity.

    AI-CORE-BEGIN
        ROLE: What is specific to one kind of a more general object — organisation data on a counterparty head, the head holding the common data and the identity.
        CONTRACT: Exactly one Generalization points to that head, and the classifier code matches the variant the head declares. It may carry a Lifecycle for its own data.
        INVARIANTS: No identity of its own beyond the head's; a head has at most one instance of a given specialization; cannot head another Specialization and cannot be a Composite target.
    AI-CORE-END
    """

    declared_variant: ClassVar[Any] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("SpecEntity")

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Expose the declared value this extension's own marker names."""
        super().__pydantic_init_subclass__(**kwargs)
        for info in cls.model_fields.values():
            for meta in info.metadata:
                if isinstance(meta, Classifier) and meta.variant is not None:
                    cls.declared_variant = meta.variant
                    return
