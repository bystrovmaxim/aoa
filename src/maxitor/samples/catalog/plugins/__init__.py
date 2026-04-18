# src/maxitor/samples/catalog/plugins/__init__.py
from maxitor.samples.catalog.plugins.after_enrich_plugin import CatalogAfterEnrichPlugin
from maxitor.samples.catalog.plugins.global_finish_plugin import CatalogGlobalFinishPlugin
from maxitor.samples.catalog.plugins.unhandled_error_plugin import CatalogUnhandledErrorSwallowPlugin

__all__ = [
    "CatalogAfterEnrichPlugin",
    "CatalogGlobalFinishPlugin",
    "CatalogUnhandledErrorSwallowPlugin",
]
