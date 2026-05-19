# packages/aoa-examples/src/aoa/examples/model/catalog/plugins/__init__.py
from aoa.examples.model.catalog.plugins.after_enrich_plugin import CatalogAfterEnrichPlugin
from aoa.examples.model.catalog.plugins.global_finish_plugin import CatalogGlobalFinishPlugin
from aoa.examples.model.catalog.plugins.unhandled_error_plugin import CatalogUnhandledErrorSwallowPlugin

__all__ = [
    "CatalogAfterEnrichPlugin",
    "CatalogGlobalFinishPlugin",
    "CatalogUnhandledErrorSwallowPlugin",
]
