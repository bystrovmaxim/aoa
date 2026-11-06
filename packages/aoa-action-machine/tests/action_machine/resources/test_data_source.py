# tests/action_machine/resources/test_data_source.py
"""
``BaseDataSource``: a store several resources share.

A data source declares ``@meta(description=...)`` and no domain, its class name ends in
``DataSource``, an action cannot depend on it, and the graph shows it as a ``DataSource``
node hanging on the application. Classes declared here that the interpreter keeps are
excluded from the graph model, so they never reach a graph another test builds; the graph
itself is built in a fresh interpreter.
"""

from __future__ import annotations

import json
import textwrap

import jsonschema
import pytest

from aoa.action_machine.domain import BaseDomain
from aoa.action_machine.exceptions.dependency_declaration_error import DependencyDeclarationError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources import BaseDataSource, BaseStorage

from ...support.isolated_entity_models import run_isolated_model


class _ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop"


@exclude_graph_model
@meta(description="Main shop database")
class _ShopDataSource(BaseDataSource):
    pass


def test_a_data_source_declares_a_description_and_no_domain() -> None:
    """``@meta(description=...)`` alone is a data source's whole declaration."""
    assert MetaIntentResolver.resolve_description(_ShopDataSource) == "Main shop database"
    assert _ShopDataSource._meta_info["domain"] is None


def test_a_data_source_with_a_domain_is_refused() -> None:
    """A data source is physical: resources of several domains may share it."""
    with pytest.raises(TypeError, match="a data source has no domain"):

        @meta(description="Billing database", domain=_ShopDomain)
        @exclude_graph_model
        class _BillingDataSource(BaseDataSource):
            pass


def test_a_resource_without_a_domain_is_still_refused() -> None:
    """Only a data source goes without a domain."""
    with pytest.raises(TypeError, match="domain is required"):

        @meta(description="Orders")
        @exclude_graph_model
        class _OrdersStorage(BaseStorage):
            pass


def test_a_data_source_name_ends_in_data_source() -> None:
    """The suffix is checked when the class is created."""
    with pytest.raises(NamingSuffixError, match="ends in 'DataSource'"):

        class _ShopDatabase(BaseDataSource):
            pass


def test_an_action_cannot_depend_on_a_data_source() -> None:
    """An action reaches a data source only through a resource that names it."""
    with pytest.raises(DependencyDeclarationError, match="a data source is not a dependency"):

        @depends(_ShopDataSource)
        @exclude_graph_model
        class _CheckoutAction(BaseAction):  # type: ignore[type-arg]
            pass


_MODEL = textwrap.dedent(
    """
    from aoa.action_machine.domain import BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseDataSource, BaseStorage


    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Shop"


    @meta(description="Main shop database")
    class ShopDataSource(BaseDataSource):
        pass


    @meta(description="Orders", domain=ShopDomain)
    class OrdersStorage(BaseStorage[ShopDataSource]):
        @classmethod
        def get_wrapper_class(cls):
            return None


    print(create_node_graph_coordinator().to_json())
    """
)


def test_the_graph_shows_a_data_source_on_the_application() -> None:
    """One ``DataSource`` node with its description, one ``application`` edge, valid against schema 1.8."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    graph = json.loads(result.stdout)
    jsonschema.Draft202012Validator(GRAPH_JSON_SCHEMA).validate(graph)
    (node,) = [n for n in graph["nodes"] if n["type"] == "DataSource"]
    assert (node["label"], node["properties"]) == ("ShopDataSource", {"description": "Main shop database"})
    (edge,) = [e for e in graph["edges"] if e["source_id"] == node["id"]]  # its one edge: to the application
    assert (edge["type"], edge["relationship"], edge["is_dag"], edge["properties"]) == ("application", "Aggregation", True, {})
    assert edge["target_id"].endswith(".Application")
