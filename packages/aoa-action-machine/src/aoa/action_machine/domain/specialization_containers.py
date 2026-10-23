# packages/aoa-action-machine/src/aoa/action_machine/domain/specialization_containers.py
"""
Specialization containers — a declared choice and its optionally loaded data.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A head stores the information common to an object; an alternative stores what is
specific to one of its kinds. ``Specialization[Alternatives, Dictionary]`` links
the head to those details. ``Generalization[Head]`` points back to the common data.
These relationships do not create tables or Python inheritance between the classes.

The dictionary is the vocabulary. On each alternative's reverse field,
``Classifier(variant=EditionKindEnumEntity.FIRST)`` identifies
one declared value. The head needs no separate classifier field or marker.

A specialization holds an identifier, a declared dictionary value and an optional
loaded entity. Dictionary validation resolves reference objects by code and refuses
bare strings, unknown codes and fabricated instances. When an entity is supplied,
its declared value must be the same object as the selected variant. Containers are
frozen and never load data. Identifier equality remains the resource's responsibility.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    stored code -> resource calls Dictionary.by_code(code) -> declared value
                                                               |
    loaded details or None ------------------------------------+
                                                               v
                         Specialization[Alternatives, Dictionary]
                                   id, variant, entity

``entity=None`` means no details were supplied. A head field explicitly typed as
``Specialization[Alternatives, Dictionary] | None`` can instead have no selection.
Model build validates the dictionary and alternatives independently of loading.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _declared_value(entity_cls: type[Any]) -> Any:
    """Return the value the class declares, imported late to keep the module cycle closed."""
    # pylint: disable-next=import-outside-toplevel  # the import would close a cycle at module load
    from aoa.action_machine.domain.spec_entity import declared_value

    return declared_value(entity_cls)


class Specialization[T, D](BaseModel):
    """
    AI-CORE-BEGIN
        ROLE: Head-side container: a link to one of the declared alternatives.
        CONTRACT: ``id`` and ``variant`` are always present; ``entity`` holds the hydrated row
            when one was loaded. Subscript with the alternative class or union and its dictionary.
        INVARIANTS: A value assigned to ``entity`` must be one of the classes in the type
            argument and must declare the same value as ``variant``; the container is frozen.
        AI-CORE-END
    """

    model_config = ConfigDict(frozen=True)

    id: Any = Field(description="Identifier of the related extension row")
    variant: D = Field(description="The declared value that selects this alternative")
    entity: T | None = Field(default=None, repr=False, description="The hydrated extension row")

    @model_validator(mode="after")
    def _check_pairing(self) -> Self:
        """Refuse a value that disagrees with the class of the hydrated row."""
        if self.entity is None:
            return self
        declared = _declared_value(type(self.entity))
        if declared is None:
            return self
        declared_code = getattr(declared, "code", declared)
        if self.variant is not declared:
            raise ValueError(
                f"variant {getattr(self.variant, 'code', self.variant)!r} does not match "
                f"{type(self.entity).__name__}, which declares {declared_code!r}"
            )
        return self


class Generalization[T](BaseModel):
    """
    AI-CORE-BEGIN
        ROLE: Extension-side container: a link back to the head this row belongs to.
        CONTRACT: ``id`` is always present; ``entity`` holds the hydrated head row when loaded.
            Subscript with the head class.
        INVARIANTS: A value assigned to ``entity`` must be the class in the type argument;
            the container is frozen after construction.
        AI-CORE-END
    """

    model_config = ConfigDict(frozen=True)

    id: Any = Field(description="Identifier of the related head row")
    entity: T | None = Field(default=None, repr=False, description="The hydrated head row")


class Classifier:
    """
    AI-CORE-BEGIN
        ROLE: Marks an extension's reverse field with the dictionary value it is.
        CONTRACT: ``variant`` is one of the head's dictionary values, the object itself; the
            field the marker sits on is the pair, so the marker never restates its name.
        INVARIANTS: ``variant`` is a declared dictionary value; the marker is frozen; it has
            no ``field`` argument and no ``field`` attribute.
        AI-CORE-END
    """

    __slots__ = ("_variant",)

    def __init__(self, variant: Any = None) -> None:
        """
        Args:
            variant: The declared dictionary value this class is.

        Raises:
            TypeError: ``variant`` is not a declared dictionary value.
        """
        if variant is None:
            raise TypeError(
                "Classifier: name a value, not a list of codes — "
                "write Classifier(variant=<Dictionary>.<VALUE>)."
            )
        # pylint: disable-next=import-outside-toplevel  # the import would close a cycle at module load
        from aoa.action_machine.domain.enum_entity import BaseEnumEntity

        if not isinstance(variant, BaseEnumEntity):
            raise TypeError(
                f"Classifier: variant must be a declared dictionary value, "
                f"got {type(variant).__name__}: {variant!r}."
            )

        object.__setattr__(self, "_variant", variant)

    @property
    def variant(self) -> Any:
        """The declared dictionary value this class is."""
        return object.__getattribute__(self, "_variant")

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Classifier is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Classifier is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        return f"Classifier(variant={self.variant!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Classifier):
            return NotImplemented
        return self.variant is other.variant

    def __hash__(self) -> int:
        return hash(("variant", id(self.variant)))
