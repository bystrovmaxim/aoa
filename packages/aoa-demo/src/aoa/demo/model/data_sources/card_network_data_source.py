# packages/aoa-demo/src/aoa/demo/model/data_sources/card_network_data_source.py
"""CardNetworkDataSource — the card network service."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import ExternalServiceDataSource


@meta(description="The card network service")
class CardNetworkDataSource(ExternalServiceDataSource):
    """A demo external service: the card network a payment's events come from."""
