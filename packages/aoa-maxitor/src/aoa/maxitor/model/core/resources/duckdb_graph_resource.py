# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/duckdb_graph_resource.py
"""
DuckDB-backed coordinator graph resource — in-memory SQL over JSON loaded **over HTTP**
from the examples ``graph-json`` endpoint (:data:`DEFAULT_EXAMPLE_GRAPH_JSON_URL`).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``connections["DuckDBGraph"]`` is the :class:`DuckDBGraphResource`; :attr:`~ExternalServiceResource.service`
is the in-memory ``duckdb.DuckDBPyConnection``. :meth:`DuckDBGraphResource.__init__` opens the database,
:meth:`DuckDBGraphResource._install_database` runs explicit ``CREATE TABLE`` / ``CREATE INDEX`` / ``CREATE VIEW``
(physical tables plus ``CREATE VIEW nodes`` / ``edges``, then ``nodes_type_counts`` / ``edge_type_counts`` over those views; aligned with
:data:`~aoa.action_machine.graph_model.graph_json_schema.GRAPH_JSON_SCHEMA`), then :func:`_fill_database` inserts rows
from the validated coordinator payload.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import duckdb
from jsonschema import Draft202012Validator

from aoa.action_machine.graph_model.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service.external_service_resource import ExternalServiceResource
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain

DEFAULT_EXAMPLE_GRAPH_JSON_URL = "http://127.0.0.1:8001/examples/model/graph-json"
ENV_EXAMPLE_GRAPH_JSON_URL = "MAXITOR_EXAMPLE_GRAPH_JSON_URL"

DUCKDB_GRAPH_CONNECTION_KEY = "DuckDBGraph"


@meta(
    description="DuckDB in-memory store for coordinator graph JSON (HTTP + entity/domain helpers)",
    domain=DiagramsDomain,
)
class DuckDBGraphResource(ExternalServiceResource[duckdb.DuckDBPyConnection]):
    """
    AI-CORE-BEGIN
    ROLE: Fetch coordinator graph JSON via HTTP and load it into DuckDB; :attr:`.service` is the DuckDB connection.
    CONTRACT: GET :data:`DEFAULT_EXAMPLE_GRAPH_JSON_URL` (or :envvar:`MAXITOR_EXAMPLE_GRAPH_JSON_URL`), parse ``coordinator_json``, validate against :data:`~aoa.action_machine.graph_model.graph_json_schema.GRAPH_JSON_SCHEMA`, create schema via :meth:`_install_database`, then :func:`_fill_database`.
    AI-CORE-END
    """

    @staticmethod
    def load_graph_json_http() -> dict[str, Any]:
        """HTTP GET ``graph-json``; parse ``coordinator_json`` and validate against :data:`~aoa.action_machine.graph_model.graph_json_schema.GRAPH_JSON_SCHEMA`."""
        raw_url = os.environ.get(ENV_EXAMPLE_GRAPH_JSON_URL, DEFAULT_EXAMPLE_GRAPH_JSON_URL)
        url = (raw_url or "").strip() or DEFAULT_EXAMPLE_GRAPH_JSON_URL
        req = Request(url, method="GET")
        try:
            with urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
        except HTTPError as exc:
            msg = f"Example graph-json HTTP {exc.code} from {url!r}"
            raise RuntimeError(msg) from exc
        except URLError as exc:
            msg = f"Example graph-json request failed for {url!r}: {exc.reason!r}"
            raise RuntimeError(msg) from exc
        envelope: dict[str, Any] = json.loads(body)
        coordinator_raw = envelope.get("coordinator_json")
        if not isinstance(coordinator_raw, str):
            msg = f"Expected str coordinator_json in response from {url!r}, got {type(coordinator_raw).__name__}"
            raise TypeError(msg)
        payload: dict[str, Any] = json.loads(coordinator_raw)
        Draft202012Validator(GRAPH_JSON_SCHEMA).validate(payload)
        return payload

    def _install_database(self, con: duckdb.DuckDBPyConnection) -> None:
        """Create DuckDB tables, indexes, and ``nodes`` / ``edges`` views (DDL only; no row inserts)."""
        parts: list[str] = [
        # --- node tables (one table per graph-node oneOf branch in GRAPH_JSON_SCHEMA) ---
        """CREATE TABLE action (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE application (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      name VARCHAR NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE domain (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      name VARCHAR NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE entity (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE resource (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE params (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL
    );""",
        """CREATE TABLE result (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL
    );""",
        """CREATE TABLE field (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      prop_required BOOLEAN NOT NULL,
      description VARCHAR NOT NULL,
      json_schema_value BOOLEAN NOT NULL,
      entity_schema BOOLEAN NOT NULL,
      json_schema_name VARCHAR,
      json_schema JSON
    );""",
        """CREATE TABLE property_field (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      prop_required BOOLEAN NOT NULL,
      entity_schema BOOLEAN NOT NULL
    );""",
        """CREATE TABLE regular_aspect (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE summary_aspect (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE compensator (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      description VARCHAR,
      target_aspect_name VARCHAR
    );""",
        """CREATE TABLE error_handler (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      description VARCHAR,
      exception_types JSON
    );""",
        """CREATE TABLE checker (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      type_checker VARCHAR NOT NULL,
      checker_required BOOLEAN NOT NULL
    );""",
        """CREATE TABLE required_context (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      ctx_key VARCHAR NOT NULL
    );""",
        """CREATE TABLE lifecycle (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      field_name VARCHAR NOT NULL
    );""",
        """CREATE TABLE state (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      kind VARCHAR NOT NULL,
      lifecycle_class_id VARCHAR NOT NULL,
      state_key VARCHAR NOT NULL
    );""",
        """CREATE TABLE sensitive (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      properties JSON NOT NULL
    );""",
        """CREATE TABLE role (
      id VARCHAR NOT NULL PRIMARY KEY,
      label VARCHAR NOT NULL,
      role_mode VARCHAR NOT NULL
    );""",
        # --- edges: ``empty_properties`` enum members (separate tables) ---
        """CREATE TABLE application_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE domain_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE generic_params_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE generic_result_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE check_roles_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE regular_aspect_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE summary_aspect_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE compensate_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE on_error_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE result_checker_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE entity_schema_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE field_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        """CREATE TABLE property_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL
    );""",
        # --- other link oneOf branches ---
        """CREATE TABLE depends_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      description VARCHAR NOT NULL
    );""",
        """CREATE TABLE connection_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      conn_key VARCHAR NOT NULL
    );""",
        """CREATE TABLE required_context_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      ctx_key VARCHAR NOT NULL
    );""",
        """CREATE TABLE entity_relation_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      field_name VARCHAR NOT NULL,
      relation_type VARCHAR NOT NULL,
      cardinality VARCHAR NOT NULL,
      description VARCHAR NOT NULL,
      has_inverse BOOLEAN NOT NULL,
      deprecated BOOLEAN NOT NULL,
      inverse_entity_id VARCHAR,
      inverse_field VARCHAR
    );""",
        """CREATE TABLE entity_view_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      field_name VARCHAR NOT NULL
    );""",
        """CREATE TABLE lifecycle_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      field_name VARCHAR NOT NULL
    );""",
        """CREATE TABLE lifecycle_contains_state_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      state_key VARCHAR NOT NULL
    );""",
        """CREATE TABLE lifecycle_transition_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      from_state VARCHAR NOT NULL,
      to_state VARCHAR NOT NULL
    );""",
        """CREATE TABLE sensitive_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      properties JSON NOT NULL
    );""",
        """CREATE TABLE state_edges (
      source_id VARCHAR NOT NULL,
      target_id VARCHAR NOT NULL,
      relationship VARCHAR NOT NULL,
      is_dag BOOLEAN NOT NULL,
      properties JSON NOT NULL
    );""",
        ]
        parts.extend(f"CREATE INDEX ix_{t}_source ON {t} (source_id);" for t in _EDGE_TABLE_NAMES)
        parts.extend(f"CREATE INDEX ix_{t}_target ON {t} (target_id);" for t in _EDGE_TABLE_NAMES)
        parts.extend(
            [
                "CREATE INDEX ix_state_lifecycle ON state (lifecycle_class_id, state_key);",
                "CREATE INDEX ix_state_kind ON state (kind);",
            ],
        )
        parts.extend(_graph_union_view_ddls())
        parts.extend(_type_count_view_ddls())
        con.execute("".join(parts))

    def __init__(self) -> None:
        json_data = DuckDBGraphResource.load_graph_json_http()
        self._source_json = dict(json_data)
        con = duckdb.connect(database=":memory:")
        self._install_database(con)
        _fill_database(con, json_data)
        super().__init__(con)


def _pack_json_or_none(value: Any) -> str | None:
    """JSON-encode ``value`` for DuckDB ``JSON`` columns; return ``None`` when ``value`` is ``None``."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _get_properties(row: dict[str, Any]) -> dict[str, Any]:
    """Return ``row['properties']`` when it is a dict; otherwise ``{}``."""
    raw = row.get("properties")
    if isinstance(raw, dict):
        return cast(dict[str, Any], raw)
    return {}


# Nodes / edge JSON ``type`` is implied by the physical table name, except ``state`` rows where
# three JSON kinds share one table — then column ``kind`` stores ``StateInitial`` / ``StateIntermediate`` / ``StateFinal``.
# DDL ends with ``CREATE VIEW nodes`` / ``edges`` / ``nodes_type_counts`` / ``edge_type_counts``.


def _qt(ident: str) -> str:
    """Double-quote a SQL identifier."""
    return '"' + ident.replace('"', '""') + '"'


_EDGE_TABLE_NAMES: tuple[str, ...] = (
    "application_edges",
    "domain_edges",
    "generic_params_edges",
    "generic_result_edges",
    "check_roles_edges",
    "regular_aspect_edges",
    "summary_aspect_edges",
    "compensate_edges",
    "on_error_edges",
    "result_checker_edges",
    "entity_schema_edges",
    "field_edges",
    "property_edges",
    "depends_edges",
    "connection_edges",
    "required_context_edges",
    "entity_relation_edges",
    "entity_view_edges",
    "lifecycle_edges",
    "lifecycle_contains_state_edges",
    "lifecycle_transition_edges",
    "sensitive_edges",
    "state_edges",
)


def _graph_union_view_ddls() -> list[str]:
    """Return ``CREATE VIEW nodes`` and ``CREATE VIEW edges`` (union of physical tables; ``type`` is table name except ``state`` uses ``kind``)."""

    def _nj() -> str:
        return "json_object()"

    node_parts: list[str] = [
        "SELECT id, label, CAST('action' AS VARCHAR) AS type, json_object('description', description) AS payload FROM action",
        "SELECT id, label, CAST('application' AS VARCHAR) AS type, json_object('name', name, 'description', description) AS payload FROM application",
        "SELECT id, label, CAST('domain' AS VARCHAR) AS type, json_object('name', name, 'description', description) AS payload FROM domain",
        "SELECT id, label, CAST('entity' AS VARCHAR) AS type, json_object('description', description) AS payload FROM entity",
        "SELECT id, label, CAST('resource' AS VARCHAR) AS type, json_object('description', description) AS payload FROM resource",
        f"SELECT id, label, CAST('params' AS VARCHAR) AS type, {_nj()} AS payload FROM params",
        f"SELECT id, label, CAST('result' AS VARCHAR) AS type, {_nj()} AS payload FROM result",
        "SELECT id, label, CAST('field' AS VARCHAR) AS type, json_object('prop_required', prop_required, 'description', description, 'json_schema_value', json_schema_value, 'entity_schema', entity_schema, 'json_schema_name', json_schema_name, 'json_schema', json_schema) AS payload FROM field",
        "SELECT id, label, CAST('property_field' AS VARCHAR) AS type, json_object('prop_required', prop_required, 'entity_schema', entity_schema) AS payload FROM property_field",
        "SELECT id, label, CAST('regular_aspect' AS VARCHAR) AS type, json_object('description', description) AS payload FROM regular_aspect",
        "SELECT id, label, CAST('summary_aspect' AS VARCHAR) AS type, json_object('description', description) AS payload FROM summary_aspect",
        "SELECT id, label, CAST('compensator' AS VARCHAR) AS type, json_object('description', description, 'target_aspect_name', target_aspect_name) AS payload FROM compensator",
        "SELECT id, label, CAST('error_handler' AS VARCHAR) AS type, json_object('description', description, 'exception_types', exception_types) AS payload FROM error_handler",
        "SELECT id, label, CAST('checker' AS VARCHAR) AS type, json_object('type_checker', type_checker, 'checker_required', checker_required) AS payload FROM checker",
        "SELECT id, label, CAST('required_context' AS VARCHAR) AS type, json_object('ctx_key', ctx_key) AS payload FROM required_context",
        "SELECT id, label, CAST('lifecycle' AS VARCHAR) AS type, json_object('field_name', field_name) AS payload FROM lifecycle",
        "SELECT id, label, kind AS type, json_object('lifecycle_class_id', lifecycle_class_id, 'state_key', state_key) AS payload FROM state",
        "SELECT id, label, CAST('sensitive' AS VARCHAR) AS type, json_object('properties', properties) AS payload FROM sensitive",
        "SELECT id, label, CAST('role' AS VARCHAR) AS type, json_object('role_mode', role_mode) AS payload FROM role",
    ]
    edge_parts: list[str] = [
        f"SELECT source_id, target_id, relationship, is_dag, CAST('application_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM application_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('domain_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM domain_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('generic_params_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM generic_params_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('generic_result_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM generic_result_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('check_roles_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM check_roles_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('regular_aspect_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM regular_aspect_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('summary_aspect_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM summary_aspect_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('compensate_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM compensate_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('on_error_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM on_error_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('result_checker_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM result_checker_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('entity_schema_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM entity_schema_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('field_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM field_edges",
        f"SELECT source_id, target_id, relationship, is_dag, CAST('property_edges' AS VARCHAR) AS type, {_nj()} AS payload FROM property_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('depends_edges' AS VARCHAR) AS type, json_object('description', description) AS payload FROM depends_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('connection_edges' AS VARCHAR) AS type, json_object('conn_key', conn_key) AS payload FROM connection_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('required_context_edges' AS VARCHAR) AS type, json_object('ctx_key', ctx_key) AS payload FROM required_context_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('entity_relation_edges' AS VARCHAR) AS type, json_object('field_name', field_name, 'relation_type', relation_type, 'cardinality', cardinality, 'description', description, 'has_inverse', has_inverse, 'deprecated', deprecated, 'inverse_entity_id', inverse_entity_id, 'inverse_field', inverse_field) AS payload FROM entity_relation_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('entity_view_edges' AS VARCHAR) AS type, json_object('field_name', field_name) AS payload FROM entity_view_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('lifecycle_edges' AS VARCHAR) AS type, json_object('field_name', field_name) AS payload FROM lifecycle_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('lifecycle_contains_state_edges' AS VARCHAR) AS type, json_object('state_key', state_key) AS payload FROM lifecycle_contains_state_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('lifecycle_transition_edges' AS VARCHAR) AS type, json_object('from_state', from_state, 'to_state', to_state) AS payload FROM lifecycle_transition_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('sensitive_edges' AS VARCHAR) AS type, json_object('properties', properties) AS payload FROM sensitive_edges",
        "SELECT source_id, target_id, relationship, is_dag, CAST('state_edges' AS VARCHAR) AS type, json_object('properties', properties) AS payload FROM state_edges",
    ]
    return [
        "CREATE VIEW nodes AS\n" + "\nUNION ALL\n".join(node_parts) + ";",
        "CREATE VIEW edges AS\n" + "\nUNION ALL\n".join(edge_parts) + ";",
    ]


def _type_count_view_ddls() -> list[str]:
    """Return ``CREATE VIEW nodes_type_counts`` / ``edge_type_counts`` (aggregates ``nodes.type`` / ``edges.type``)."""

    return [
        (
            "CREATE VIEW nodes_type_counts AS "
            "SELECT type AS label, COUNT(*)::BIGINT AS row_count FROM nodes GROUP BY type;"
        ),
        (
            "CREATE VIEW edge_type_counts AS "
            "SELECT type AS label, COUNT(*)::BIGINT AS row_count FROM edges GROUP BY type;"
        ),
    ]


def _fill_table_action(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO action VALUES (?, ?, ?)",
            [node["id"], node["label"], p["description"]],
        )


def _fill_table_application(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO application VALUES (?, ?, ?, ?)",
            [node["id"], node["label"], p["name"], p["description"]],
        )


def _fill_table_domain(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO domain VALUES (?, ?, ?, ?)",
            [node["id"], node["label"], p["name"], p["description"]],
        )


def _fill_table_entity(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute("INSERT INTO entity VALUES (?, ?, ?)", [node["id"], node["label"], p["description"]])


def _fill_table_resource(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute("INSERT INTO resource VALUES (?, ?, ?)", [node["id"], node["label"], p["description"]])


def _fill_table_params(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        con.execute("INSERT INTO params VALUES (?, ?)", [node["id"], node["label"]])


def _fill_table_result(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        con.execute("INSERT INTO result VALUES (?, ?)", [node["id"], node["label"]])


def _fill_table_field(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO field VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                node["id"],
                node["label"],
                p["required"],
                p["description"],
                p["json_schema_value"],
                p["entity_schema"],
                p.get("json_schema_name"),
                _pack_json_or_none(p.get("json_schema")),
            ],
        )


def _fill_table_property_field(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO property_field VALUES (?, ?, ?, ?)",
            [node["id"], node["label"], p["required"], p["entity_schema"]],
        )


def _fill_table_regular_aspect(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO regular_aspect VALUES (?, ?, ?)",
            [node["id"], node["label"], p["description"]],
        )


def _fill_table_summary_aspect(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO summary_aspect VALUES (?, ?, ?)",
            [node["id"], node["label"], p["description"]],
        )


def _fill_table_compensator(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO compensator VALUES (?, ?, ?, ?)",
            [node["id"], node["label"], p.get("description"), p.get("target_aspect_name")],
        )


def _fill_table_error_handler(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO error_handler VALUES (?, ?, ?, ?)",
            [node["id"], node["label"], p.get("description"), _pack_json_or_none(p.get("exception_types"))],
        )


def _fill_table_checker(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO checker VALUES (?, ?, ?, ?)",
            [node["id"], node["label"], p["TypeChecker"], p["required"]],
        )


def _fill_table_required_context(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO required_context VALUES (?, ?, ?)",
            [node["id"], node["label"], p["key"]],
        )


def _fill_table_lifecycle(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO lifecycle VALUES (?, ?, ?)",
            [node["id"], node["label"], p["field_name"]],
        )


def _fill_table_state(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        t = node["type"]
        con.execute(
            "INSERT INTO state VALUES (?, ?, ?, ?, ?)",
            [node["id"], node["label"], t, p["lifecycle_class_id"], p["state_key"]],
        )


def _fill_table_sensitive(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute(
            "INSERT INTO sensitive VALUES (?, ?, ?)",
            [node["id"], node["label"], _pack_json_or_none(p)],
        )


def _fill_table_role(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for node in rows:
        p = _get_properties(node)
        con.execute("INSERT INTO role VALUES (?, ?, ?)", [node["id"], node["label"], p["role_mode"]])


def _fill_table_application_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO application_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_domain_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO domain_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_generic_params_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO generic_params_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_generic_result_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO generic_result_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_check_roles_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO check_roles_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_regular_aspect_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO regular_aspect_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_summary_aspect_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO summary_aspect_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_compensate_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO compensate_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_on_error_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO on_error_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_result_checker_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO result_checker_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_entity_schema_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO entity_schema_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_field_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO field_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_property_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        con.execute(
            "INSERT INTO property_edges (source_id, target_id, relationship, is_dag) VALUES (?, ?, ?, ?)",
            [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]],
        )


def _fill_table_depends_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO depends_edges (source_id, target_id, relationship, is_dag, description) VALUES (?, ?, ?, ?, ?)",
            [*base, p["description"]],
        )


def _fill_table_connection_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO connection_edges (source_id, target_id, relationship, is_dag, conn_key) VALUES (?, ?, ?, ?, ?)",
            [*base, p["key"]],
        )


def _fill_table_required_context_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO required_context_edges (source_id, target_id, relationship, is_dag, ctx_key) VALUES (?, ?, ?, ?, ?)",
            [*base, p["key"]],
        )


def _fill_table_entity_relation_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO entity_relation_edges (source_id, target_id, relationship, is_dag, field_name, relation_type, cardinality, description, has_inverse, deprecated, inverse_entity_id, inverse_field) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                *base,
                p["field_name"],
                p["relation_type"],
                p["cardinality"],
                p["description"],
                p["has_inverse"],
                p["deprecated"],
                p.get("inverse_entity_id"),
                p.get("inverse_field"),
            ],
        )


def _fill_table_entity_view_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO entity_view_edges (source_id, target_id, relationship, is_dag, field_name) VALUES (?, ?, ?, ?, ?)",
            [*base, p["field_name"]],
        )


def _fill_table_lifecycle_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO lifecycle_edges (source_id, target_id, relationship, is_dag, field_name) VALUES (?, ?, ?, ?, ?)",
            [*base, p["field_name"]],
        )


def _fill_table_lifecycle_contains_state_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO lifecycle_contains_state_edges (source_id, target_id, relationship, is_dag, state_key) VALUES (?, ?, ?, ?, ?)",
            [*base, p["state_key"]],
        )


def _fill_table_lifecycle_transition_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO lifecycle_transition_edges (source_id, target_id, relationship, is_dag, from_state, to_state) VALUES (?, ?, ?, ?, ?, ?)",
            [*base, p["from_state"], p["to_state"]],
        )


def _fill_table_sensitive_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO sensitive_edges (source_id, target_id, relationship, is_dag, properties) VALUES (?, ?, ?, ?, ?)",
            [*base, _pack_json_or_none(p)],
        )


def _fill_table_state_edges(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    for edge in rows:
        p = _get_properties(edge)
        base = [edge["source_id"], edge["target_id"], edge["relationship"], edge["is_dag"]]
        con.execute(
            "INSERT INTO state_edges (source_id, target_id, relationship, is_dag, properties) VALUES (?, ?, ?, ?, ?)",
            [*base, _pack_json_or_none(p)],
        )


def _fill_database(con: duckdb.DuckDBPyConnection, json_data: dict[str, Any]) -> None:
    """Partition payload by ``type`` and fill every node and edge table via dedicated loaders."""
    nodes = list(json_data.get("nodes") or [])
    edges = list(json_data.get("edges") or [])
    nodes_by_type: dict[str, list[dict[str, Any]]] = {}
    for n in nodes:
        nodes_by_type.setdefault(str(n["type"]), []).append(n)
    edges_by_type: dict[str, list[dict[str, Any]]] = {}
    for e in edges:
        edges_by_type.setdefault(str(e["type"]), []).append(e)

    _fill_table_action(con, nodes_by_type.get("Action", []))
    _fill_table_application(con, nodes_by_type.get("Application", []))
    _fill_table_domain(con, nodes_by_type.get("Domain", []))
    _fill_table_entity(con, nodes_by_type.get("Entity", []))
    _fill_table_resource(con, nodes_by_type.get("Resource", []))
    _fill_table_params(con, nodes_by_type.get("Params", []))
    _fill_table_result(con, nodes_by_type.get("Result", []))
    _fill_table_field(con, nodes_by_type.get("Field", []))
    _fill_table_property_field(con, nodes_by_type.get("PropertyField", []))
    _fill_table_regular_aspect(con, nodes_by_type.get("RegularAspect", []))
    _fill_table_summary_aspect(con, nodes_by_type.get("SummaryAspect", []))
    _fill_table_compensator(con, nodes_by_type.get("Compensator", []))
    _fill_table_error_handler(con, nodes_by_type.get("ErrorHandler", []))
    _fill_table_checker(con, nodes_by_type.get("Checker", []))
    _fill_table_required_context(con, nodes_by_type.get("RequiredContext", []))
    _fill_table_lifecycle(con, nodes_by_type.get("Lifecycle", []))
    _fill_table_state(
        con,
        [
            *nodes_by_type.get("StateInitial", []),
            *nodes_by_type.get("StateIntermediate", []),
            *nodes_by_type.get("StateFinal", []),
        ],
    )
    _fill_table_sensitive(con, nodes_by_type.get("Sensitive", []))
    _fill_table_role(con, nodes_by_type.get("Role", []))

    _fill_table_application_edges(con, edges_by_type.get("application", []))
    _fill_table_domain_edges(con, edges_by_type.get("domain", []))
    _fill_table_generic_params_edges(con, edges_by_type.get("generic:params", []))
    _fill_table_generic_result_edges(con, edges_by_type.get("generic:result", []))
    _fill_table_check_roles_edges(con, edges_by_type.get("@check_roles", []))
    _fill_table_regular_aspect_edges(con, edges_by_type.get("@regular_aspect", []))
    _fill_table_summary_aspect_edges(con, edges_by_type.get("@summary_aspect", []))
    _fill_table_compensate_edges(con, edges_by_type.get("@compensate", []))
    _fill_table_on_error_edges(con, edges_by_type.get("@on_error", []))
    _fill_table_result_checker_edges(con, edges_by_type.get("@result_checker", []))
    _fill_table_entity_schema_edges(con, edges_by_type.get("entity_schema", []))
    _fill_table_field_edges(con, edges_by_type.get("field", []))
    _fill_table_property_edges(con, edges_by_type.get("property", []))
    _fill_table_depends_edges(con, edges_by_type.get("@depends", []))
    _fill_table_connection_edges(con, edges_by_type.get("@connection", []))
    _fill_table_required_context_edges(con, edges_by_type.get("@required_context", []))
    _fill_table_entity_relation_edges(con, edges_by_type.get("entity_relation", []))
    _fill_table_entity_view_edges(con, edges_by_type.get("entity_view", []))
    _fill_table_lifecycle_edges(con, edges_by_type.get("lifecycle", []))
    _fill_table_lifecycle_contains_state_edges(con, edges_by_type.get("lifecycle_contains_state", []))
    _fill_table_lifecycle_transition_edges(con, edges_by_type.get("lifecycle_transition", []))
    _fill_table_sensitive_edges(con, edges_by_type.get("sensitive", []))
    _fill_table_state_edges(con, edges_by_type.get("state", []))

    _assert_no_unknown_graph_types(nodes_by_type, edges_by_type)


def _assert_no_unknown_graph_types(
    nodes_by_type: dict[str, list[dict[str, Any]]],
    edges_by_type: dict[str, list[dict[str, Any]]],
) -> None:
    known_nodes = {
        "Action",
        "Application",
        "Domain",
        "Entity",
        "Resource",
        "Params",
        "Result",
        "Field",
        "PropertyField",
        "RegularAspect",
        "SummaryAspect",
        "Compensator",
        "ErrorHandler",
        "Checker",
        "RequiredContext",
        "Lifecycle",
        "StateInitial",
        "StateIntermediate",
        "StateFinal",
        "Sensitive",
        "Role",
    }
    known_edges = {
        "application",
        "domain",
        "generic:params",
        "generic:result",
        "@check_roles",
        "@regular_aspect",
        "@summary_aspect",
        "@compensate",
        "@on_error",
        "@result_checker",
        "entity_schema",
        "field",
        "property",
        "@depends",
        "@connection",
        "@required_context",
        "entity_relation",
        "entity_view",
        "lifecycle",
        "lifecycle_contains_state",
        "lifecycle_transition",
        "sensitive",
        "state",
    }
    extra_n = set(nodes_by_type) - known_nodes
    if extra_n:
        msg = f"Unknown nodes graph type(s): {sorted(extra_n)!r}"
        raise KeyError(msg)
    extra_e = set(edges_by_type) - known_edges
    if extra_e:
        msg = f"Unknown edge graph type(s): {sorted(extra_e)!r}"
        raise KeyError(msg)
