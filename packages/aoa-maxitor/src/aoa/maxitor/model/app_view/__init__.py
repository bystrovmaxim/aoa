# packages/aoa-maxitor/src/aoa/maxitor/model/app_view/__init__.py
"""App view actions for assembling sidebar-friendly data."""

from .actions import GetLeftMenuSidebarDataAction
from .app_view_domen_domain import AppViewDomenDomain

__all__ = [
    "AppViewDomenDomain",
    "GetLeftMenuSidebarDataAction",
]

