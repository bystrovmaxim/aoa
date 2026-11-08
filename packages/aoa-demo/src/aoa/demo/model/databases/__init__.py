# packages/aoa-demo/src/aoa/demo/model/databases/__init__.py
"""
The demo's databases — one module per database shared by more than one resource.

Only a database that several domains reach through resources of their own lives
here: it is one resource listing every entity of those domains. A database that
one storage already owns stays with that storage where it is.

``ShopDatabaseStorage`` is the database of the storefront, the support desk and
inventory — three domains, one resource, one ``@entities`` list.
"""

from aoa.demo.model.databases.shop_database_storage import ShopDatabaseStorage

__all__ = ["ShopDatabaseStorage"]
