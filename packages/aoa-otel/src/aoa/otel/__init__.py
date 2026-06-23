# packages/aoa-otel/src/aoa/otel/__init__.py
"""
OpenTelemetry plugin for AOA.

Install::

    pip install aoa-otel

Usage::

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    from aoa.otel import OpenTelemetryPlugin

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    plugin = OpenTelemetryPlugin(tracer_provider=provider)
"""

from __future__ import annotations

from aoa.otel.plugin import OpenTelemetryPlugin

__all__ = ["OpenTelemetryPlugin"]
