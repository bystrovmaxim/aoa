# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_erd_domain_payload_action.py
"""
GetErdDomainPayloadAction — one bounded-context ERD graph as JSON for the client.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize ``{nodes, edges}`` for a single ``domain_qualname`` so the SPA can
render ERD without server-generated HTML. The ``graph`` field on ``Result`` uses
:class:`~aoa.action_machine.model.json_schema_value.JsonSchemaValue` for wire JSON Schema.

    Params.domain_qualname
          |
          v
    regular aspect  ->  ``erd_domain_class`` (:class:`~aoa.action_machine.domain.base_domain.BaseDomain` subclass)
          |
          v
    summary aspect  ->  Result graph JSON + labels
"""

from __future__ import annotations

import importlib
from typing import Any, ClassVar, cast

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState, JsonSchemaValue
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.resources.service_graph_resource import (
    SERVICE_GRAPH_CONNECTION_KEY,
    ServiceGraphResource,
)
from aoa.maxitor.model.diagrams.actions.build_erd_graph_data_action import (
    erd_payload_from_coordinator_for_domain,
    node_graph_coordinator_from_interchange_nx,
    payload_to_domain_dict,
)
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


@meta(
    description="Get ERD nodes/edges JSON for one interchange domain qualname (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(ServiceGraphResource, key=SERVICE_GRAPH_CONNECTION_KEY, description="Interchange nx graph from LoadGraphAction")
class GetErdDomainPayloadAction(
    BaseAction["GetErdDomainPayloadAction.Params", "GetErdDomainPayloadAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit one domain slice of ``ERD_DATA``-shaped JSON for client rendering.
    CONTRACT: ``domain_qualname`` is the full interchange node id for a ``BaseDomain`` class.
    INVARIANTS: Reads the graph only via ``connections["ServiceGraph"].service``; resolves the domain class in a regular aspect before building the graph.
    AI-CORE-END
    """

    class Params(BaseParams):
        domain_qualname: str = Field(min_length=1, description="Full qualname of the BaseDomain interchange node id")

    class Result(BaseResult):
        json_schema: ClassVar = JsonSchemaValue.define(
            name="ErdDomainGraphJson",
            schema={
                "type": "object",
                "properties": {
                    "nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {"type": "string"},
                                "color": {"type": "string"},
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
                                "domain_qualifier": {"type": "string"},
                            },
                            "required": ["id", "label", "color", "fields"],
                            "additionalProperties": False,
                        },
                    },
                    "edges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "target": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["source", "target", "label"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["nodes", "edges"],
                "additionalProperties": False,
            },
        )

        domain_label: str = Field(min_length=1, description="Human tab label (domain name or class name)")
        domain_qualifier: str = Field(min_length=1, description="Same as request interchange qualname")
        graph: json_schema = Field(description="ERD_DATA-style object: {nodes: [...], edges: [...]}")

    @regular_aspect("Resolve interchange BaseDomain class from qualname")
    @result_instance("erd_domain_class", type, required=True)  # type: ignore[untyped-decorator]
    async def resolve_erd_domain_class_aspect(
        self,
        params: GetErdDomainPayloadAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        qual = params.domain_qualname.strip()
        if "." not in qual:
            msg = f"Invalid domain type qualname: {qual!r}"
            raise ValueError(msg)
        parts = qual.split(".")
        for mod_len in range(len(parts) - 1, 0, -1):
            mod_name = ".".join(parts[:mod_len])
            attr_path = parts[mod_len:]
            try:
                module = importlib.import_module(mod_name)
            except ModuleNotFoundError:
                continue
            obj: Any = module
            try:
                for attr in attr_path:
                    obj = getattr(obj, attr)
            except AttributeError:
                continue
            if isinstance(obj, type) and issubclass(obj, BaseDomain):
                domain_cls: type[BaseDomain] = obj
                return {"erd_domain_class": domain_cls}
        msg = f"Not a BaseDomain subclass or not importable: {qual!r}"
        raise TypeError(msg)

    @summary_aspect("Build ERD graph JSON for one domain")
    async def build_domain_payload_summary(
        self,
        params: GetErdDomainPayloadAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetErdDomainPayloadAction.Result:
        nx_resource = cast(ServiceGraphResource, connections[SERVICE_GRAPH_CONNECTION_KEY])
        coordinator = node_graph_coordinator_from_interchange_nx(nx_resource.service)
        qual = params.domain_qualname.strip()
        dc = cast(type[BaseDomain], state["erd_domain_class"])
        payload = erd_payload_from_coordinator_for_domain(coordinator, dc)
        base = getattr(dc, "name", None) or dc.__name__
        return GetErdDomainPayloadAction.Result(
            domain_label=str(base),
            domain_qualifier=qual,
            graph=payload_to_domain_dict(payload),
        )
