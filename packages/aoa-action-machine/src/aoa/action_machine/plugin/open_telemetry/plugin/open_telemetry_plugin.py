# packages/aoa-action-machine/src/aoa/action_machine/plugin/open_telemetry/plugin/open_telemetry_plugin.py
"""
OpenTelemetryPlugin — distributed tracing and state x-ray for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers the full ActionMachine event surface via two independent OTel signals:

**OTel Traces** (``tracer_provider``) — timing and execution structure:
- One root span per action run with child spans per aspect, @on_error handler,
  and compensator.
- Saga rollback events recorded as timed span events on the root span.
- Exception recording and ERROR status on failures.

**OTel Logs** (``logger_provider``) — state x-ray and self-sufficient audit:
- Emits a log record for every lifecycle event (start, each step, finish, error).
- Includes ``aoa.state.<field>`` attributes with per-field serialization of
  ``aspect_result`` so each aspect's state contribution is inspectable.
- Self-sufficient: carries all timing and identity fields from Traces, so it
  works standalone without a tracer_provider.
- Correlated with Traces via OTel ``trace_id`` / ``span_id`` from the root span
  context, plus ``aoa.trace_id`` from ``context.request.trace_id``.

At least one of ``tracer_provider`` / ``logger_provider`` is required.

Requires ``aoa-action-machine[otel]``::

    pip install "aoa-action-machine[otel]"

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GlobalStartEvent
        Traces → root span started (aoa.action, aoa.nest_level)
        Logs   → "aoa.action.start" record

    BeforeRegularAspect / BeforeSummary / BeforeOnError / BeforeCompensate
        Traces → child span started
        Logs   → "<event>.before" record

    AfterRegularAspect / AfterSummary / AfterOnError / AfterCompensate
        Traces → child span closed (aoa.duration_ms, OK)
        Logs   → "<event>.after" record + aoa.state.<field> per aspect_result key

    CompensateFailedEvent
        Traces → compensator span closed (ERROR, record_exception)
        Logs   → "aoa.compensate.failed" record WARN

    SagaRollbackStartedEvent / SagaRollbackCompletedEvent
        Traces → root_span.add_event(...)
        Logs   → saga record WARN

    GlobalFinishEvent
        Traces → root span closed (aoa.duration_ms, OK)
        Logs   → "aoa.action.finish" record + aoa.result.<field>

    UnhandledErrorEvent
        Traces → root span closed (ERROR, record_exception)
        Logs   → "aoa.action.error" record ERROR

═══════════════════════════════════════════════════════════════════════════════
CORRELATION FIELDS (written to both signals when both are active)
═══════════════════════════════════════════════════════════════════════════════

    aoa.trace_id   — context.request.trace_id (application-level, if set)
    OTel trace_id  — from root span context (OTel-native, for backend linking)
    OTel span_id   — from root span context (OTel-native, for backend linking)

═══════════════════════════════════════════════════════════════════════════════
STATE SERIALIZATION
═══════════════════════════════════════════════════════════════════════════════

Each field in ``aspect_result`` is serialized individually:
- Primitives (str, int, float, bool, None) — written as-is.
- Complex objects — ``json.dumps(value, default=repr)`` truncated to
  ``max_field_length`` chars with ``...[truncated]`` suffix.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

Traces only (timing)::

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
    from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin

    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    plugin = OpenTelemetryPlugin(tracer_provider=tp)

Logs only (state x-ray, no timing backend)::

    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import ConsoleLogExporter, SimpleLogRecordProcessor
    from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin

    lp = LoggerProvider()
    lp.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogExporter()))
    plugin = OpenTelemetryPlugin(logger_provider=lp)

Both signals (full observability)::

    plugin = OpenTelemetryPlugin(tracer_provider=tp, logger_provider=lp)
"""

from __future__ import annotations

import json
import time
from typing import Any

from opentelemetry import trace
from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.context import Context as OtelContext
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span, StatusCode, TraceFlags

from aoa.action_machine.intents.on import (
    AfterCompensateAspectEvent,
    AfterOnErrorAspectEvent,
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BeforeCompensateAspectEvent,
    BeforeOnErrorAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    CompensateFailedEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
    UnhandledErrorEvent,
    on,
)
from aoa.action_machine.plugin.core import Plugin
from aoa.action_machine.plugin.core.events import BasePluginEvent

_SPAN_KEY = "root_span"
_CTX_KEY = "root_ctx"
_ASPECT_SPANS_KEY = "aspect_spans"


class OpenTelemetryPlugin(Plugin):
    """
    AI-CORE-BEGIN
    ROLE: Emit OTel Traces and/or OTel Logs for the full ActionMachine event surface.
    CONTRACT: At least one of tracer_provider / logger_provider required; one root
        span per GlobalStartEvent; child spans per aspect / @on_error / compensator;
        log records for every event with per-field state serialization in After* events;
        explicit OTel Context ensures correct parent–child nesting in concurrent async runs.
    INVARIANTS: All span refs live in per-run plugin state (no instance mutation);
        spans always closed on finish / error / compensator failure;
        _emit_log is a no-op when logger_provider was not provided.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        tracer_provider: TracerProvider | None = None,
        logger_provider: LoggerProvider | None = None,
        service_name: str = "aoa",
        max_field_length: int = 500,
        watch_actions: frozenset[type] | None = None,
        watch_events: frozenset[type] | None = None,
    ) -> None:
        if tracer_provider is None and logger_provider is None:
            raise ValueError("OpenTelemetryPlugin requires at least one of tracer_provider or logger_provider.")
        super().__init__(watch_actions=watch_actions, watch_events=watch_events)
        self._tracer = tracer_provider.get_tracer(service_name) if tracer_provider else None
        self._otel_logger = logger_provider.get_logger(service_name) if logger_provider else None
        self._max_field_length = max_field_length

    async def get_initial_state(self) -> dict[str, Any]:
        return {
            _SPAN_KEY: None,
            _CTX_KEY: None,
            _ASPECT_SPANS_KEY: {},
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Action lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    @on(GlobalStartEvent, ignore_exceptions=False)
    async def on_action_start(
        self,
        state: dict[str, Any],
        event: GlobalStartEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Start root span (Traces) and emit start log record (Logs)."""
        span: Span | None = None
        ctx = None
        if self._tracer is not None:
            span = self._tracer.start_span(
                name=event.action_name,
                attributes={
                    "aoa.action": event.action_name,
                    "aoa.nest_level": event.nest_level,
                },
            )
            ctx = trace.set_span_in_context(span)

        self._emit_log(
            body="aoa.action.start",
            attributes={
                "aoa.action": event.action_name,
                "aoa.nest_level": event.nest_level,
            },
            span=span,
            event=event,
        )
        return {**state, _SPAN_KEY: span, _CTX_KEY: ctx, _ASPECT_SPANS_KEY: {}}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_action_finish(
        self,
        state: dict[str, Any],
        event: GlobalFinishEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Close root span with OK (Traces) and emit finish log with result fields (Logs)."""
        root_span: Span | None = state.get(_SPAN_KEY)
        if self._tracer is not None:
            for span in state.get(_ASPECT_SPANS_KEY, {}).values():
                if span is not None and span.is_recording():
                    span.set_status(StatusCode.OK)
                    span.end()
        if root_span is not None and root_span.is_recording():
            root_span.set_attribute("aoa.duration_ms", event.duration_ms)
            root_span.set_status(StatusCode.OK)
            root_span.end()

        self._emit_log(
            body="aoa.action.finish",
            attributes={
                "aoa.action": event.action_name,
                "aoa.duration_ms": event.duration_ms,
                **self._result_attributes(event.result),
            },
            span=root_span,
            event=event,
        )
        return {**state, _SPAN_KEY: None, _CTX_KEY: None}

    @on(UnhandledErrorEvent, ignore_exceptions=False)
    async def on_unhandled_error(
        self,
        state: dict[str, Any],
        event: UnhandledErrorEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Record exception on root span with ERROR status (Traces) and emit error log (Logs)."""
        root_span: Span | None = state.get(_SPAN_KEY)
        if self._tracer is not None:
            for span in state.get(_ASPECT_SPANS_KEY, {}).values():
                if span is not None and span.is_recording():
                    span.record_exception(event.error)
                    span.set_status(StatusCode.ERROR, description=str(event.error))
                    span.end()
        if root_span is not None and root_span.is_recording():
            root_span.record_exception(event.error)
            root_span.set_status(StatusCode.ERROR, description=str(event.error))
            root_span.end()

        self._emit_log(
            body="aoa.action.error",
            attributes={
                "aoa.action": event.action_name,
                "aoa.error": str(event.error),
                "aoa.error_type": type(event.error).__name__,
            },
            severity=SeverityNumber.ERROR,
            span=root_span,
            event=event,
        )
        return {**state, _SPAN_KEY: None, _CTX_KEY: None}

    # ─────────────────────────────────────────────────────────────────────────
    # Regular aspects
    # ─────────────────────────────────────────────────────────────────────────

    @on(BeforeRegularAspectEvent, ignore_exceptions=False)
    async def on_regular_aspect_start(
        self,
        state: dict[str, Any],
        event: BeforeRegularAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Start child span for regular aspect (Traces) and emit before-log (Logs)."""
        new_state = state
        if self._tracer is not None:
            new_state = _start_aspect_span(state, event.aspect_name, event.action_name, self._tracer)

        self._emit_log(
            body="aoa.aspect.regular.before",
            attributes={
                "aoa.action": event.action_name,
                "aoa.aspect": event.aspect_name,
            },
            span=state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    @on(AfterRegularAspectEvent, ignore_exceptions=False)
    async def on_regular_aspect_end(
        self,
        state: dict[str, Any],
        event: AfterRegularAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Close regular aspect span (Traces) and emit after-log with state x-ray (Logs)."""
        aspect_span: Span | None = state.get(_ASPECT_SPANS_KEY, {}).get(event.aspect_name) if self._tracer else None
        new_state = _end_aspect_span(state, event.aspect_name, event.duration_ms) if self._tracer else state
        self._emit_log(
            body="aoa.aspect.regular.after",
            attributes={
                "aoa.action": event.action_name,
                "aoa.aspect": event.aspect_name,
                "aoa.duration_ms": event.duration_ms,
                **self._state_attributes(event.aspect_result, event.opaque_fields),
            },
            span=aspect_span if aspect_span is not None else state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    # ─────────────────────────────────────────────────────────────────────────
    # Summary aspect
    # ─────────────────────────────────────────────────────────────────────────

    @on(BeforeSummaryAspectEvent, ignore_exceptions=False)
    async def on_summary_aspect_start(
        self,
        state: dict[str, Any],
        event: BeforeSummaryAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Start child span for summary aspect (Traces) and emit before-log (Logs)."""
        new_state = state
        if self._tracer is not None:
            new_state = _start_aspect_span(state, event.aspect_name, event.action_name, self._tracer)

        self._emit_log(
            body="aoa.aspect.summary.before",
            attributes={
                "aoa.action": event.action_name,
                "aoa.aspect": event.aspect_name,
            },
            span=state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    @on(AfterSummaryAspectEvent, ignore_exceptions=False)
    async def on_summary_aspect_end(
        self,
        state: dict[str, Any],
        event: AfterSummaryAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Close summary aspect span (Traces) and emit after-log with result fields (Logs)."""
        aspect_span: Span | None = state.get(_ASPECT_SPANS_KEY, {}).get(event.aspect_name) if self._tracer else None
        new_state = _end_aspect_span(state, event.aspect_name, event.duration_ms) if self._tracer else state

        self._emit_log(
            body="aoa.aspect.summary.after",
            attributes={
                "aoa.action": event.action_name,
                "aoa.aspect": event.aspect_name,
                "aoa.duration_ms": event.duration_ms,
                **self._result_attributes(event.result),
            },
            span=aspect_span if aspect_span is not None else state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    # ─────────────────────────────────────────────────────────────────────────
    # @on_error handlers
    # ─────────────────────────────────────────────────────────────────────────

    @on(BeforeOnErrorAspectEvent, ignore_exceptions=False)
    async def on_on_error_aspect_start(
        self,
        state: dict[str, Any],
        event: BeforeOnErrorAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Start child span for @on_error handler (Traces) and emit before-log (Logs)."""
        new_state = state
        if self._tracer is not None:
            new_state = _start_aspect_span(state, event.aspect_name, event.action_name, self._tracer)

        self._emit_log(
            body="aoa.on_error.before",
            attributes={
                "aoa.action": event.action_name,
                "aoa.aspect": event.aspect_name,
                "aoa.error": str(event.error),
                "aoa.error_type": type(event.error).__name__,
            },
            severity=SeverityNumber.WARN,
            span=state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    @on(AfterOnErrorAspectEvent, ignore_exceptions=False)
    async def on_on_error_aspect_end(
        self,
        state: dict[str, Any],
        event: AfterOnErrorAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Close @on_error handler span (Traces) and emit after-log with result (Logs)."""
        aspect_span: Span | None = state.get(_ASPECT_SPANS_KEY, {}).get(event.aspect_name) if self._tracer else None
        new_state = _end_aspect_span(state, event.aspect_name, event.duration_ms) if self._tracer else state

        self._emit_log(
            body="aoa.on_error.after",
            attributes={
                "aoa.action": event.action_name,
                "aoa.aspect": event.aspect_name,
                "aoa.duration_ms": event.duration_ms,
                **self._result_attributes(event.handler_result),
            },
            span=aspect_span if aspect_span is not None else state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    # ─────────────────────────────────────────────────────────────────────────
    # Compensators (Saga rollback steps)
    # ─────────────────────────────────────────────────────────────────────────

    @on(BeforeCompensateAspectEvent, ignore_exceptions=False)
    async def on_compensate_start(
        self,
        state: dict[str, Any],
        event: BeforeCompensateAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Start child span for compensator (Traces) and emit before-log (Logs)."""
        new_state = state
        if self._tracer is not None:
            root_ctx: OtelContext | None = state.get(_CTX_KEY)
            span = self._tracer.start_span(
                name=event.compensator_name,
                context=root_ctx,
                attributes={
                    "aoa.compensator": event.compensator_name,
                    "aoa.aspect": event.aspect_name,
                    "aoa.action": event.action_name,
                },
            )
            aspect_spans: dict[str, Span] = {**state.get(_ASPECT_SPANS_KEY, {}), event.compensator_name: span}
            new_state = {**state, _ASPECT_SPANS_KEY: aspect_spans}

        self._emit_log(
            body="aoa.compensate.before",
            attributes={
                "aoa.action": event.action_name,
                "aoa.compensator": event.compensator_name,
                "aoa.aspect": event.aspect_name,
            },
            severity=SeverityNumber.WARN,
            span=state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    @on(AfterCompensateAspectEvent, ignore_exceptions=False)
    async def on_compensate_end(
        self,
        state: dict[str, Any],
        event: AfterCompensateAspectEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Close compensator span with OK (Traces) and emit after-log (Logs)."""
        aspect_span: Span | None = (
            state.get(_ASPECT_SPANS_KEY, {}).get(event.compensator_name) if self._tracer else None
        )
        new_state = _end_aspect_span(state, event.compensator_name, event.duration_ms) if self._tracer else state

        self._emit_log(
            body="aoa.compensate.after",
            attributes={
                "aoa.action": event.action_name,
                "aoa.compensator": event.compensator_name,
                "aoa.duration_ms": event.duration_ms,
            },
            span=aspect_span if aspect_span is not None else state.get(_SPAN_KEY),
            event=event,
        )
        return new_state

    @on(CompensateFailedEvent, ignore_exceptions=False)
    async def on_compensate_failed(
        self,
        state: dict[str, Any],
        event: CompensateFailedEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Close compensator span with ERROR (Traces) and emit failed-log (Logs)."""
        if self._tracer is not None:
            aspect_spans: dict[str, Span] = dict(state.get(_ASPECT_SPANS_KEY, {}))
            span = aspect_spans.pop(event.compensator_name, None)
            if span is not None and span.is_recording():
                span.record_exception(event.compensator_error)
                span.set_status(StatusCode.ERROR, description=str(event.compensator_error))
                span.end()
            state = {**state, _ASPECT_SPANS_KEY: aspect_spans}

        self._emit_log(
            body="aoa.compensate.failed",
            attributes={
                "aoa.action": event.action_name,
                "aoa.compensator": event.compensator_name,
                "aoa.compensator_error": str(event.compensator_error),
                "aoa.compensator_error_type": type(event.compensator_error).__name__,
            },
            severity=SeverityNumber.WARN,
            span=state.get(_SPAN_KEY),
            event=event,
        )
        return state

    # ─────────────────────────────────────────────────────────────────────────
    # Saga rollback lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    @on(SagaRollbackStartedEvent, ignore_exceptions=False)
    async def on_saga_rollback_started(
        self,
        state: dict[str, Any],
        event: SagaRollbackStartedEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Record rollback start as timed event on root span (Traces) and emit log (Logs)."""
        root_span: Span | None = state.get(_SPAN_KEY)
        if root_span is not None and root_span.is_recording():
            root_span.add_event(
                "saga.rollback.started",
                {
                    "aoa.saga.stack_depth": event.stack_depth,
                    "aoa.saga.compensator_count": event.compensator_count,
                    "aoa.saga.error": str(event.error),
                },
            )

        self._emit_log(
            body="aoa.saga.rollback.started",
            attributes={
                "aoa.action": event.action_name,
                "aoa.saga.stack_depth": event.stack_depth,
                "aoa.saga.compensator_count": event.compensator_count,
                "aoa.saga.error": str(event.error),
                "aoa.saga.error_type": type(event.error).__name__,
            },
            severity=SeverityNumber.WARN,
            span=root_span,
            event=event,
        )
        return state

    @on(SagaRollbackCompletedEvent, ignore_exceptions=False)
    async def on_saga_rollback_completed(
        self,
        state: dict[str, Any],
        event: SagaRollbackCompletedEvent,
        log: Any,
    ) -> dict[str, Any]:
        """Record rollback outcome as timed event on root span (Traces) and emit log (Logs)."""
        root_span: Span | None = state.get(_SPAN_KEY)
        if root_span is not None and root_span.is_recording():
            root_span.add_event(
                "saga.rollback.completed",
                {
                    "aoa.saga.total": event.total_frames,
                    "aoa.saga.succeeded": event.succeeded,
                    "aoa.saga.failed": event.failed,
                    "aoa.saga.skipped": event.skipped,
                    "aoa.saga.duration_ms": event.duration_ms,
                },
            )

        self._emit_log(
            body="aoa.saga.rollback.completed",
            attributes={
                "aoa.action": event.action_name,
                "aoa.saga.total": event.total_frames,
                "aoa.saga.succeeded": event.succeeded,
                "aoa.saga.failed": event.failed,
                "aoa.saga.skipped": event.skipped,
                "aoa.saga.duration_ms": event.duration_ms,
            },
            severity=SeverityNumber.WARN if event.failed > 0 else SeverityNumber.INFO,
            span=root_span,
            event=event,
        )
        return state

    # ─────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _emit_log(
        self,
        body: str,
        attributes: dict[str, Any],
        severity: SeverityNumber = SeverityNumber.INFO,
        span: Span | None = None,
        event: BasePluginEvent | None = None,
    ) -> None:
        """Emit an OTel log record. No-op if logger_provider was not provided."""
        if self._otel_logger is None:
            return

        span_ctx = span.get_span_context() if span is not None else None
        trace_id = span_ctx.trace_id if (span_ctx and span_ctx.is_valid) else None
        span_id = span_ctx.span_id if (span_ctx and span_ctx.is_valid) else None
        trace_flags = span_ctx.trace_flags if (span_ctx and span_ctx.is_valid) else TraceFlags.DEFAULT

        all_attributes: dict[str, Any] = {}
        if event is not None:
            aoa_trace_id = event.context.request.trace_id
            if aoa_trace_id:
                all_attributes["aoa.trace_id"] = aoa_trace_id
        all_attributes.update(attributes)

        now = int(time.time_ns())
        self._otel_logger.emit(
            LogRecord(  # type: ignore[call-overload]
                timestamp=now,
                observed_timestamp=now,
                trace_id=trace_id,
                span_id=span_id,
                trace_flags=trace_flags,
                severity_number=severity,
                severity_text=severity.name,
                body=body,
                attributes=all_attributes,
            )
        )

    def _state_attributes(
        self,
        data: dict[str, Any] | None,
        opaque_fields: frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        """Serialize each state field as ``aoa.state.<key>`` attribute, skipping opaque fields."""
        if not data:
            return {}
        return {
            f"aoa.state.{key}": _serialize_value(value, self._max_field_length)
            for key, value in data.items()
            if key not in opaque_fields
        }

    def _result_attributes(self, result: Any) -> dict[str, Any]:
        """Serialize each result field as ``aoa.result.<key>`` attribute."""
        data: dict[str, Any] | None = None
        if hasattr(result, "model_dump"):
            data = result.model_dump()
        elif hasattr(result, "__dict__"):
            data = result.__dict__
        if not data:
            return {}
        return {f"aoa.result.{key}": _serialize_value(value, self._max_field_length) for key, value in data.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────


def _start_aspect_span(
    state: dict[str, Any],
    aspect_name: str,
    action_name: str,
    tracer: trace.Tracer,
) -> dict[str, Any]:
    """Create a child span under the root span stored in *state*."""
    root_ctx: OtelContext | None = state.get(_CTX_KEY)
    span = tracer.start_span(
        name=aspect_name,
        context=root_ctx,
        attributes={
            "aoa.aspect": aspect_name,
            "aoa.action": action_name,
        },
    )
    aspect_spans: dict[str, Span] = {**state.get(_ASPECT_SPANS_KEY, {}), aspect_name: span}
    return {**state, _ASPECT_SPANS_KEY: aspect_spans}


def _end_aspect_span(
    state: dict[str, Any],
    aspect_name: str,
    duration_ms: float,
) -> dict[str, Any]:
    """End the aspect span identified by *aspect_name* and record *duration_ms*."""
    aspect_spans: dict[str, Span] = dict(state.get(_ASPECT_SPANS_KEY, {}))
    span = aspect_spans.pop(aspect_name, None)
    if span is not None and span.is_recording():
        span.set_attribute("aoa.duration_ms", duration_ms)
        span.set_status(StatusCode.OK)
        span.end()
    return {**state, _ASPECT_SPANS_KEY: aspect_spans}


def _serialize_value(value: Any, max_length: int) -> str | int | float | bool | None:
    """Serialize a state field value to an OTel-safe type.

    Primitives pass through unchanged. Pydantic models are dumped via
    ``model_dump()`` for clean JSON. Other complex objects fall back to
    ``json.dumps(default=repr)`` then ``repr()``. Result truncated to
    *max_length* characters.
    """
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        raw = value.model_dump() if hasattr(value, "model_dump") else value
        text = json.dumps(raw, default=repr)
    except Exception:
        text = repr(value)
    if len(text) > max_length:
        text = text[:max_length] + "...[truncated]"
    return text
