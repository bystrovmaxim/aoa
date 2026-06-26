# packages/aoa-langgraph/src/aoa/langgraph/topology_validator.py
"""
Topology and dataflow validator for LangGraphController.build().

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Implements 11 structural checks run inside ``.build()``.  Rules 1–2 (data
contract: output fields declared, no inconsistent finish outs) live in
``_validate_contract()`` and run before this validator is called.

Rules 1–3  — node/entry/finish presence
Rules 4–6  — all name references resolve to registered nodes or END
Rule  7    — non-finish nodes have ≥1 outgoing edge
Rules 8–9  — BFS reachability from start nodes
(cycles are NOT an error — LLM agent loops are normal)
Rules 10–11 — required Params fields and out-fields have at least one producer

Rules #14–#15 are structural only: a field is "covered" if ANY action node in
the graph writes it, OR it is declared as an inp-field.  Path-conditionality
(a producer exists only on some branches) is legal — runtime readiness checks
(``_extract_params``, ``_extract_output``) handle the rest.

Function nodes (no Params/Result) are transparent to rules 10–11.
Nodes with ``response_mapper`` are excluded from write-set analysis (opaque).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    LangGraphController.build()
        │
        ▼  _validate_topology()
        │      passes plain Python types (no dataclass imports → no circular dep)
        │
        ▼  topology_validator.validate(...)
               rules 1–6    — O(n) presence checks
               _build_adjacency + _bfs  — O(n+e) reachability
               rules 7–9    — dead ends, unreachable nodes, unreachable finishes
               _check_dataflow  — ActionSchemaIntentResolver for write sets

"""

from __future__ import annotations

from collections import deque
from typing import Any

from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from aoa.langgraph.exceptions import (
    DeadEndNodeError,
    FieldHasNoProducerError,
    FinishUnreachableError,
    NoEntryPointError,
    NoFinishPointError,
    NoNodesError,
    OutputHasNoProducerError,
    UnreachableNodeError,
    UnregisteredNodeError,
)

_END = "__end__"


def validate(
    *,
    node_names: set[str],
    action_nodes: dict[str, Any],
    edges: list[tuple[str, str]],
    conditional_edges: list[tuple[str, str, str]],
    routes: list[tuple[str, list[str]]],
    start_names: list[str],
    finish_names: list[str],
    inp_field_names: set[str],
    out_field_names: set[str],
    has_opaque_action_nodes: bool = False,
) -> None:
    """Run all 11 topology and dataflow checks; raise on the first violation found."""
    _check_presence(node_names, start_names, finish_names)
    _check_name_references(
        node_names=node_names,
        start_names=start_names,
        finish_names=finish_names,
        edges=edges,
        conditional_edges=conditional_edges,
        routes=routes,
    )
    adj = _build_adjacency(node_names, edges, conditional_edges, routes, finish_names)
    _check_reachability(adj, node_names, start_names, finish_names)
    _check_dataflow(action_nodes, inp_field_names, out_field_names, has_opaque_action_nodes)


def _check_presence(
    node_names: set[str],
    start_names: list[str],
    finish_names: list[str],
) -> None:
    """Raise if nodes, starts, or finishes are empty (rules 1–3)."""
    if not node_names:
        raise NoNodesError("No nodes registered. Call .node() at least once.")
    if not start_names:
        raise NoEntryPointError("No start node declared. Call .start() at least once.")
    if not finish_names:
        raise NoFinishPointError("No finish node declared. Call .finish() at least once.")


def _check_name_references(
    *,
    node_names: set[str],
    start_names: list[str],
    finish_names: list[str],
    edges: list[tuple[str, str]],
    conditional_edges: list[tuple[str, str, str]],
    routes: list[tuple[str, list[str]]],
) -> None:
    """Verify all referenced node names are registered (rules 4–6)."""
    valid_dests = node_names | {_END}
    for name in start_names:
        if name not in node_names:
            raise UnregisteredNodeError(
                f"Start node '{name}' is not registered. Call .node() before .start()."
            )
    for name in finish_names:
        if name not in node_names:
            raise UnregisteredNodeError(
                f"Finish node '{name}' is not registered. Call .node() before .finish()."
            )
    for _src, dst in edges:
        if dst not in valid_dests:
            raise UnregisteredNodeError(
                f"Edge destination '{dst}' is not a registered node or END."
            )
    for _src, if_true, if_false in conditional_edges:
        for dst in (if_true, if_false):
            if dst not in valid_dests:
                raise UnregisteredNodeError(
                    f"Conditional edge destination '{dst}' is not a registered node or END."
                )
    for _src, targets in routes:
        for dst in targets:
            if dst not in valid_dests:
                raise UnregisteredNodeError(
                    f"Route destination '{dst}' is not a registered node or END."
                )


def _check_reachability(
    adj: dict[str, set[str]],
    node_names: set[str],
    start_names: list[str],
    finish_names: list[str],
) -> None:
    """Check dead ends, finish reachability, and full-graph reachability (rules 7–9)."""
    for name in node_names:
        if name in finish_names:
            continue
        if not adj.get(name):
            raise DeadEndNodeError(name)
    reachable = _bfs(adj, start_names)
    for finish in finish_names:
        if finish not in reachable:
            raise FinishUnreachableError(finish)
    for name in node_names:
        if name not in reachable:
            raise UnreachableNodeError(name)


def _build_adjacency(
    node_names: set[str],
    edges: list[tuple[str, str]],
    conditional_edges: list[tuple[str, str, str]],
    routes: list[tuple[str, list[str]]],
    finish_names: list[str],
) -> dict[str, set[str]]:
    """Build a forward adjacency dict; finish nodes implicitly connect to END."""
    adj: dict[str, set[str]] = {n: set() for n in node_names | {_END}}

    for src, dst in edges:
        adj.setdefault(src, set()).add(dst)

    for src, if_true, if_false in conditional_edges:
        adj.setdefault(src, set()).update((if_true, if_false))

    for src, targets in routes:
        adj.setdefault(src, set()).update(targets)

    for finish in finish_names:
        adj.setdefault(finish, set()).add(_END)

    return adj


def _bfs(adj: dict[str, set[str]], starts: list[str]) -> set[str]:
    """Return the set of all nodes reachable from any of the start nodes via BFS."""
    visited: set[str] = set()
    queue: deque[str] = deque(starts)
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for neighbour in adj.get(node, set()):
            if neighbour not in visited:
                queue.append(neighbour)
    return visited


def _check_dataflow(
    action_nodes: dict[str, Any],
    inp_field_names: set[str],
    out_field_names: set[str],
    has_opaque_action_nodes: bool = False,
) -> None:
    """Check that required Params fields and out-fields each have at least one producer.

    When has_opaque_action_nodes=True (any node has response_mapper), rule 11 is skipped:
    opaque nodes can write any field and their write-sets cannot be determined statically.
    """
    all_written: set[str] = _collect_write_sets(action_nodes)

    # Rule 10: each required Params field has a producer or is an inp-field
    for node_name, action_cls in action_nodes.items():
        try:
            params_type = ActionSchemaIntentResolver.resolve_params_type(action_cls)
            if params_type is None:
                continue
        except (ValueError, TypeError):
            continue
        for field_name, field_info in params_type.model_fields.items():
            if not field_info.is_required():
                continue
            if field_name in inp_field_names or field_name in all_written:
                continue
            raise FieldHasNoProducerError(node_name, field_name)

    # Rule 11: each out-field has a producer or is an inp-field.
    # Skip when opaque nodes exist — their writes are unknown.
    if not has_opaque_action_nodes:
        for field_name in out_field_names:
            if field_name in inp_field_names or field_name in all_written:
                continue
            raise OutputHasNoProducerError(field_name)


def _collect_write_sets(action_nodes: dict[str, Any]) -> set[str]:
    """Collect all fields written by any action node (union of all Result field names)."""
    written: set[str] = set()
    for action_cls in action_nodes.values():
        try:
            result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
            written.update(result_type.model_fields.keys())
        except (ValueError, TypeError):
            pass
    return written
