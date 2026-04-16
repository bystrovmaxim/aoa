# src/maxitor/test_domain/plugins/__init__.py
"""Плагины test_domain — отдельный модуль на класс."""

from maxitor.test_domain.plugins.after_charge_plugin import TestAfterChargeAspectPlugin
from maxitor.test_domain.plugins.global_finish_plugin import TestGlobalFinishPlugin
from maxitor.test_domain.plugins.unhandled_error_plugin import TestUnhandledErrorPlugin

__all__ = [
    "TestAfterChargeAspectPlugin",
    "TestGlobalFinishPlugin",
    "TestUnhandledErrorPlugin",
]
