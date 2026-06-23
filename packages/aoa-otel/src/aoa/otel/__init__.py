# packages/aoa-action-machine/src/aoa/action_machine/plugin/open_telemetry/__init__.py
"""
OpenTelemetry plugin for ActionMachine — optional extra ``aoa-action-machine[otel]``.

Install::

    pip install "aoa-action-machine[otel]"

Usage::

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    plugin = OpenTelemetryPlugin(tracer_provider=provider)
"""

from __future__ import annotations

from aoa.action_machine.plugin.open_telemetry.plugin import OpenTelemetryPlugin

__all__ = ["OpenTelemetryPlugin"]
