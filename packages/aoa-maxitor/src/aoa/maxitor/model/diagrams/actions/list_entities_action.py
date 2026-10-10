# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py
"""
ListEntitiesAction — ERD entity/field/relation JSON from DuckDB.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Return ``ERD_DATA``-shaped slices per requested ``BaseDomain`` interchange id from
``connections["DuckDBGraph"]``. Scalar columns come from ``entity_field`` /
``entity_field_edges`` (interchange ``EntityField`` vertices + ``entity_field`` composition
edges); relation slots appear as ``FK -> …`` rows. The wire ``domain_slices`` field uses
``ListEntitiesDomainSlicesJson`` from
:mod:`~aoa.maxitor.model.diagrams.actions.list_entities_action_schema` (a
:class:`~aoa.action_machine.model.json_schema_value.JsonSchemaValue` alias).
"""

from __future__ import annotations

from typing import Annotated, Any, cast

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi.query_field_before import QUERY_STR_LIST_BEFORE
from aoa.maxitor.model.diagrams.actions.list_entities_action_schema import ListEntitiesDomainSlicesJson
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource


@meta(
    description="List entities, fields, and relations for interchange domain qualnames (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (entity / domain / entity_relation)",
)
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
                "BaseDomain interchange node ids. HTTP: repeat ``domain_qualnames`` once per id. Omit for no domains."
            ),
        )
        include_one_hop_neighbors: bool = Field(
            default=True,
            description="Include neighbor entities one ``entity_relation`` edge away from the slice.",
        )

    class Result(BaseResult):
        """HTTP/JSON body is ``model_dump(mode="json")`` of this result (single key ``domain_slices``)."""

        # [
        #   {
        #     "domain_label": "Billing",
        #     "domain_qualname": "myapp.model.billing.domain.BillingDomain",
        #     "list_entities": {
        #       "entities": [
        #         {
        #           "id": (
        #             "myapp.model.billing.entities.billing_sat_interchange_slice."
        #             "InterchangeAssessmentSliceEntity"
        #           ),
        #           "label": "InterchangeAssessmentSliceEntity",
        #           "domain_qualname": "myapp.model.billing.domain.BillingDomain",
        #           "fields": [
        #             {"name": "id", "type": "str", "primary_key": true, "foreign_key": false},
        #             {
        #               "name": "lifecycle",
        #               "type": "BillingDenseLifecycle",
        #               "primary_key": false,
        #               "foreign_key": false,
        #             },
        #             {"name": "scheme_code", "type": "str", "primary_key": false, "foreign_key": false},
        #             {"name": "assessor_build", "type": "str", "primary_key": false, "foreign_key": false},
        #             {
        #               "name": "ic_plus_basis_points",
        #               "type": "int",
        #               "primary_key": false,
        #               "foreign_key": false,
        #             },
        #             {
        #               "name": "network_batch_id",
        #               "type": "str",
        #               "primary_key": false,
        #               "foreign_key": false,
        #             },
        #             {
        #               "name": "legal_entity_ref",
        #               "type": "str",
        #               "primary_key": false,
        #               "foreign_key": false,
        #             },
        #             {"name": "currency_iso", "type": "str", "primary_key": false, "foreign_key": false},
        #             {
        #               "name": "chargeback_ingest_correlate",
        #               "type": "FK -> BillingChargebackIngestCorrelateEntity",
        #               "primary_key": false,
        #               "foreign_key": true,
        #             },
        #           ],
        #         }
        #       ],
        #       "relations": [
        #         {
        #           "source": (
        #             "myapp.model.billing.entities.billing_sat_interchange_slice."
        #             "InterchangeAssessmentSliceEntity"
        #           ),
        #           "target": (
        #             "myapp.model.billing.entities.billing_mesh_chargeback_ingest."
        #             "BillingChargebackIngestCorrelateEntity"
        #           ),
        #           "label": "chargeback_ingest_correlate",
        #           "relationship_kind": "association",
        #           "source_cardinality": "zero_many",
        #           "target_cardinality": "one",
        #         }
        #       ],
        #     },
        #   }
        # ]
        domain_slices: ListEntitiesDomainSlicesJson = Field(
            description="One entry per requested domain: domain_label, domain_qualname, list_entities.",
        )

    @staticmethod
    def _domain_label(duck: DuckDBGraphResource, qual: str) -> str:
        """Return ``domain`` label from DuckDB, or ``qual`` when the row is missing."""
        row = duck.service.execute(
            "SELECT COALESCE(NULLIF(name, ''), label, id) FROM domain WHERE id = ?",
            [qual],
        ).fetchone()
        return str(row[0]) if row else qual

    @staticmethod
    def _slice_payload(duck: DuckDBGraphResource, qual: str, include_neighbors: bool) -> dict[str, Any]:
        """Run DuckDB SQL for one domain slice and return ``entities`` + ``relations`` lists."""
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
        ), specialization_edge_rows AS (
          SELECT
            ese.source_id AS entity_id,
            ese.source_id || ':' || ese.field_name AS field_node_id,
            ese.field_name || ' (by ' || ese.classifier_field || ')' AS name,
            ese.labels AS labels,
            ese.alternative_index AS ordinal,
            COUNT(DISTINCT ese.target_id) OVER (PARTITION BY ese.source_id, ese.field_name) AS alternatives
          FROM entity_specialization_edges ese
        ), specialization_rows AS (
          SELECT
            entity_id,
            field_node_id,
            name,
            array_to_string(MIN(labels), ' | ') AS type,
            MIN(ordinal) AS ordinal,
            MAX(alternatives) AS alternatives
          FROM specialization_edge_rows
          GROUP BY entity_id, field_node_id, name
        ), rendered_rows AS (
          SELECT entity_id, field_node_id, name, type, ordinal
          FROM specialization_rows
          WHERE alternatives > 1
        ), excluded_field_nodes AS (
          SELECT field_node_id FROM rendered_rows
        ), field_rows AS (
          SELECT
            efe.source_id AS entity_id,
            efe.target_id AS field_node_id,
            vf.label AS name,
            vf.field_type AS type,
            vf.primary_key_hint AS primary_key,
            FALSE AS foreign_key,
            efe.ordinal AS ordinal
          FROM entity_field_edges efe
          INNER JOIN entity_field vf ON vf.id = efe.target_id
          WHERE efe.target_id NOT IN (SELECT field_node_id FROM excluded_field_nodes WHERE field_node_id IS NOT NULL)
          UNION ALL
          SELECT
            rr.entity_id,
            rr.field_node_id,
            rr.name,
            rr.type,
            FALSE AS primary_key,
            TRUE AS foreign_key,
            rr.ordinal
          FROM rendered_rows rr
          UNION ALL
          SELECT entity_id, CAST(NULL AS VARCHAR) AS field_node_id, name, type, FALSE AS primary_key, foreign_key, 2147483647 AS ordinal FROM fk
        ), ordered_field_rows AS (
          SELECT DISTINCT
                 fr.entity_id,
                 fr.field_node_id,
                 fr.name,
                 fr.type,
                 fr.primary_key,
                 fr.foreign_key,
                 fr.ordinal AS sort_key
          FROM field_rows fr
        )
        SELECT e.id, e.label, COALESCE(MIN(de.target_id), '') AS domain_qualname,
               COALESCE(
                 list(struct_pack(
                   field_id := fr.field_node_id,
                   name := fr.name,
                   type := fr.type,
                   primary_key := fr.primary_key,
                   foreign_key := fr.foreign_key
                 ) ORDER BY fr.sort_key, fr.name) FILTER (WHERE fr.name IS NOT NULL),
                 CAST([] AS STRUCT(
                   field_id VARCHAR,
                   name VARCHAR,
                   type VARCHAR,
                   primary_key BOOLEAN,
                   foreign_key BOOLEAN
                 )[])
               ) AS fields
        FROM selected_entity se
        JOIN entity e ON e.id = se.id
        LEFT JOIN domain_edges de ON de.source_id = e.id
        LEFT JOIN ordered_field_rows fr ON fr.entity_id = e.id
        GROUP BY e.id, e.label
        ORDER BY e.id
    """
        group_sql = f"""
        WITH domain_entity AS (
          SELECT source_id AS id FROM domain_edges WHERE target_id = ?
        ), selected_entity AS (
          SELECT id FROM domain_entity
          {neighbor_clause}
        )
        SELECT ese.source_id || ':' || ese.field_name AS group_id,
               ese.field_name || ' (by ' || ese.classifier_field || ')' AS label,
               ese.classifier_field AS classifier_field,
               list(DISTINCT ese.target_id ORDER BY ese.target_id) AS members
        FROM entity_specialization_edges ese
        WHERE ese.source_id IN (SELECT id FROM selected_entity)
        GROUP BY ese.source_id, ese.field_name, ese.classifier_field
        HAVING COUNT(DISTINCT ese.target_id) > 1
        ORDER BY ese.source_id, ese.field_name
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
        relations = duck.execute_fetch_dicts(relation_sql, [qual])
        groups = duck.execute_fetch_dicts(group_sql, [qual])
        relations.extend(
            {
                "source": group["group_id"].rsplit(":", 1)[0],
                "target": group["group_id"],
                "label": "by " + str(group["classifier_field"]),
                "relationship_kind": "specialization",
                "source_cardinality": "zero_many",
                "target_cardinality": "one",
            }
            for group in groups
        )
        # The generalization half of the axis: each extension points at its head.
        parent_entity_sql = """
        WITH domain_entity AS (
          SELECT source_id AS id FROM domain_edges WHERE target_id = ?
        )
        SELECT pe.source_id AS source, pe.target_id AS target,
               CASE WHEN COALESCE(pe.classifier_value, '') = '' THEN pe.field_name ELSE pe.classifier_value END AS label,
               'generalization' AS relationship_kind,
               'zero_many' AS source_cardinality,
               'one' AS target_cardinality
        FROM parent_entity_edges pe
        WHERE pe.source_id IN (SELECT id FROM domain_entity)
          AND pe.target_id IN (SELECT id FROM domain_entity)
        ORDER BY pe.source_id, pe.target_id
        """
        relations.extend(duck.execute_fetch_dicts(parent_entity_sql, [qual]))
        return {
            "entities": duck.execute_fetch_dicts(entity_sql, [qual]),
            "relations": relations,
            "groups": groups,
        }

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
                "domain_label": self._domain_label(duck, qual),
                "domain_qualname": qual,
                "list_entities": self._slice_payload(duck, qual, params.include_one_hop_neighbors),
            }
            for qual in params.domain_qualnames
        ]
        return ListEntitiesAction.Result(domain_slices=slices)
