# tests/action_machine/resources/test_in_memory_and_external_service_data_sources.py
"""The two kinds of data source beside PostgreSQL: a store kept in memory, and an external service.

The data sources of this module serve no resource, so they stay out of the graph every other test builds.
"""

from __future__ import annotations

import pytest

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource, ExternalServiceDataSource, InMemoryDataSource


@exclude_graph_model
@meta(description="Catalog kept in memory")
class _CatalogDataSource(InMemoryDataSource):
    pass


@exclude_graph_model
@meta(description="Card network")
class _CardNetworkDataSource(ExternalServiceDataSource):
    pass


class _Client:
    """A client that says whether it was closed."""

    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def test_both_are_data_sources() -> None:
    assert issubclass(InMemoryDataSource, BaseDataSource)
    assert issubclass(ExternalServiceDataSource, BaseDataSource)


async def test_an_in_memory_store_is_one_mapping_until_it_closes() -> None:
    """Every resource reads and writes the same mapping; closing empties it."""
    async with _CatalogDataSource() as catalog:
        catalog.store["sku-1"] = {"title": "Lamp"}
        assert catalog.store == {"sku-1": {"title": "Lamp"}}
        assert catalog.store is catalog.store
    assert catalog.store == {}


def test_an_in_memory_store_may_start_from_given_rows() -> None:
    rows = {"sku-1": {"title": "Lamp"}}
    assert _CatalogDataSource(rows).store is rows


async def test_an_external_service_keeps_its_address_credentials_and_client() -> None:
    """What the resources share is given once; a shared client is left open."""
    client = _Client()
    async with _CardNetworkDataSource("https://cards.example", credentials={"key": "k"}, client=client) as cards:
        assert (cards.base_url, dict(cards.credentials), cards.client) == ("https://cards.example", {"key": "k"}, client)
    assert client.closed is False


@pytest.mark.parametrize("close_client", [True, False])
async def test_an_external_service_closes_only_a_client_it_owns(close_client: bool) -> None:
    client = _Client()
    await _CardNetworkDataSource(client=client, close_client=close_client).close()
    assert client.closed is close_client
