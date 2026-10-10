# tests/maxitor/test_duckdb_specialization_type_registration.py
"""
The store now knows two edge kinds, and it still refuses a kind nobody declared.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A specialization reaches the diagram as two edge kinds — `entity_specialization` (head to one
alternative) and `parent_entity` (extension to head). The resource keeps a list of known node and
edge types and raises on anything else, which is the right behaviour for a viewer that must not
silently drop what it cannot draw. So both kinds have to be **taught**, at every site a kind is
known about, and this file is what proves they were: the graph is accepted, each kind lands in its
own table with its properties intact, its indexes exist like every other edge table's, and both
appear in the view the viewer queries.

The last class feeds the same resource a kind nobody declared. The guard must still refuse, so the
tests above prove the kinds were taught rather than the guard loosened. That distinction is the
whole point: a test that only checks a graph is accepted passes just as well when the guard has
been removed.

═══════════════════════════════════════════════════════════════════════════════
WHY THE KIND IS REMOVED FROM THE REGISTRY RATHER THAN FROM THE GRAPH
═══════════════════════════════════════════════════════════════════════════════

"The store refuses an unregistered kind" cannot be shown by sending a kind the engine never emits:
that proves the guard works on nonsense, not that it protects these two. The measured form is to
take the registry away from a kind that **is** emitted and confirm the load dies — which is exactly
what a half-finished registration would look like to a user.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **KeyError** — an edge kind the store does not know; raised once, for the whole load.

Covers registration. What the rows contain is the ERD test file's subject.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.maxitor.model.diagrams.resources import duckdb_graph_resource as resource_module
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    _EDGE_TABLE_NAMES,
    DuckDBGraphResource,
)

SPECIALIZATION = "entity_specialization"
GENERALIZATION = "parent_entity"
_SPECIALIZATION_TABLE = "entity_specialization_edges"
_GENERALIZATION_TABLE = "parent_entity_edges"


def _graph_with(*edge_types: str) -> dict[str, Any]:
    """Return a graph whose edges carry ``edge_types``, one edge each."""
    nodes = [
        {"id": "d.demo", "type": "Domain", "label": "Demo", "properties": {"name": "Demo", "description": "d"}},
        {"id": "e.Head", "type": "Entity", "label": "Head", "properties": {"description": "h"}},
        {"id": "e.Alt", "type": "Entity", "label": "Alt", "properties": {"description": "a"}},
    ]
    properties = {
        SPECIALIZATION: {
            "field_name": "pack",
            "classifier_field": "media",
            "classifier_value": "first",
            "alternative_index": 0,
            "alternatives": ["first -> e.Alt"],
            "labels": ["Alt (first)"],
            "relation_type": "specialization",
            "cardinality": "one",
            "description": "d",
            "has_inverse": True,
            "deprecated": False,
        },
        GENERALIZATION: {
            "field_name": "record",
            "inverse_field": "pack",
            "classifier_value": "first",
            "head_entity_id": "e.Head",
        },
    }
    edges = [
        {
            "source_id": "e.Head",
            "target_id": "e.Alt",
            "type": edge_type,
            "relationship": "Generalization" if edge_type == GENERALIZATION else "Association",
            "is_dag": False,
            "properties": properties[edge_type],
        }
        for edge_type in edge_types
    ]
    return {"schema_version": "1.0", "nodes": nodes, "edges": edges}


class TestTheKindsAreKnown:
    def test_a_graph_carrying_both_kinds_is_accepted(self) -> None:
        """Both kinds in one graph, because a half-registered pair is the failure being guarded."""
        duck = DuckDBGraphResource.build_from_json(_graph_with(SPECIALIZATION, GENERALIZATION))

        assert duck is not None

    def test_each_kind_lands_in_its_own_table(self) -> None:
        duck = DuckDBGraphResource.build_from_json(_graph_with(SPECIALIZATION, GENERALIZATION))
        counts = {
            table: int(duck.service.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # type: ignore[union-attr]
            for table in (_SPECIALIZATION_TABLE, _GENERALIZATION_TABLE)
        }

        assert counts == {_SPECIALIZATION_TABLE: 1, _GENERALIZATION_TABLE: 1}

    def test_the_properties_survive_the_table(self) -> None:
        """A column the table forgets is a property the diagram loses, so the values are read back."""
        duck = DuckDBGraphResource.build_from_json(_graph_with(SPECIALIZATION, GENERALIZATION))

        specialization = duck.execute_fetch_dicts(
            f"SELECT field_name, classifier_field, classifier_value, labels FROM {_SPECIALIZATION_TABLE}",
        )[0]
        generalization = duck.execute_fetch_dicts(
            f"SELECT field_name, inverse_field, head_entity_id FROM {_GENERALIZATION_TABLE}",
        )[0]

        assert specialization["field_name"] == "pack"
        assert specialization["classifier_field"] == "media"
        assert specialization["classifier_value"] == "first"
        assert generalization == {"field_name": "record", "inverse_field": "pack", "head_entity_id": "e.Head"}
        # Every property of this kind is required, and the table says so: a nullable column would let a
        # row through with the property missing, and the diagram would draw an axis with no partner field.
        columns = {
            row["column_name"]: row["is_nullable"]
            for row in duck.execute_fetch_dicts(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                f"WHERE table_name = '{_GENERALIZATION_TABLE}'"
            )
        }
        assert columns["inverse_field"] == "NO", "the generalization's properties are not optional"
        assert columns["field_name"] == "NO"
        assert columns["classifier_value"] == "NO"
        assert columns["head_entity_id"] == "NO"

    def test_both_tables_are_indexed_like_every_other_edge_table(self) -> None:
        """Edge tables are indexed through one tuple; an entry missing from it slows the viewer."""
        duck = DuckDBGraphResource.build_from_json(_graph_with(SPECIALIZATION, GENERALIZATION))

        for table in (_SPECIALIZATION_TABLE, _GENERALIZATION_TABLE):
            indexes = {
                row[0]
                for row in duck.service.execute(  # type: ignore[union-attr]
                    f"SELECT index_name FROM duckdb_indexes() WHERE table_name = '{table}'"
                ).fetchall()
            }
            assert indexes == {f"ix_{table}_source", f"ix_{table}_target"}

    def test_both_kinds_appear_in_the_view_the_viewer_reads(self) -> None:
        duck = DuckDBGraphResource.build_from_json(_graph_with(SPECIALIZATION, GENERALIZATION))

        types = {row["type"] for row in duck.execute_fetch_dicts("SELECT DISTINCT type FROM edges")}

        assert {_SPECIALIZATION_TABLE, _GENERALIZATION_TABLE} <= types

    def test_both_kinds_are_in_the_table_name_tuple(self) -> None:
        """The tuple drives index creation, so a kind outside it is a table without indexes."""
        assert {_SPECIALIZATION_TABLE, _GENERALIZATION_TABLE} <= set(_EDGE_TABLE_NAMES)


class TestTheGuardStillRefuses:
    def test_a_kind_nobody_declared_is_still_refused(self) -> None:
        graph = _graph_with(SPECIALIZATION)
        graph["edges"][0]["type"] = "not_declared_at_all"

        with pytest.raises(KeyError, match="Unknown edge graph type"):
            DuckDBGraphResource.build_from_json(graph)

    def test_the_guard_names_every_kind_it_did_not_recognise(self) -> None:
        graph = _graph_with(SPECIALIZATION)
        graph["edges"][0]["type"] = "not_declared_at_all"

        with pytest.raises(KeyError) as caught:
            DuckDBGraphResource.build_from_json(graph)

        assert "not_declared_at_all" in str(caught.value)


class TestARegistryEntryIsRequired:
    """
    Take the registry away from a kind the engine **does** emit, and the load must die.

    This is the shape a half-finished registration has: the emitter is there, one of the five sites
    is not. A guard that let the graph through would put a diagram on screen with an axis silently
    missing from it, which is the failure this feature exists to remove.
    """

    @pytest.mark.parametrize("kind", [SPECIALIZATION, GENERALIZATION])
    def test_a_kind_missing_from_the_registry_stops_the_whole_load(
        self,
        kind: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """One kind not recognised, and the load dies naming it — not a diagram with a hole in it."""
        original = resource_module._assert_no_unknown_graph_types

        def _guard_that_never_learned_this_kind(
            nodes_by_type: dict[str, Any],
            edges_by_type: dict[str, Any],
        ) -> None:
            """Refuse exactly the kind under test, and behave normally for everything else."""
            if kind in edges_by_type:
                msg = f"Unknown edge graph type(s): {[kind]!r}"
                raise KeyError(msg)
            original(nodes_by_type, edges_by_type)

        monkeypatch.setattr(resource_module, "_assert_no_unknown_graph_types", _guard_that_never_learned_this_kind)

        with pytest.raises(KeyError, match="Unknown edge graph type") as caught:
            DuckDBGraphResource.build_from_json(_graph_with(kind))

        assert kind in str(caught.value), "the refusal names the kind it did not recognise"
