# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py
"""ListEntitiesAction — ERD entity/field/relation JSON from DuckDB."""

from __future__ import annotations

from typing import Annotated, Any, cast

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.integrations.fastapi.query_field_before import QUERY_STR_LIST_BEFORE
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState, JsonSchemaValue
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


def _domain_label(duck: DuckDBGraphResource, qual: str) -> str:
    # Label from ``domain`` row only; if missing, echo ``qual`` (no guessed short name).
    row = duck.service.execute(
        "SELECT COALESCE(NULLIF(name, ''), label, id) FROM domain WHERE id = ?",
        [qual],
    ).fetchone()
    return str(row[0]) if row else qual


def _slice_payload(duck: DuckDBGraphResource, qual: str, include_neighbors: bool) -> dict[str, Any]:
    neighbor_clause = (
        """
        UNION
        SELECT er.target_id FROM entity_relation_edges er JOIN domain_entity de ON er.source_id = de.id
        UNION
        SELECT er.source_id FROM entity_relation_edges er JOIN domain_entity de ON er.target_id = de.id
        """
        if include_neighbors
        else ""
    )
    entity_sql = f"""
        WITH domain_entity AS (
          SELECT source_id AS id FROM domain_edges WHERE target_id = ?
        ), selected_entity AS (
          SELECT id FROM domain_entity
          {neighbor_clause}
        ), fk AS (
          SELECT er.source_id AS entity_id, er.field_name AS name, 'FK -> ' || target.label AS type, TRUE AS foreign_key
          FROM entity_relation_edges er
          JOIN selected_entity src ON src.id = er.source_id
          JOIN selected_entity tgt ON tgt.id = er.target_id
          JOIN entity target ON target.id = er.target_id
          WHERE er.field_name <> ''
        ), field_rows AS (
          SELECT entity_id, name, type, primary_key, FALSE AS foreign_key FROM entity_field
          UNION ALL
          SELECT entity_id, name, type, FALSE AS primary_key, foreign_key FROM fk
        )
        SELECT e.id, e.label, COALESCE(MIN(de.target_id), '') AS domain_qualname,
               list(distinct struct_pack(
                 name := fr.name,
                 type := fr.type,
                 primary_key := fr.primary_key,
                 foreign_key := fr.foreign_key
               )) AS fields
        FROM selected_entity se
        JOIN entity e ON e.id = se.id
        LEFT JOIN domain_edges de ON de.source_id = e.id
        LEFT JOIN field_rows fr ON fr.entity_id = e.id
        GROUP BY e.id, e.label
        ORDER BY e.id
    """
    relation_sql = f"""
        WITH domain_entity AS (
          SELECT source_id AS id FROM domain_edges WHERE target_id = ?
        ), selected_entity AS (
          SELECT id FROM domain_entity
          {neighbor_clause}
        )
        SELECT er.source_id AS source, er.target_id AS target,
               CASE WHEN er.cardinality = '' THEN er.field_name ELSE er.field_name || ' (' || er.cardinality || ')' END AS label,
               COALESCE(NULLIF(er.relation_type, ''), 'association') AS relationship_kind,
               CASE WHEN er.cardinality = 'one' THEN 'zero_many' ELSE 'one' END AS source_cardinality,
               CASE WHEN er.cardinality = 'one' THEN 'one' ELSE 'zero_many' END AS target_cardinality
        FROM entity_relation_edges er
        JOIN selected_entity src ON src.id = er.source_id
        JOIN selected_entity tgt ON tgt.id = er.target_id
        WHERE er.source_id IN (SELECT id FROM domain_entity)
           OR er.target_id IN (SELECT id FROM domain_entity)
        ORDER BY er.source_id, er.target_id, er.field_name
    """
    return {
        "entities": duck.execute_fetch_dicts(entity_sql, [qual]),
        "relations": duck.execute_fetch_dicts(relation_sql, [qual]),
    }


@meta(description="List entities, fields, and relations for interchange domain qualnames (diagrams)", domain=DiagramsDomain)
@check_roles(NoneRole)
@connection(DuckDBGraphResource, key=DUCKDB_GRAPH_CONNECTION_KEY, description="Coordinator graph in DuckDB (entity / domain / entity_relation)")
class ListEntitiesAction(BaseAction["ListEntitiesAction.Params", "ListEntitiesAction.Result"]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``ERD_DATA``-shaped JSON slices for each requested ``BaseDomain`` interchange id.
    CONTRACT: ``domain_qualnames`` list is used as given (order and duplicates preserved); empty list yields no slices.
    INVARIANTS: Reads ``connections[DuckDBGraph]`` (DuckDB connection) only — no NetworkX scan.
    AI-CORE-END
    """

    class Params(BaseParams):
        domain_qualnames: Annotated[list[str], QUERY_STR_LIST_BEFORE] = Field(
            default_factory=list,
            description=(
                "BaseDomain interchange node ids. HTTP: repeat ``domain_qualnames`` once per id. "
                "Omit for no domains."
            ),
        )
        include_one_hop_neighbors: bool = Field(
            default=True,
            description="Include neighbor entities one ``entity_relation`` edge away from the slice.",
        )

    class Result(BaseResult):
        domain_slices: JsonSchemaValue.define(
            name="ListEntitiesDomainSlicesJson",
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "domain_label": {"type": "string", "minLength": 1},
                        "domain_qualname": {"type": "string", "minLength": 1},
                        "list_entities": {
                            "type": "object",
                            "properties": {
                                "entities": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "label": {"type": "string"},
                                            "domain_qualname": {
                                                "type": "string",
                                                "description": (
                                                    "Interchange qualname of the BaseDomain owning this entity "
                                                    "(for accent coloring)."
                                                ),
                                            },
                                            "fields": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "type": {"type": "string"},
                                                        "primary_key": {"type": "boolean"},
                                                        "foreign_key": {"type": "boolean"},
                                                    },
                                                    "required": [
                                                        "name",
                                                        "type",
                                                        "primary_key",
                                                        "foreign_key",
                                                    ],
                                                    "additionalProperties": False,
                                                },
                                            },
                                        },
                                        "required": ["id", "label", "domain_qualname", "fields"],
                                        "additionalProperties": False,
                                    },
                                },
                                "relations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "source": {"type": "string"},
                                            "target": {"type": "string"},
                                            "label": {"type": "string"},
                                            "relationship_kind": {"type": "string"},
                                            "source_cardinality": {
                                                "type": "string",
                                                "enum": ["one", "zero_one", "one_many", "zero_many"],
                                            },
                                            "target_cardinality": {
                                                "type": "string",
                                                "enum": ["one", "zero_one", "one_many", "zero_many"],
                                            },
                                        },
                                        "required": [
                                            "source",
                                            "target",
                                            "label",
                                            "relationship_kind",
                                            "source_cardinality",
                                            "target_cardinality",
                                        ],
                                        "additionalProperties": False,
                                    },
                                },
                            },
                            "required": ["entities", "relations"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["domain_label", "domain_qualname", "list_entities"],
                    "additionalProperties": False,
                },
            },
        ) = Field(
            description="One entry per requested domain: domain_label, domain_qualname, list_entities.",
        )

    @summary_aspect("Serialize ERD slices for requested domains (DuckDB)")
    async def build_domain_payload_summary(
        self,
        params: ListEntitiesAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListEntitiesAction.Result:
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        if not params.domain_qualnames:
            return ListEntitiesAction.Result(domain_slices=[])

        slices = [
            {
                "domain_label": _domain_label(duck, qual),
                "domain_qualname": qual,
                "list_entities": _slice_payload(duck, qual, params.include_one_hop_neighbors),
            }
            for qual in params.domain_qualnames
        ]
        return ListEntitiesAction.Result(domain_slices=slices)
