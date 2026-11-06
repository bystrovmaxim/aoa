# packages/aoa-demo/src/aoa/demo/model/data_sources/billing_warehouse_data_source.py
"""BillingWarehouseDataSource — the billing warehouse database."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource


@meta(description="The billing warehouse database")
class BillingWarehouseDataSource(BaseDataSource):
    """A demo database: the billing warehouse."""
