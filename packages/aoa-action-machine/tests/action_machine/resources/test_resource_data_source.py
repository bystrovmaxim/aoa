# tests/action_machine/resources/test_resource_data_source.py
"""
A resource names its data source as the type argument of its base.

``class OrdersResource(BaseStorage[ShopDataSource])`` names ``ShopDataSource``; a resource
that inherits a base without a type argument names none. A data source outside the bound of
the parameter it fills, and a second data source in one hierarchy, are refused when the class
is created; an instance of another class, or none where one is named, is refused at run time.
The graph shows a ``resource_data_source`` edge from each resource that names a data source.
Classes the interpreter keeps here are excluded from the graph model; the graph itself is
built in a fresh interpreter.
"""

from __future__ import annotations

import json
import textwrap

import jsonschema
import pytest

from aoa.action_machine.exceptions.data_source_declaration_error import DataSourceDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseController, BaseDataSource, BaseGateway, BaseStorage

from ...support.isolated_entity_models import run_isolated_model


@exclude_graph_model
@meta(description="Main shop database")
class _ShopDataSource(BaseDataSource):
    pass


@exclude_graph_model
@meta(description="Billing database")
class _BillingDataSource(BaseDataSource):
    pass


@exclude_graph_model
class _RelationalDataSource(BaseDataSource):
    """A kind of data source: the bound of a narrower resource base."""


@exclude_graph_model
class _RelationalStorage[D: _RelationalDataSource](BaseStorage[D]):
    """A kind of storage that takes only a relational data source."""

    def get_wrapper_class(self) -> None:
        return None


@exclude_graph_model
class _OrdersStorage(BaseStorage[_ShopDataSource]):
    def get_wrapper_class(self) -> None:
        return None


@exclude_graph_model
class _SessionStorage(BaseStorage):  # type: ignore[type-arg]
    def get_wrapper_class(self) -> None:
        return None


def test_a_resource_names_its_data_source_through_its_base() -> None:
    """The type argument of the base is the resource's data source; every kind of resource takes one."""
    assert _OrdersStorage.data_source_type() is _ShopDataSource

    @exclude_graph_model
    class _MailGateway(BaseGateway[_ShopDataSource]):
        def get_wrapper_class(self) -> None:
            return None

    @exclude_graph_model
    class _RoomController(BaseController[_ShopDataSource]):
        def get_wrapper_class(self) -> None:
            return None

    assert _MailGateway.data_source_type() is _ShopDataSource
    assert _RoomController.data_source_type() is _ShopDataSource


def test_a_resource_without_a_type_argument_has_no_data_source() -> None:
    """A data source is optional."""
    assert _SessionStorage.data_source_type() is None


def test_a_data_source_of_the_wrong_kind_is_refused() -> None:
    """A data source outside the bound of its parameter is refused when the class is created."""
    with pytest.raises(DataSourceDeclarationError, match=r"_RelationalStorage\[_ShopDataSource\] needs a data source of the kind _RelationalDataSource"):

        class _LedgerStorage(_RelationalStorage[_ShopDataSource]):  # type: ignore[type-var]
            pass


def test_a_second_data_source_is_refused() -> None:
    """A resource hierarchy names at most one data source."""

    @exclude_graph_model
    class _Shared[D: BaseDataSource](BaseStorage[_ShopDataSource]):
        def get_wrapper_class(self) -> None:
            return None

    with pytest.raises(DataSourceDeclarationError, match="a resource has one data source; its bases name _BillingDataSource, _ShopDataSource"):

        class _Both(_Shared[_BillingDataSource]):
            pass


def test_the_data_source_given_at_run_time_is_checked() -> None:
    """An instance of the declared class passes; another class, or none, is refused; a resource without one takes none."""
    _OrdersStorage._check_data_source(_ShopDataSource())
    with pytest.raises(DataSourceDeclarationError, match="_OrdersStorage works through _ShopDataSource: pass data_source= of that class; got _BillingDataSource"):
        _OrdersStorage._check_data_source(_BillingDataSource())
    with pytest.raises(DataSourceDeclarationError, match="got none"):
        _OrdersStorage._check_data_source(None)
    _SessionStorage._check_data_source(None)
    with pytest.raises(DataSourceDeclarationError, match="_SessionStorage names no data source, so it takes none"):
        _SessionStorage._check_data_source(_ShopDataSource())


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
    class OrdersResource(BaseStorage[ShopDataSource]):
        def get_wrapper_class(self):
            return None


    @meta(description="Support", domain=ShopDomain)
    class SupportResource(BaseStorage[ShopDataSource]):
        def get_wrapper_class(self):
            return None


    @meta(description="Sessions", domain=ShopDomain)
    class SessionResource(BaseStorage):
        def get_wrapper_class(self):
            return None


    print(create_node_graph_coordinator().to_json())
    """
)


def test_the_graph_has_an_edge_from_each_resource_that_names_a_data_source() -> None:
    """Two ``resource_data_source`` edges to ``ShopDataSource``; none from the resource without one; valid against 1.7."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    graph = json.loads(result.stdout)
    jsonschema.Draft202012Validator(GRAPH_JSON_SCHEMA).validate(graph)
    rows = [e for e in graph["edges"] if e["type"] == "resource_data_source"]
    assert sorted(e["source_id"].rsplit(".", 1)[-1] for e in rows) == ["OrdersResource", "SupportResource"]
    assert {e["target_id"].rsplit(".", 1)[-1] for e in rows} == {"ShopDataSource"}
    assert {(e["relationship"], e["is_dag"], json.dumps(e["properties"])) for e in rows} == {("Aggregation", True, "{}")}
    assert all(e["id"] == f"{e['source_id']}|resource_data_source|{e['target_id']}" for e in rows)
