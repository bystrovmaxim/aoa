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

``resource_entity`` (2.0) is the aggregation edge from a resource to each entity its ``@entities``
lists. An entity may lie in two databases — a replica or a projection — so the edge is not
"exactly one per entity"; the schema checks only the shape, and AOA checks "one per listed entry"
when it builds the graph. Protocols before 2.0 carried ``entity_resource`` (1.6) and ``DataSource``
with ``resource_data_source`` (1.7, 1.8); 2.0 removes them: a resource is a database, and the model
names no store.

``entity_specialization`` is the association edge from a head to one of its alternatives. One edge per
alternative; ``alternatives`` repeats the whole ordered declaration on every edge of the cluster, so a
consumer holding one row has the set without a second lookup and without re-sorting what was written.

The schema belongs to the Open Gnomon Protocol, a standard with no code that lives in
bystrovmaxim/gnomon (``packages/open-gnomon-protocol/graph/2.0.json``); ``graph_json_schema.json``
beside this module is a copy of it, which ``tests/scripts/test_schema_copies.py`` keeps equal to
version ``2.0`` as published. AOA writes version ``2.0``.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

GRAPH_JSON_SCHEMA: dict[str, Any] = json.loads(
    files(__package__).joinpath("graph_json_schema.json").read_text(encoding="utf-8")
)
