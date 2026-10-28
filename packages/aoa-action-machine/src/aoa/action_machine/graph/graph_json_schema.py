# packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py
"""JSON Schema for ActionMachine graph export via :class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator`.

Callers may pass :data:`GRAPH_JSON_SCHEMA` to :meth:`NodeGraphCoordinator.build` as ``export_json_schema``
for a stable keyword at call sites; :meth:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator.to_json`
does not validate against it (validate in tests or tooling with :class:`jsonschema.Draft202012Validator` if needed).

Sourced from ``archive/plan/CURRENT.md`` (appendix) with alignment fixes
(``Field`` node properties, ``Lifecycle`` / ``@required_context`` / ``@check_roles`` edge names).

Generalization (UML inheritance) edges ``parent_action``, ``parent_role``, and ``parent_domain`` use
``relationship: \"Generalization\"`` and empty ``properties``; each wire ``type`` is its own ``oneOf`` branch
(see plan ``generalization_graph_nodes.md`` §PR‑4 / §I.3).

``parent_entity`` is the same relationship **with properties**, and it cannot reuse those three: their
``properties`` block allows ``maxProperties: 0``, while an entity generalization has to name the field it
came through, the head's field it answers to, the code it declares, and the head itself.

``entity_specialization`` is the association edge from a head to one of its alternatives. One edge per
alternative; ``alternatives`` repeats the whole ordered declaration on every edge of the cluster, so a
consumer holding one row has the set without a second lookup and without re-sorting what was written.

The schema itself lives in ``maxitor-gnomon``, the graph format's own package, by version
(``packages/maxitor-gnomon/protocol/graph/<version>.json``, the Open Gnomon Protocol); this module names the version AOA writes, ``1.1``.
"""

from __future__ import annotations

from typing import Any

from maxitor_gnomon.schemas import graph_schema

GRAPH_JSON_SCHEMA: dict[str, Any] = graph_schema("1.1")
