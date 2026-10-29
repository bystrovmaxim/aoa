# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/list_entities_action.py
"""
ListEntitiesAction — ERD entity/field/relation JSON from DuckDB.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Return ``ERD_DATA``-shaped slices per requested ``BaseDomain`` interchange id from
``connections["DuckDBGraph"]``. Scalar columns come from ``entity_field`` /
``entity_field_edges`` (interchange ``EntityField`` vertices + ``entity_field`` composition
edges); relation slots appear as FK rows whose type is the target table's label. The wire ``domain_slices`` field uses
``ListEntitiesDomainSlicesJson`` from
:mod:`~maxitor.front.model.diagrams.actions.list_entities_action_schema` (a
:class:`~aoa.action_machine.model.json_schema_value.JsonSchemaValue` alias).
"""

from __future__ import annotations

import json
from typing import Annotated, Any, cast

from maxitor.front.model.diagrams.actions.list_entities_action_schema import (
    ListEntitiesDomainSlicesJson,
    ListEntitiesRelationsJson,
)
from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi.query_field_before import QUERY_STR_LIST_BEFORE

_KIND_FIELDS = frozenset({"code", "display_name"})
"""The field rows a dictionary kind supplies: never printed, always kept in ``values``."""


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
        #             "InterchangeAssessmentSliceCoreEntity"
        #           ),
        #           "label": "InterchangeAssessmentSliceCoreEntity",
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
        #               "type": "BillingChargebackIngestCorrelateCoreEntity",
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
        #             "InterchangeAssessmentSliceCoreEntity"
        #           ),
        #           "target": (
        #             "myapp.model.billing.entities.billing_mesh_chargeback_ingest."
        #             "BillingChargebackIngestCorrelateCoreEntity"
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
        relations: ListEntitiesRelationsJson = Field(
            default_factory=list,
            description=(
                "Every line between two tables of the whole request (the union of its slices); the merged "
                "multi-domain ERD draws these, pruned to the tables on screen."
            ),
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
    def _selection_cte(domain_count: int, include_neighbors: bool) -> str:
        """``domain_entity`` and ``selected_entity`` CTEs for ``domain_count`` domain ids bound as parameters."""
        placeholders = ", ".join("?" for _ in range(domain_count))
        neighbor_clause = (
            """
          UNION
          SELECT er.target_id FROM entity_relation_edges er JOIN domain_entity de ON er.source_id = de.id
          UNION
          SELECT er.source_id FROM entity_relation_edges er JOIN domain_entity de ON er.target_id = de.id
          UNION
          SELECT rr.target_id FROM entity_reference_edges rr JOIN domain_entity de ON rr.source_id = de.id
          UNION
          SELECT rr.source_id FROM entity_reference_edges rr JOIN domain_entity de ON rr.target_id = de.id
            """
            if include_neighbors
            else ""
        )
        return f"""
        WITH domain_entity AS (
          SELECT source_id AS id FROM domain_edges WHERE target_id IN ({placeholders})
        ), selected_entity AS (
          SELECT id FROM domain_entity
          {neighbor_clause}
        )"""

    @staticmethod
    def _association_rows(duck: DuckDBGraphResource, quals: list[str], include_neighbors: bool) -> list[dict[str, Any]]:
        """Relations, dictionary references and axis dictionaries whose two ends are both among the selected entities.

        Why a table is on screen — its own domain or a 1-hop neighbour — never decides whether its lines are drawn.
        A relation field and its declared inverse are one association and give one row: ``source_field`` is the
        canonical field (the side with cardinality ``one``; on a tie the smaller table id, then the smaller field
        name), ``target_field`` its inverse; a relation without an inverse is its own row with ``target_field`` null.
        """
        sql = ListEntitiesAction._selection_cte(len(quals), include_neighbors) + """
        , rel AS (
          SELECT er.*
          FROM entity_relation_edges er
          JOIN selected_entity src ON src.id = er.source_id
          JOIN selected_entity tgt ON tgt.id = er.target_id
        )
        SELECT * FROM (
          SELECT r.source_id AS source, r.target_id AS target,
                 CASE WHEN r.cardinality = '' THEN r.field_name ELSE r.field_name || ' (' || r.cardinality || ')' END AS label,
                 COALESCE(NULLIF(r.relation_type, ''), 'association') AS relationship_kind,
                 -- An end is one, zero or one (an optional relation), or zero or many (spec 029, FR-043).
                 CASE
                   WHEN i.field_name IS NULL THEN CASE WHEN r.cardinality = 'one' THEN 'zero_many' ELSE 'one' END
                   WHEN i.cardinality = 'one' THEN CASE WHEN i.optional THEN 'zero_one' ELSE 'one' END
                   ELSE 'zero_many'
                 END AS source_cardinality,
                 CASE
                   WHEN r.cardinality = 'one' THEN CASE WHEN r.optional THEN 'zero_one' ELSE 'one' END
                   ELSE 'zero_many'
                 END AS target_cardinality,
                 r.field_name AS source_field,
                 i.field_name AS target_field
          FROM rel r
          LEFT JOIN rel i
            ON COALESCE(r.inverse_field, '') <> ''
           AND i.source_id = r.target_id
           AND i.target_id = r.source_id
           AND i.field_name = r.inverse_field
          WHERE i.field_name IS NULL
             OR (r.cardinality = 'one' AND i.cardinality <> 'one')
             OR ((r.cardinality = 'one') = (i.cardinality = 'one')
                 AND (r.source_id < i.source_id OR (r.source_id = i.source_id AND r.field_name < i.field_name)))
          UNION ALL
          SELECT rr.source_id AS source, rr.target_id AS target, rr.field_name AS label,
                 'reference' AS relationship_kind,
                 -- Many rows refer to one dictionary value: the crow's foot at the referring table.
                 'zero_many' AS source_cardinality,
                 'one' AS target_cardinality,
                 rr.field_name AS source_field,
                 CAST(NULL AS VARCHAR) AS target_field
          FROM entity_reference_edges rr
          JOIN selected_entity src ON src.id = rr.source_id
          JOIN selected_entity tgt ON tgt.id = rr.target_id
          UNION ALL
          -- A specialization head draws a line to the dictionary its axis is classified by.
          SELECT DISTINCT ese.source_id AS source, ese.dictionary_qualname AS target, ese.field_name AS label,
                 'reference' AS relationship_kind,
                 'zero_many' AS source_cardinality,
                 'one' AS target_cardinality,
                 ese.field_name AS source_field,
                 CAST(NULL AS VARCHAR) AS target_field
          FROM entity_specialization_edges ese
          JOIN selected_entity src ON src.id = ese.source_id
          JOIN selected_entity tgt ON tgt.id = ese.dictionary_qualname
        ) rows
        ORDER BY source, target, label
        """
        return duck.execute_fetch_dicts(sql, quals)

    @staticmethod
    def _generalization_rows(
        duck: DuckDBGraphResource, quals: list[str], include_neighbors: bool
    ) -> list[dict[str, Any]]:
        """Extension → head lines whose two ends are both among the selected entities."""
        sql = ListEntitiesAction._selection_cte(len(quals), include_neighbors) + """
        SELECT pe.source_id AS source, pe.target_id AS target,
               CASE WHEN COALESCE(pe.classifier_value, '') = '' THEN pe.field_name ELSE pe.classifier_value END AS label,
               'generalization' AS relationship_kind,
               -- A head row has at most one row of each variant; a variant row has exactly one head.
               'zero_one' AS source_cardinality,
               'one' AS target_cardinality,
               -- The two declared fields that join a variant to its head: its reverse field, the head's axis.
               pe.field_name AS source_field,
               pe.inverse_field AS target_field
        FROM parent_entity_edges pe
        JOIN selected_entity src ON src.id = pe.source_id
        JOIN selected_entity tgt ON tgt.id = pe.target_id
        ORDER BY pe.source_id, pe.target_id
        """
        return duck.execute_fetch_dicts(sql, quals)

    @staticmethod
    def request_relations(duck: DuckDBGraphResource, quals: list[str], include_neighbors: bool) -> list[dict[str, Any]]:
        """Every line between two tables of the whole request, so a line whose ends come from two slices exists."""
        if not quals:
            return []
        rows = ListEntitiesAction._association_rows(duck, quals, include_neighbors)
        rows.extend(ListEntitiesAction._generalization_rows(duck, quals, include_neighbors))
        return rows

    @staticmethod
    def _slice_payload(duck: DuckDBGraphResource, qual: str, include_neighbors: bool) -> dict[str, Any]:
        """Run DuckDB SQL for one domain slice and return ``entities`` + ``relations`` lists."""
        neighbor_clause = (
            """
        UNION
        SELECT er.target_id FROM entity_relation_edges er JOIN domain_entity de ON er.source_id = de.id
        UNION
        SELECT er.source_id FROM entity_relation_edges er JOIN domain_entity de ON er.target_id = de.id
        UNION
        SELECT rr.target_id FROM entity_reference_edges rr JOIN domain_entity de ON rr.source_id = de.id
        UNION
        SELECT rr.source_id FROM entity_reference_edges rr JOIN domain_entity de ON rr.target_id = de.id
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
          -- A table lists every relation field it declares, whether its target is on screen or not.
          SELECT er.source_id AS entity_id, er.field_name AS name, target.label AS type, TRUE AS foreign_key
          FROM entity_relation_edges er
          JOIN selected_entity src ON src.id = er.source_id
          JOIN entity target ON target.id = er.target_id
          WHERE er.field_name <> ''
        ), specialization_edge_rows AS (
          SELECT
            ese.source_id AS entity_id,
            ese.source_id || ':' || ese.field_name AS field_node_id,
            ese.field_name AS name,
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
            -- A variant's reverse field is the key that points at its specialization head.
            EXISTS (
              SELECT 1 FROM parent_entity_edges pe WHERE pe.source_id = efe.source_id AND pe.field_name = vf.label
            ) AS foreign_key,
            efe.ordinal AS ordinal,
            vf.reference_qualname AS reference_qualname,
            vf.field_annotation AS annotation
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
            rr.ordinal,
            CAST(NULL AS VARCHAR) AS reference_qualname,
            CAST(NULL AS VARCHAR) AS annotation
          FROM rendered_rows rr
          UNION ALL
          SELECT entity_id, CAST(NULL AS VARCHAR) AS field_node_id, name, type, FALSE AS primary_key, foreign_key, 2147483647 AS ordinal, CAST(NULL AS VARCHAR) AS reference_qualname, CAST(NULL AS VARCHAR) AS annotation FROM fk
        ), ordered_field_rows AS (
          SELECT DISTINCT
                 fr.entity_id,
                 fr.field_node_id,
                 fr.name,
                 fr.type,
                 fr.primary_key,
                 fr.foreign_key,
                 fr.ordinal AS sort_key,
                 fr.reference_qualname,
                 fr.annotation
          FROM field_rows fr
        )
        SELECT e.id, e.label, COALESCE(MIN(de.target_id), '') AS domain_qualname,
               e.entity_kind AS entity_kind, e.values_json AS values_json, e.declares_values AS declares_values,
               COALESCE(
                 list(struct_pack(
                   field_id := fr.field_node_id,
                   name := fr.name,
                   type := fr.type,
                   primary_key := fr.primary_key,
                   foreign_key := fr.foreign_key,
                   reference_qualname := fr.reference_qualname,
                   annotation := fr.annotation
                 ) ORDER BY fr.sort_key, fr.name) FILTER (WHERE fr.name IS NOT NULL),
                 CAST([] AS STRUCT(
                   field_id VARCHAR,
                   name VARCHAR,
                   type VARCHAR,
                   primary_key BOOLEAN,
                   foreign_key BOOLEAN,
                   reference_qualname VARCHAR,
                   annotation VARCHAR
                 )[])
               ) AS fields
        FROM selected_entity se
        JOIN entity e ON e.id = se.id
        LEFT JOIN domain_edges de ON de.source_id = e.id
        LEFT JOIN ordered_field_rows fr ON fr.entity_id = e.id
        GROUP BY e.id, e.label, e.entity_kind, e.values_json, e.declares_values
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
               ese.field_name || ' (by ' || COALESCE(ese.classifier_field, ese.dictionary_label) || ')' AS label,
               ese.classifier_field AS classifier_field,
               ese.dictionary_label AS dictionary_label,
               list(DISTINCT ese.target_id ORDER BY ese.target_id) AS members
        FROM entity_specialization_edges ese
        WHERE ese.source_id IN (SELECT id FROM selected_entity)
        GROUP BY ese.source_id, ese.field_name, ese.classifier_field, ese.dictionary_label
        HAVING COUNT(DISTINCT ese.target_id) > 1
        ORDER BY ese.source_id, ese.field_name
        """
        relations = ListEntitiesAction._association_rows(duck, [qual], include_neighbors)
        groups = duck.execute_fetch_dicts(group_sql, [qual])
        relations.extend(
            {
                "source": group["group_id"].rsplit(":", 1)[0],
                "target": group["group_id"],
                "label": "by " + str(group["classifier_field"] or group["dictionary_label"]),
                "relationship_kind": "specialization",
                "source_cardinality": "zero_many",
                "target_cardinality": "one",
            }
            for group in groups
        )
        # The relation label above needs the name; the group's own label already carries it, so
        # the payload hands it over once, inside `label`.
        for group in groups:
            group.pop("dictionary_label", None)
        # The generalization half of the axis: each extension points at its head.
        relations.extend(ListEntitiesAction._generalization_rows(duck, [qual], include_neighbors))
        entities = duck.execute_fetch_dicts(entity_sql, [qual])
        for entity in entities:
            # A table that declares values is a dictionary card, whatever its kind word is called.
            if entity.pop("declares_values"):
                # The card shows labels: the two rows the dictionary kind supplies are storage
                # identity, and the code stays in ``values`` for every consumer that needs it.
                entity["fields"] = [
                    field for field in entity.get("fields") or [] if field.get("name") not in _KIND_FIELDS
                ]
            declared = json.loads(entity.pop("values_json") or "[]")
            entity["values"] = [
                {
                    "code": value["code"],
                    "display_name": value["display_name"],
                    "properties": [
                        {"name": name, "value": item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)}
                        for name, item in value.get("properties", {}).items()
                    ],
                }
                for value in declared
            ]
        return {
            "entities": entities,
            "relations": relations,
            "groups": groups,
        }

    @summary_aspect("Serialize ERD slices for requested domains (DuckDB)")
    async def build_domain_payload_summary(
        self,
        params: ListEntitiesAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
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
        relations = self.request_relations(duck, list(dict.fromkeys(params.domain_qualnames)), params.include_one_hop_neighbors)
        return ListEntitiesAction.Result(domain_slices=slices, relations=relations)
