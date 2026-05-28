from __future__ import annotations

from abc import ABC
from typing import Generic, Protocol, TypeVar

import pytest

from aoa.action_machine.graph.core.edge_relationship import GENERALIZATION
from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge


def test_generalization_graph_edge_uses_generalization_relationship() -> None:
    edge = GeneralizationGraphEdge(
        edge_name="parent_action",
        is_dag=False,
        target_node_id="pkg.actions.ParentAction",
    )

    assert edge.edge_relationship is GENERALIZATION
    d = edge.to_dict(source_id="pkg.actions.ChildAction")
    assert d["relationship"] == GENERALIZATION.archimate_name
    assert d["type"] == "parent_action"


def _sort_key(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def test_collect_direct_parents_single_parent_skips_root() -> None:
    class AxisRoot:
        pass

    class Parent(AxisRoot):
        pass

    class Child(Parent):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(Child, AxisRoot) == (Parent,)
    assert GeneralizationGraphEdge.collect_direct_parents(Parent, AxisRoot) == ()
    assert GeneralizationGraphEdge.collect_direct_parents(AxisRoot, AxisRoot) == ()


def test_collect_direct_parents_transitive_not_flattened() -> None:
    class AxisRoot:
        pass

    class A(AxisRoot):
        pass

    class B(A):
        pass

    class C(B):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(C, AxisRoot) == (B,)
    assert GeneralizationGraphEdge.collect_direct_parents(B, AxisRoot) == (A,)


def test_collect_direct_parents_multiple_inheritance_sorted() -> None:
    class AxisRoot:
        pass

    class BranchA(AxisRoot):
        pass

    class BranchB(AxisRoot):
        pass

    class Combined(BranchB, BranchA):
        pass

    expected = tuple(sorted((BranchA, BranchB), key=_sort_key))
    assert GeneralizationGraphEdge.collect_direct_parents(Combined, AxisRoot) == expected


def test_collect_direct_parents_skips_protocol_bases() -> None:
    class AxisRoot:
        pass

    class Proto(Protocol):
        pass

    class Concrete(AxisRoot):
        pass

    class Mixed(Proto, Concrete):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(Mixed, AxisRoot) == (Concrete,)


def test_collect_direct_parents_skips_plain_generic_base() -> None:
    T = TypeVar("T")

    class AxisRoot:
        pass

    class WithGeneric(Generic[T], AxisRoot):
        pass

    class Leaf(WithGeneric[int]):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(Leaf, AxisRoot) == (WithGeneric,)


def test_collect_direct_parents_unions_orig_bases_with_bases_for_generic_subclass() -> None:
    """``__orig_bases__`` may repeat only the parameterized root while ``__bases__`` holds the direct parent."""

    T = TypeVar("T")

    class AxisRoot(Generic[T]):
        pass

    class Mid(AxisRoot[int]):
        pass

    class Leaf(Mid):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(Leaf, AxisRoot) == (Mid,)


def test_collect_direct_parents_prefers_orig_bases_when_present() -> None:
    T = TypeVar("T")

    class AxisRoot:
        pass

    class ParamBase(Generic[T], AxisRoot):
        pass

    class Specialized(ParamBase[int]):
        pass

    bases = Specialized.__bases__
    assert hasattr(Specialized, "__orig_bases__")
    assert Specialized.__orig_bases__ != bases

    assert GeneralizationGraphEdge.collect_direct_parents(Specialized, AxisRoot) == (ParamBase,)


def test_collect_direct_parents_filters_non_axis_bases() -> None:
    class AxisRoot:
        pass

    class NotOnAxis:
        pass

    class OnAxis(AxisRoot):
        pass

    class Child(NotOnAxis, OnAxis):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(Child, AxisRoot) == (OnAxis,)


def test_collect_direct_parents_mixed_bases_skip_axis_root_keep_concrete_parent() -> None:
    """PR-8: direct bases may list the axis root alongside the real parent — only the parent is kept."""

    class AxisRoot:
        pass

    class Concrete(AxisRoot):
        pass

    class Child(Concrete, AxisRoot):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(Child, AxisRoot) == (Concrete,)


def test_collect_direct_parents_mixed_bases_generic_subclass_and_concrete() -> None:
    """PR-8: same host may list a parameterized generic axis subclass and another concrete axis class."""

    T = TypeVar("T")

    class AxisRoot:
        pass

    class Gen(Generic[T], AxisRoot):
        pass

    class Standalone(AxisRoot):
        pass

    class Child(Standalone, Gen[int]):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(Child, AxisRoot) == (Gen, Standalone)


def test_collect_direct_parents_keeps_abc_intermediate_classifier() -> None:
    """PR-8: intermediate ABC on the axis is a valid direct generalization target."""

    class AxisRoot:
        pass

    class AbstractService(ABC, AxisRoot):
        pass

    class ConcreteService(AbstractService):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(ConcreteService, AxisRoot) == (AbstractService,)
    assert GeneralizationGraphEdge.collect_direct_parents(AbstractService, AxisRoot) == ()


def test_collect_direct_parents_requires_class_arguments() -> None:
    class AxisRoot:
        pass

    with pytest.raises(TypeError, match="host_cls"):
        GeneralizationGraphEdge.collect_direct_parents("not-a-type", AxisRoot)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="root"):
        GeneralizationGraphEdge.collect_direct_parents(AxisRoot, "not-a-type")  # type: ignore[arg-type]


def test_generalization_graph_edge_exported_from_aoa_graph_package() -> None:
    import aoa.action_machine.graph.core as g

    assert g.GeneralizationGraphEdge is GeneralizationGraphEdge
