# tests/action_machine/runtime/test_action_product_machine_init.py
"""Tests for ActionProductMachine initialization — logger and plugin wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.console_logger import ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.plugin.core.plugin import Plugin
from aoa.action_machine.plugin.core.plugin_coordinator import PluginCoordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator

# ---------------------------------------------------------------------------
# Loggers
# ---------------------------------------------------------------------------


def test_default_console_logger_added_when_nothing_passed() -> None:
    machine = ActionProductMachine(cache_coordinator=None)
    assert len(machine._log_coordinator._loggers) == 1
    assert isinstance(machine._log_coordinator._loggers[0], ConsoleLogger)


def test_no_default_logger_when_loggers_empty_list() -> None:
    machine = ActionProductMachine(loggers=[], cache_coordinator=None)
    assert machine._log_coordinator._loggers == []


def test_explicit_loggers_added_when_no_coordinator_passed() -> None:
    logger = MagicMock(spec=BaseLogger)
    machine = ActionProductMachine(loggers=[logger], cache_coordinator=None)
    assert logger in machine._log_coordinator._loggers


def test_no_default_logger_when_log_coordinator_passed() -> None:
    lc = LogCoordinator(loggers=[])
    machine = ActionProductMachine(log_coordinator=lc, cache_coordinator=None)
    assert machine._log_coordinator._loggers == []


def test_loggers_added_to_passed_log_coordinator() -> None:
    lc = LogCoordinator(loggers=[])
    logger = MagicMock(spec=BaseLogger)
    machine = ActionProductMachine(log_coordinator=lc, loggers=[logger], cache_coordinator=None)
    assert logger in machine._log_coordinator._loggers
    assert machine._log_coordinator is lc


# ---------------------------------------------------------------------------
# Plugins
# ---------------------------------------------------------------------------


def test_no_plugins_by_default() -> None:
    machine = ActionProductMachine(cache_coordinator=None)
    assert machine._plugin_coordinator.plugins == []


def test_plugins_added_when_no_coordinator_passed() -> None:
    plugin = MagicMock(spec=Plugin)
    machine = ActionProductMachine(plugins=[plugin], cache_coordinator=None)
    assert plugin in machine._plugin_coordinator.plugins


def test_plugins_added_to_passed_plugin_coordinator() -> None:
    pc = PluginCoordinator()
    plugin = MagicMock(spec=Plugin)
    machine = ActionProductMachine(plugin_coordinator=pc, plugins=[plugin], cache_coordinator=None)
    assert plugin in machine._plugin_coordinator.plugins
    assert machine._plugin_coordinator is pc


def test_plugin_coordinator_passed_without_plugins_unchanged() -> None:
    pc = PluginCoordinator()
    machine = ActionProductMachine(plugin_coordinator=pc, cache_coordinator=None)
    assert machine._plugin_coordinator.plugins == []
    assert machine._plugin_coordinator is pc


# ---------------------------------------------------------------------------
# Cache coordinator
# ---------------------------------------------------------------------------


def test_default_cache_coordinator_created_when_nothing_passed() -> None:
    machine = ActionProductMachine()
    assert isinstance(machine._cache_coordinator, CacheCoordinator)


def test_no_cache_coordinator_when_none_passed_explicitly() -> None:
    machine = ActionProductMachine(cache_coordinator=None)
    assert machine._cache_coordinator is None


def test_explicit_cache_coordinator_used_when_passed() -> None:
    cc = CacheCoordinator()
    machine = ActionProductMachine(cache_coordinator=cc)
    assert machine._cache_coordinator is cc
