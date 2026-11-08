# tests/action_machine/graph/test_data_source_removal.py
"""
Phase 1 of issue #487 removed the data source layer: a resource is a database, and the model knows no store.

This module pins that removal from the outside in. Every module of the old layer is gone and
cannot be imported; the public facades no longer name its classes; a resource base takes no
type argument. The freed rule is pinned too: an action of one domain may depend on a resource
of another domain, and a built graph carries no ``DataSource`` node and no
``resource_data_source`` edge. Each model is built in a fresh interpreter.
"""

from __future__ import annotations

import importlib.util
import json
import textwrap
from typing import Any

import pytest

from aoa.action_machine import exceptions as exceptions_facade
from aoa.action_machine import resources as resources_facade
from aoa.action_machine.resources import BaseController, BaseGateway, BaseStorage

from ...support.isolated_entity_models import run_isolated_model

_REMOVED_MODULES = [
    "aoa.action_machine.resources.base_data_source",
    "aoa.action_machine.resources.data_source_resolver",
    "aoa.action_machine.resources.in_memory.in_memory_data_source",
    "aoa.action_machine.resources.external_service.external_service_data_source",
    "aoa.action_machine.graph.nodes.data_source_graph_node",
    "aoa.action_machine.graph.inspectors.data_source_graph_node_inspector",
    "aoa.action_machine.graph.edges.resource_data_source_graph_edge",
    "aoa.action_machine.graph.validators.entity_data_source_validator",
    "aoa.action_machine.graph.validators.resource_domain_validator",
    "aoa.action_machine.exceptions.data_source_declaration_error",
]

_REMOVED_RESOURCE_EXPORTS = ["BaseDataSource", "InMemoryDataSource", "ExternalServiceDataSource"]


@pytest.mark.parametrize("module_name", _REMOVED_MODULES)
def test_a_removed_module_cannot_be_imported(module_name: str) -> None:
    """Every module of the removed data source layer has no spec left to import."""
    try:
        spec = importlib.util.find_spec(module_name)
    except ModuleNotFoundError:
        spec = None
    assert spec is None


@pytest.mark.parametrize("name", _REMOVED_RESOURCE_EXPORTS)
def test_the_resources_facade_no_longer_exports_a_data_source(name: str) -> None:
    """The resources package names none of the removed data source classes."""
    assert name not in resources_facade.__all__
    assert not hasattr(resources_facade, name)


def test_the_exceptions_facade_no_longer_exports_the_declaration_error() -> None:
    """The declaration error of the removed layer is not exported any more."""
    assert "DataSourceDeclarationError" not in exceptions_facade.__all__
    assert not hasattr(exceptions_facade, "DataSourceDeclarationError")


def test_the_domain_facade_no_longer_exports_the_entity_resource_error() -> None:
    """The refusal of an entity whose resource named no data source went with the rule."""
    from aoa.action_machine import domain as domain_facade
    from aoa.action_machine.domain import exceptions as domain_exceptions

    assert "EntityResourceError" not in domain_facade.__all__
    assert not hasattr(domain_facade, "EntityResourceError")
    assert not hasattr(domain_exceptions, "EntityResourceError")


@pytest.mark.parametrize("resource_base", [BaseStorage, BaseGateway, BaseController])
def test_a_resource_base_refuses_a_type_argument(resource_base: type[Any]) -> None:
    """A resource base is no longer generic over the data source it works through."""
    with pytest.raises(TypeError):
        resource_base[object]  # type: ignore[index]


_MODEL = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.check_roles import GuestRole, check_roles
    from aoa.action_machine.intents.depends import depends
    from aoa.action_machine.intents.entities import entities
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.model.base_action import BaseAction
    from aoa.action_machine.model.base_params import BaseParams
    from aoa.action_machine.model.base_result import BaseResult


    class SalesDomain(BaseDomain):
        name = "sales"
        description = "Sales"


    class BillingDomain(BaseDomain):
        name = "billing"
        description = "Billing"


    @entity(description="Invoice", domain=BillingDomain)
    class InvoiceCoreEntity(BaseCoreEntity):
        id: str = Field(description="Invoice id")


    @meta(description="Billing ledger store")
    @entities(InvoiceCoreEntity)
    class BillingStorage(BaseStorage):
        @classmethod
        def get_wrapper_class(cls):
            return None


    @meta(description="Reads the billing ledger", domain=SalesDomain)
    @check_roles(GuestRole)
    @depends(BillingStorage, description="billing ledger")
    class ReadBillingAction(BaseAction["ReadBillingAction.Params", "ReadBillingAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            invoice_id: str = Field(description="Invoice id")


    print(create_node_graph_coordinator().to_json())
    """
)


@pytest.fixture(scope="module")
def built() -> dict[str, Any]:
    """The graph of a sales action that depends on a billing resource, built in a fresh interpreter."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _name(node_id: str) -> str:
    """The class name a node id ends with (a ``__main__`` class has no module prefix)."""
    return node_id.rsplit(".", 1)[-1]


def test_an_action_may_depend_on_a_resource_of_another_domain(built: dict[str, Any]) -> None:
    """The cross-domain dependency is in the graph: the rule that forbade it is gone."""
    dependencies = [edge for edge in built["edges"] if edge["type"] == "@depends"]
    assert any(
        _name(edge["source_id"]) == "ReadBillingAction" and _name(edge["target_id"]) == "BillingStorage"
        for edge in dependencies
    )


def test_the_built_graph_has_no_data_source_node(built: dict[str, Any]) -> None:
    """No node of the removed ``DataSource`` type reaches the graph."""
    assert all(node["type"] != "DataSource" for node in built["nodes"])


def test_the_built_graph_has_no_resource_data_source_edge(built: dict[str, Any]) -> None:
    """A resource no longer names a data source in the graph."""
    assert all(edge["type"] != "resource_data_source" for edge in built["edges"])
