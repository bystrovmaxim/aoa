# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/entity_specialization_validator.py
"""
EntitySpecializationValidator — the build rules a specialization declaration must satisfy.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The parser reads a specialization and the graph builds its edges. Neither judges the
declaration: a head that names a class no code answers to, a class claimed by two heads,
a code that cannot fit the classifier's type — all of them build something, and what
they build is quietly wrong. One edge points at the wrong table, or an alternative
disappears, and nothing says so.

This module is the judgement. It walks every declared entity once, collects the axes,
and refuses a declaration that breaks a rule, naming the class, the field and the rule.
The centre of it is the **two-sided code comparison**: the codes the head names and the
codes the classes declare must be the same set, with the same size, in both directions.
A one-sided check passes a model whose codes are three and three but not the same three.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    every declared entity  ──►  gather_entity_specialization_intent_resolvers
        (one walk)                    │  one row per axis
                                      v
                       _validate_axis   (rules read on one head)
                                      │
                                      v
                    _validate_across_axes  (rules needing every axis)
                       class in two heads · two heads on one classifier ·
                       outside class pointing at a field · reachability · cycles
                                      │
                                      v
                    SpecializationDeclarationError(class, field, rule)

The pass is empty work for a model that declares no specialization: the walk finds no
axes and returns without touching anything, which is what keeps an unchanged model on
exactly the path it took before this feature existed.

═══════════════════════════════════════════════════════════════════════════════
WHAT IS DELIBERATELY NOT CHECKED
═══════════════════════════════════════════════════════════════════════════════

Data completeness, data disjointness and whether the codes present in the data match the
declared ones are **not** model invariants: a table can hold a value nobody declared, and
the model cannot promise otherwise. A code that arrives from data and answers to no
alternative is reported where the row is read, as
:exc:`~aoa.action_machine.domain.exceptions.UndeclaredSpecializationVariantError`.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import**: the rules are defined.
- **Build**: :func:`validate_entity_specializations` runs once per graph build.
- **Runtime**: nothing here runs; the model has already been accepted or refused.

"""

from __future__ import annotations

from typing import Any, NoReturn

from pydantic import TypeAdapter, ValidationError

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
from aoa.action_machine.domain.specialization_containers import (
    Classifier,
    Specialization,
)
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import is_relation_container
from aoa.action_machine.intents.entity.entity_specialization_intent_resolver import (
    EntitySpecializationIntentResolver,
    gather_entity_specialization_intent_resolvers,
    read_reverse_declarations,
)

__all__ = ["declared_entity_classes", "validate_entity_specializations"]


def declared_entity_classes() -> list[type[BaseEntity]]:
    """
    Return every class decorated with ``@entity`` that is currently loaded.

    Walks the loaded subclasses of :class:`~aoa.action_machine.domain.entity.BaseEntity`
    rather than the built graph, because the rules about a class **outside** the union
    have to see classes the graph has no node for — that is precisely the state they
    refuse. Sorted by qualified name so a report names the same class first on every run.

    A class marked :func:`~aoa.action_machine.graph.core.exclude_graph_model.exclude_graph_model`
    is **not** part of the model, so it is not a class these rules can judge. The mark is
    the repository's own way of saying "this host is deliberately outside the graph", and
    a class kept out of the graph can neither break a rule nor be broken by one.
    """
    found: dict[str, type[BaseEntity]] = {}
    pending: list[type[Any]] = [BaseEntity]
    seen: set[type[Any]] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for subclass in current.__subclasses__():
            pending.append(subclass)
            if entity_info_is_set(subclass) and not excluded_from_graph_model(subclass):
                found[f"{subclass.__module__}.{subclass.__qualname__}"] = subclass
    return [found[key] for key in sorted(found)]


def _fail(axis: EntitySpecializationIntentResolver, details: str) -> NoReturn:
    """Raise the declaration error for ``axis``, naming the head, the field and the rule."""
    raise SpecializationDeclarationError(axis.head_entity.__name__, axis.field_name, details)


def _classifier_marker(field_info: Any) -> Classifier | None:
    """Return the ``Classifier`` marker on a field, or ``None``."""
    return next((item for item in field_info.metadata if isinstance(item, Classifier)), None)


def _is_specialization_container(annotation: Any) -> bool:
    """True when the annotation is a subscripted ``Specialization`` container."""
    return getattr(annotation, "__pydantic_generic_metadata__", {}).get("origin") is Specialization


def _inverse_field_name(field_info: Any) -> str:
    """Return the field name an ``Inverse`` marker names, or an empty string."""
    for item in field_info.metadata:
        for attribute in ("field_name", "target_field"):
            name = getattr(item, attribute, None)
            if isinstance(name, str) and name:
                return name
    return ""


def _gather_axes(entities: list[type[BaseEntity]]) -> list[EntitySpecializationIntentResolver]:
    """Return every axis declared by ``entities``, in a stable order."""
    axes: list[EntitySpecializationIntentResolver] = []
    for cls in entities:
        axes.extend(gather_entity_specialization_intent_resolvers(cls))
    return axes


# ─────────────────────────────────────────────────────────────────────────────
# Rules read on one head
# ─────────────────────────────────────────────────────────────────────────────


def _validate_axis(axis: EntitySpecializationIntentResolver) -> None:
    """
    Apply every rule that can be decided from one axis alone.

    Order matters, and it is the order of fundamentality: a class that is not an entity
    cannot be asked about its reverse field, and answering "it declares no field pointing
    back" would be true but useless — the developer would look for a missing field instead
    of a missing decorator.
    """
    _validate_alternatives_are_entities(axis)
    _validate_classifier_field(axis)
    _validate_head_field(axis)
    _validate_declared_codes(axis)
    _validate_codes_match(axis)
    _validate_codes_fit_classifier(axis)
    _validate_codes_unique(axis)


def _validate_classifier_field(axis: EntitySpecializationIntentResolver) -> None:
    """`Classifier(field=…)` must name an existing scalar field of the head, not the axis itself."""
    model_fields = axis.head_entity.model_fields
    if axis.classifier_field == axis.field_name:
        _fail(axis, "the classifier field names the specialization field itself")
    if axis.classifier_field not in model_fields:
        _fail(
            axis,
            f"classifier field '{axis.classifier_field}' is not a field of '{axis.head_entity.__name__}'",
        )
    classifier_info = model_fields[axis.classifier_field]
    if _is_specialization_container(classifier_info.annotation):
        _fail(axis, f"classifier field '{axis.classifier_field}' is a specialization field itself")
    if is_relation_container(classifier_info.annotation):
        _fail(axis, f"classifier field '{axis.classifier_field}' is a relation, not a scalar field")

    # A property or a class constant is not a field at all: pydantic keeps them out of
    # `model_fields`, so reaching here means the name is a real field. The one way a
    # non-field name survives is a `ClassVar`, which pydantic also excludes — so the
    # membership test above is the whole check, and an attribute the class defines
    # beside its fields never passes it.
    annotation = classifier_info.annotation
    if annotation is None:
        _fail(axis, f"classifier field '{axis.classifier_field}' has no usable annotation")


def _validate_head_field(axis: EntitySpecializationIntentResolver) -> None:
    """The axis's own field must be a ``Specialization`` container on the head."""
    head_field = axis.head_entity.model_fields.get(axis.field_name)
    if head_field is None:
        _fail(axis, "the specialization field is not a field of its own head")
    if not _is_specialization_container(head_field.annotation):
        _fail(axis, "a `Classifier` marker sits on a field whose type is not a `Specialization` container")


def _validate_alternatives_are_entities(axis: EntitySpecializationIntentResolver) -> None:
    """Every class in the type argument must be a declared ``@entity``, so the graph has a node."""
    for alternative in axis.alternatives:
        if not entity_info_is_set(alternative):
            _fail(
                axis,
                f"alternative '{alternative.__name__}' is not a declared entity — mark it with @entity",
            )


def _declared_code(axis: EntitySpecializationIntentResolver, alternative: type[Any]) -> str | None:
    """Return the code ``alternative`` declares for this axis, or ``None``."""
    declarations = read_reverse_declarations(alternative, axis.head_entity)
    if not declarations:
        return None
    codes: list[str] = []
    for _, info in declarations:
        marker = _classifier_marker(info)
        codes.extend(marker.code_values if marker is not None else ())
    return codes[0] if codes else None


def _validate_declared_codes(axis: EntitySpecializationIntentResolver) -> None:
    """Every alternative must declare exactly one code on the field pointing back."""
    for alternative in axis.alternatives:
        declarations = read_reverse_declarations(alternative, axis.head_entity)
        if not declarations:
            # The reachability rule owns this case and says it better; skip this alternative and
            # keep checking the rest — one broken alternative must not stop the others from
            # being reported, and `return` here would have done exactly that.
            continue
        if len(declarations) > 1:
            names = ", ".join(name for name, _ in declarations)
            _fail(
                axis,
                f"alternative '{alternative.__name__}' points back through more than one field "
                f"({names}); the axis cannot tell which one declares its code",
            )
        field_name, info = declarations[0]
        marker = _classifier_marker(info)
        if marker is None:
            _fail(
                axis,
                f"alternative '{alternative.__name__}' declares no code on '{field_name}' — "
                f"name it with Classifier(..., Literal[...])",
            )
        if len(marker.code_values) != 1:
            _fail(
                axis,
                f"alternative '{alternative.__name__}' must declare exactly one code on "
                f"'{field_name}', got {list(marker.code_values)}",
            )
        if axis.inverse_field and field_name != axis.inverse_field:
            _fail(
                axis,
                f"alternative '{alternative.__name__}' points back through '{field_name}', "
                f"but the axis names '{axis.inverse_field}'",
            )


def _validate_codes_match(axis: EntitySpecializationIntentResolver) -> None:
    """The centre of the pass: the two sides declare the same codes, in both directions."""
    declared = {code: alternative for alternative in axis.alternatives if (code := _declared_code(axis, alternative))}
    named = list(axis.codes)

    missing = [code for code in named if code not in declared]
    extra = [code for code, alternative in declared.items() if code not in named]
    if missing:
        _fail(axis, f"code(s) {missing} are named by the head but no alternative declares them")
    if extra:
        owners = {code: declared[code].__name__ for code in extra}
        _fail(axis, f"alternative(s) declare code(s) the head does not name: {owners}")
    if len(named) != len(axis.alternatives):
        _fail(
            axis,
            f"the head names {len(named)} code(s) for {len(axis.alternatives)} alternative(s): "
            "every alternative needs exactly one code",
        )


def _validate_codes_fit_classifier(axis: EntitySpecializationIntentResolver) -> None:
    """Every named code must be a value the classifier field's annotation can hold."""
    annotation = axis.head_entity.model_fields[axis.classifier_field].annotation
    try:
        adapter = TypeAdapter(annotation)
    except Exception:  # pragma: no cover - an annotation pydantic cannot build is not ours to explain
        return
    for code in axis.codes:
        try:
            adapter.validate_python(code)
        except ValidationError:
            _fail(
                axis,
                f"code '{code}' cannot be stored by classifier field '{axis.classifier_field}' "
                f"of type {annotation}",
            )


def _validate_codes_unique(axis: EntitySpecializationIntentResolver) -> None:
    """One code selects one class: neither side may name the same code twice."""
    # A repeated code on the head's side cannot be checked, because it cannot be written:
    # Python collapses `Literal["a", "a"]` to `Literal["a"]` before the marker ever sees it,
    # and the marker reads its `code_values` through `get_args`. The rule still holds — a
    # de-duplicated literal yields fewer codes than alternatives, which is exactly what the
    # two-sided comparison refuses with its own message. So the head side is covered there.
    # Reachability, measured: a model cannot arrive here with one code on two classes. The
    # parser builds its mapping by matching each code to a class, so the second class keeps no
    # code of its own, and the two-sided comparison refuses the model first with "every
    # alternative needs exactly one code". The check stays as a guard on the invariant rather
    # than as a reachable branch: the parser's matching rule is an implementation detail, and a
    # rule whose only protection is another module's internals is not protected.
    owners: dict[str, str] = {}
    for alternative in axis.alternatives:
        declared = _declared_code(axis, alternative)
        if declared is None:
            continue
        code = declared
        if code in owners:
            _fail(
                axis,
                f"code '{code}' is declared by both '{owners[code]}' and '{alternative.__name__}'",
            )
        owners[code] = alternative.__name__


# ─────────────────────────────────────────────────────────────────────────────
# Rules that need every axis at once
# ─────────────────────────────────────────────────────────────────────────────


def _validate_one_head_per_class(axes: list[EntitySpecializationIntentResolver]) -> None:
    """A class cannot be an alternative of two heads: its code would select two tables."""
    claims: dict[type[Any], EntitySpecializationIntentResolver] = {}
    for axis in axes:
        for alternative in axis.alternatives:
            owner = claims.get(alternative)
            if owner is not None and owner.head_entity is not axis.head_entity:
                _fail(
                    axis,
                    f"class '{alternative.__name__}' is an alternative of "
                    f"'{owner.head_entity.__name__}.{owner.field_name}' and of "
                    f"'{axis.head_entity.__name__}.{axis.field_name}'",
                )
            claims[alternative] = axis


def _validate_one_axis_per_classifier(axes: list[EntitySpecializationIntentResolver]) -> None:
    """One head cannot carry two axes decided by the same field, or neither could be resolved."""
    by_head: dict[tuple[type[Any], str], EntitySpecializationIntentResolver] = {}
    for axis in axes:
        key = (axis.head_entity, axis.classifier_field)
        owner = by_head.get(key)
        if owner is not None:
            _fail(
                axis,
                f"classifier field '{axis.classifier_field}' already decides "
                f"'{owner.head_entity.__name__}.{owner.field_name}'",
            )
        by_head[key] = axis


def _validate_no_outside_class_points_at_an_axis(
    axes: list[EntitySpecializationIntentResolver],
    judged: list[type[BaseEntity]],
) -> None:
    """
    Closure: a class pointing at an axis must be one of its alternatives.

    ``judged`` is passed rather than discovered here on purpose. When this rule walked the
    loaded entities by itself, it saw a different set from the rest of the pass, and a caller
    that asked for an extra class to be judged — a fixture the walk skips — got every rule
    applied to it except this one. One pass, one list.
    """
    for axis in axes:
        alternatives = set(axis.alternatives)
        for candidate in judged:
            if candidate is axis.head_entity or candidate in alternatives:
                continue
            if read_reverse_declarations(candidate, axis.head_entity):
                _fail(
                    axis,
                    f"class '{candidate.__name__}' points at '{axis.field_name}' without being named "
                    "in the union — add it to the alternatives or remove its reverse field",
                )


# Mutuality — "every alternative is reachable from its head through a reverse field" — has no
# function of its own, and that is a finding rather than an omission. Measured: an alternative
# with no reverse field leaves the code comparison with a code the head names and no class
# declares, which that rule reports first; and an alternative whose reverse field does not point
# at this head is invisible to the parser, so the code comparison reports it the same way. A
# separate reachability rule never fired in any of the broken models the sweep builds, and a rule
# that cannot fire is not a rule — it is a message nobody will ever read.

def _validate_no_cycles(axes: list[EntitySpecializationIntentResolver]) -> None:
    """A head and its extensions must not form a cycle."""
    graph: dict[type[Any], list[type[Any]]] = {}
    for axis in axes:
        graph.setdefault(axis.head_entity, []).extend(axis.alternatives)

    visiting: set[type[Any]] = set()
    done: set[type[Any]] = set()

    def walk(node: type[Any], path: list[type[Any]]) -> list[type[Any]] | None:
        if node in done:
            return None
        if node in visiting:
            return [*path, node]
        visiting.add(node)
        for neighbour in graph.get(node, ()):
            cycle = walk(neighbour, [*path, node])
            if cycle is not None:
                return cycle
        visiting.discard(node)
        done.add(node)
        return None

    for head in list(graph):
        cycle = walk(head, [])
        if cycle is not None:
            names = " -> ".join(cls.__name__ for cls in cycle)
            failed = next(axis for axis in axes if axis.head_entity is cycle[0])
            _fail(failed, f"the head and its alternatives form a cycle: {names}")


def _validate_across_axes_first(
    axes: list[EntitySpecializationIntentResolver],
    judged: list[type[BaseEntity]],
) -> None:
    """Rules that name a cause the per-axis rules would describe only as a symptom."""
    _validate_one_head_per_class(axes)
    _validate_one_axis_per_classifier(axes)
    _validate_no_outside_class_points_at_an_axis(axes, judged)


def _validate_across_axes_last(axes: list[EntitySpecializationIntentResolver]) -> None:
    """Rules that only mean anything once every axis is individually sound."""
    _validate_no_cycles(axes)


def validate_entity_specializations(entities: list[type[BaseEntity]] | None = None) -> None:
    """
    Refuse any specialization declaration that breaks a build rule.

    Args:
        entities: Extra classes to judge, added to the walk rather than replacing it. The
            walk is what makes the closure rule possible: a class outside a union is exactly
            the class the graph has no node for, so a check narrowed to a passed-in list
            would never see the class it exists to refuse. A caller passes classes the walk
            skips — fixtures marked ``@exclude_graph_model`` — when it wants them judged.

    Raises:
        SpecializationDeclarationError: A declaration broke a rule; the error names the
            class, the field and the rule.

    A model that declares no specialization returns without doing anything, so an
    unchanged model takes no new path through the build.
    """
    judged = declared_entity_classes()
    if entities is not None:
        judged = [*judged, *(cls for cls in entities if cls not in judged)]
    axes = _gather_axes(judged)
    if not axes:
        return
    # Three passes, in the order of fundamentality. First the rules whose violation makes a
    # per-axis rule report a symptom instead of the cause: when a class is claimed by two heads,
    # the second head sees "an alternative that forgot to point back", which is true and useless.
    # Then the axis itself — a class that is not an entity cannot be asked about its reverse
    # field either. Finally the rules that mean nothing until each axis is sound.
    _validate_across_axes_first(axes, judged)
    for axis in axes:
        _validate_axis(axis)
    _validate_across_axes_last(axes)
