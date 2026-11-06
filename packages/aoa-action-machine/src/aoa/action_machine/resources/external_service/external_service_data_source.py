# packages/aoa-action-machine/src/aoa/action_machine/resources/external_service/external_service_data_source.py
"""
ExternalServiceDataSource — an external service several resources call: its address, credentials and client.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An entity an external service keeps — a payment, a shipment, a message in a mailbox —
has a physical place too: the service. ``ExternalServiceDataSource`` is that place. It
keeps what every resource calling the service shares: the base address, the
credentials and the client — an HTTP client with keep-alive, an SDK handle. A resource
asks the data source for the client; the data source decides how connections are kept.

An application derives its own data source from this kind and creates it once; it
passes the instance to every resource that names it. Resources of several domains may
share one, one resource per domain::

    @meta(description="Card network")
    class CardNetworkDataSource(ExternalServiceDataSource): ...

    async with CardNetworkDataSource("https://cards.example", credentials={"key": "…"}, client=http) as cards:
        PaymentsGateway(data_source=cards)

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- The base address, the credentials and the client are given once and never change.
- The data source closes a client only when it was given ``close_client=True``: a client
  the application shares with others is closed by the application.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_data_source import BaseDataSource


@exclude_graph_model
class ExternalServiceDataSource(BaseDataSource):
    """
    AI-CORE-BEGIN
    ROLE: The kind of data source of an external service: base address, credentials and client.
    CONTRACT: ``base_url``, ``credentials`` and ``client`` as given; ``open``/``close`` and ``async with``; ``close`` closes the client only when built with ``close_client=True``.
    INVARIANTS: Holds no transaction; never changes its address, credentials or client.
    AI-CORE-END
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        credentials: Mapping[str, str] | None = None,
        client: Any = None,
        close_client: bool = False,
    ) -> None:
        """
        Keep what the resources of this service share.

        Args:
            base_url: the address of the service; ``None`` when the client knows it.
            credentials: the keys or tokens the service asks for; empty when it asks for none.
            client: the client the resources call the service through; ``None`` when they make their own calls.
            close_client: whether ``close()`` closes the client — only for a client made for this data source.
        """
        self._base_url = base_url
        self._credentials: dict[str, str] = dict(credentials or {})
        self._client = client
        self._close_client = close_client

    @property
    def base_url(self) -> str | None:
        """The address of the service."""
        return self._base_url

    @property
    def credentials(self) -> Mapping[str, str]:
        """The keys or tokens the service asks for."""
        return self._credentials

    @property
    def client(self) -> Any:
        """The client the resources call the service through."""
        return self._client

    async def open(self) -> None:
        """Nothing to open: the client is ready when it is given."""

    async def close(self) -> None:
        """Close the client when this data source was made its owner."""
        if not self._close_client or self._client is None:
            return
        for name in ("aclose", "close"):
            if callable(getattr(self._client, name, None)):
                result = getattr(self._client, name)()
                if inspect.isawaitable(result):
                    await result
                return

    async def __aenter__(self) -> ExternalServiceDataSource:
        """Open, and give the data source to the ``async with`` block."""
        await self.open()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close, whatever the block raised."""
        await self.close()
