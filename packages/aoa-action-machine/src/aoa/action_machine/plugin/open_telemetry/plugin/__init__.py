# packages/aoa-action-machine/src/aoa/action_machine/plugin/open_telemetry/plugin/__init__.py
"""
OpenTelemetryPlugin — emits OTel spans for action runs and their aspects.

Requires ``aoa-action-machine[otel]``.
"""

from aoa.action_machine.plugin.open_telemetry.plugin.open_telemetry_plugin import OpenTelemetryPlugin

__all__ = ["OpenTelemetryPlugin"]
