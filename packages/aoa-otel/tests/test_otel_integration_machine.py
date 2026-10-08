# tests/otel/test_otel_integration_machine.py
"""
End-to-end integration tests: OpenTelemetryPlugin driven by a real ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Unit tests cover the plugin's pure helpers (``_emit_log``, ``_state_attributes``,
``_serialize_value``). They do NOT exercise the span lifecycle, which is what the
recent fixes touched. These tests run Actions through ``ActionProductMachine`` with
in-memory OTel exporters and assert on the resulting spans / log records:

- root + child spans, child→root nesting, OK status on success;
- regression for the orphan-span fix: a failing aspect's child span is closed with
  ERROR status and carries a recorded exception event;
- regression for the per-step span_id fix: a regular-aspect after-log is correlated
  with that aspect's own span, not the root span;
- saga rollback recorded as timed events on the root span; compensator spans closed;
- end-to-end ``opaque``: an opaque field never reaches ``aoa.state.*`` log attributes;
- end-to-end ``watch_actions`` / ``watch_events`` filtering.
"""

from __future__ import annotations

from typing import Any

import pytest
from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.exceptions import AccessDenied, AccessUndecided
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.plugin.core.events import GlobalFinishEvent
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.otel import OpenTelemetryPlugin

from .support import PingAction, TestDomain

# ═════════════════════════════════════════════════════════════════════════════
# Test-local Actions (full control over opaque fields and failure paths)
# ═════════════════════════════════════════════════════════════════════════════


class OtelOrderParams(BaseParams):
    order_id: str = Field(description="Client order id")


class OtelOrderResult(BaseResult):
    order_id: str = Field(description="Processed order id")


@meta(description="OTel integration order", domain=TestDomain)
@check_roles(GuestRole)
class OtelOrderAction(BaseAction[OtelOrderParams, OtelOrderResult]):
    """Two regular aspects (one with an opaque field) + summary. Success path."""

    @regular_aspect("validate")
    @result_string("order_id", required=True, min_length=1)
    async def validate_aspect(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        return {"order_id": params.order_id}

    @regular_aspect("enrich")
    @result_string("order_id", required=True, min_length=1)
    @result_string("secret_token", required=True, min_length=1, opaque=True)
    async def enrich_aspect(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        return {"order_id": state["order_id"], "secret_token": "tok-super-secret"}

    @summary_aspect("build")
    async def build_summary(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> OtelOrderResult:
        return OtelOrderResult(order_id=state["order_id"])


@meta(description="OTel integration failing order", domain=TestDomain)
@check_roles(GuestRole)
class OtelFailingAction(BaseAction[OtelOrderParams, OtelOrderResult]):
    """A regular aspect raises; no @on_error, no compensator → error propagates."""

    @regular_aspect("boom")
    async def boom_aspect(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        raise ValueError("integration boom")

    @summary_aspect("unreachable")
    async def unreachable_summary(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> OtelOrderResult:
        return OtelOrderResult(order_id="unreachable")


@meta(description="OTel integration saga", domain=TestDomain)
@check_roles(GuestRole)
class OtelSagaAction(BaseAction[OtelOrderParams, OtelOrderResult]):
    """Two compensatable steps; the third regular aspect fails → saga rollback.

    Fully self-contained (no external services), so compensators always run.
    """

    @regular_aspect("charge")
    @result_string("txn_id", required=True, min_length=1)
    async def charge_aspect(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        return {"txn_id": "TXN-1"}

    @compensate(charge_aspect, "refund charge")
    async def refund_compensate(
        self,
        params: OtelOrderParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        error: Exception,
    ) -> None:
        return None

    @regular_aspect("reserve")
    @result_string("txn_id", required=True, min_length=1)
    @result_string("reservation_id", required=True, min_length=1)
    async def reserve_aspect(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        return {"txn_id": state["txn_id"], "reservation_id": "RES-1"}

    @compensate(reserve_aspect, "release reservation")
    async def unreserve_compensate(
        self,
        params: OtelOrderParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        error: Exception,
    ) -> None:
        return None

    @regular_aspect("finalize")
    async def finalize_aspect(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        raise ValueError("saga finalize boom")

    @summary_aspect("build")
    async def build_summary(
        self,
        params: OtelOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> OtelOrderResult:
        return OtelOrderResult(order_id="unreachable")


@meta(description="OTel integration failing gate", domain=TestDomain)
@check_roles(GuestRole)
class OtelFailingGateAction(BaseAction[OtelOrderParams, OtelOrderResult]):
    """An object check that cannot complete: the store behind it is down."""

    @access_decide("Fail, as a store that is down fails")
    async def otel_failing_gate_access_decide(
        self,
        params: OtelOrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        raise ConnectionError(_FAILURE_TEXT)

    @summary_aspect("build")
    async def build_summary(
        self, params: OtelOrderParams, state: BaseState, box: ToolsBox, connections: dict[str, BaseResource]
    ) -> OtelOrderResult:
        return OtelOrderResult(order_id="unreachable")


@meta(description="OTel integration refusing gate", domain=TestDomain)
@check_roles(GuestRole)
class OtelRefusingGateAction(BaseAction[OtelOrderParams, OtelOrderResult]):
    """An object check that refuses: nothing failed, the caller may not touch this object."""

    @access_decide("Refuse the object this caller may not touch")
    async def otel_refusing_gate_access_decide(
        self,
        params: OtelOrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        return FORBIDDEN_OBJECT

    @summary_aspect("build")
    async def build_summary(
        self, params: OtelOrderParams, state: BaseState, box: ToolsBox, connections: dict[str, BaseResource]
    ) -> OtelOrderResult:
        return OtelOrderResult(order_id="unreachable")


_FAILURE_TEXT = "postgres://primary:5432 refused the connection"
"""The failure's own text: the kind may travel, this may not."""


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures / helpers
# ═════════════════════════════════════════════════════════════════════════════


def _tracer_setup() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def _logger_setup() -> tuple[LoggerProvider, InMemoryLogRecordExporter]:
    exporter = InMemoryLogRecordExporter()
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    return provider, exporter


def _span_by_name(spans: Any) -> dict[str, Any]:
    spans = list(spans)
    by_name = {s.name: s for s in spans}
    assert len(by_name) == len(spans), "duplicate span names would be hidden by _span_by_name"
    return by_name


def _root_spans(spans: Any) -> list[Any]:
    return [s for s in spans if s.parent is None]


def _child_spans(spans: Any) -> list[Any]:
    return [s for s in spans if s.parent is not None]


# ═════════════════════════════════════════════════════════════════════════════
# Traces — success path: root + child spans, nesting, OK
# ═════════════════════════════════════════════════════════════════════════════


class TestSuccessSpans:
    @pytest.mark.asyncio
    async def test_root_and_child_spans_created(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))
        spans = exporter.get_finished_spans()
        roots = _root_spans(spans)
        children = _child_spans(spans)

        assert len(roots) == 1
        assert roots[0].name.endswith("OtelOrderAction")
        # validate + enrich + build → exactly 3 child spans
        assert len(children) == 3

    @pytest.mark.asyncio
    async def test_children_nested_under_root(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))
        spans = exporter.get_finished_spans()
        root = _root_spans(spans)[0]
        root_span_id = root.context.span_id

        for child in _child_spans(spans):
            assert child.parent is not None
            assert child.parent.span_id == root_span_id

    @pytest.mark.asyncio
    async def test_all_spans_ok_on_success(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))
        for span in exporter.get_finished_spans():
            assert span.status.status_code == StatusCode.OK

    @pytest.mark.asyncio
    async def test_same_trace_id_for_all_spans(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))
        trace_ids = {s.context.trace_id for s in exporter.get_finished_spans()}
        assert len(trace_ids) == 1


# ═════════════════════════════════════════════════════════════════════════════
# Regression A — failing aspect span closed with ERROR + recorded exception
# ═════════════════════════════════════════════════════════════════════════════


class TestFailingAspectSpan:
    @pytest.mark.asyncio
    async def test_failing_aspect_span_closed_with_error(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        with pytest.raises(ValueError, match="integration boom"):
            await machine.run(Context(), OtelFailingAction(), OtelOrderParams(order_id="ORD-X"))
        by_name = _span_by_name(exporter.get_finished_spans())
        # The failing aspect span must exist and be closed (not leaked).
        assert "boom_aspect" in by_name
        boom_span = by_name["boom_aspect"]
        assert boom_span.status.status_code == StatusCode.ERROR

    @pytest.mark.asyncio
    async def test_failing_aspect_span_records_exception(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        with pytest.raises(ValueError, match="integration boom"):
            await machine.run(Context(), OtelFailingAction(), OtelOrderParams(order_id="ORD-X"))
        boom_span = _span_by_name(exporter.get_finished_spans())["boom_aspect"]
        assert any(ev.name == "exception" for ev in boom_span.events)

    @pytest.mark.asyncio
    async def test_root_span_error_on_failure(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        with pytest.raises(ValueError, match="integration boom"):
            await machine.run(Context(), OtelFailingAction(), OtelOrderParams(order_id="ORD-X"))
        root = _root_spans(exporter.get_finished_spans())[0]
        assert root.status.status_code == StatusCode.ERROR


# ═════════════════════════════════════════════════════════════════════════════
# Regression F — per-step log correlated with the aspect span, not root
# ═════════════════════════════════════════════════════════════════════════════


class TestPerStepSpanCorrelation:
    @pytest.mark.asyncio
    async def test_after_log_span_id_matches_aspect_span(self) -> None:
        tp, span_exporter = _tracer_setup()
        lp, log_exporter = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp, logger_provider=lp)])

        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))
        spans = span_exporter.get_finished_spans()
        by_name = _span_by_name(spans)
        root_span_id = _root_spans(spans)[0].context.span_id

        after_logs = [
            ld.log_record for ld in log_exporter.get_finished_logs() if ld.log_record.body == "aoa.aspect.regular.after"
        ]
        assert after_logs, "expected regular after-logs"

        for rec in after_logs:
            aspect_name = rec.attributes["aoa.aspect"]
            assert aspect_name in by_name
            # log is correlated with the aspect's own span, not the root span
            assert rec.span_id == by_name[aspect_name].context.span_id
            assert rec.span_id != root_span_id

    @pytest.mark.asyncio
    async def test_before_log_correlated_with_root_span(self) -> None:
        tp, span_exporter = _tracer_setup()
        lp, log_exporter = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp, logger_provider=lp)])

        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))

        spans = span_exporter.get_finished_spans()
        root_span_id = _root_spans(spans)[0].context.span_id

        before_logs = [
            ld.log_record
            for ld in log_exporter.get_finished_logs()
            if ld.log_record.body == "aoa.aspect.regular.before"
        ]
        assert before_logs, "expected regular before-logs"

        # before-logs are correlated with the root span (the child span context
        # is not yet active when the before-log is emitted)
        for rec in before_logs:
            assert rec.span_id == root_span_id


# ═════════════════════════════════════════════════════════════════════════════
# Saga — rollback events on root span; compensator spans closed
# ═════════════════════════════════════════════════════════════════════════════


class TestSagaSpans:
    @pytest.mark.asyncio
    async def test_rollback_events_on_root_span(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        with pytest.raises(ValueError):
            await machine.run(
                Context(),
                OtelSagaAction(),
                OtelOrderParams(order_id="ORD-1"),
            )
        root = _root_spans(exporter.get_finished_spans())[0]
        event_names = {ev.name for ev in root.events}
        assert "saga.rollback.started" in event_names
        assert "saga.rollback.completed" in event_names

    @pytest.mark.asyncio
    async def test_compensator_spans_closed(self) -> None:
        tp, exporter = _tracer_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=tp)])

        with pytest.raises(ValueError):
            await machine.run(
                Context(),
                OtelSagaAction(),
                OtelOrderParams(order_id="ORD-1"),
            )
        by_name = _span_by_name(exporter.get_finished_spans())
        assert "refund_compensate" in by_name
        assert "unreserve_compensate" in by_name
        # all compensator spans are closed (exported) → no leak


# ═════════════════════════════════════════════════════════════════════════════
# Opaque — end-to-end: opaque field never reaches aoa.state.* attributes
# ═════════════════════════════════════════════════════════════════════════════


class TestOpaqueEndToEnd:
    @pytest.mark.asyncio
    async def test_opaque_field_excluded_non_opaque_present(self) -> None:
        lp, log_exporter = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(logger_provider=lp)])

        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))

        all_attr_keys: set[str] = set()
        for ld in log_exporter.get_finished_logs():
            all_attr_keys.update(ld.log_record.attributes.keys())

        # opaque field must never be serialized into state x-ray
        assert "aoa.state.secret_token" not in all_attr_keys
        # non-opaque field from the same aspect is present
        assert "aoa.state.order_id" in all_attr_keys


# ═════════════════════════════════════════════════════════════════════════════
# watch_actions / watch_events — end-to-end filtering through the machine
# ═════════════════════════════════════════════════════════════════════════════


class TestWatchFiltersEndToEnd:
    @pytest.mark.asyncio
    async def test_watch_actions_only_watched_action_emits(self) -> None:
        lp, log_exporter = _logger_setup()
        plugin = OpenTelemetryPlugin(
            logger_provider=lp,
            watch_actions=frozenset({PingAction}),
        )
        machine = ActionProductMachine(plugins=[plugin])

        # Watched action → log records emitted.
        await machine.run(Context(), PingAction(), PingAction.Params())
        assert len(log_exporter.get_finished_logs()) > 0

        log_exporter.clear()

        # Non-watched action → nothing reaches the plugin.
        await machine.run(Context(), OtelOrderAction(), OtelOrderParams(order_id="ORD-1"))
        assert len(log_exporter.get_finished_logs()) == 0

    @pytest.mark.asyncio
    async def test_watch_events_only_finish_event_emits(self) -> None:
        tp, span_exporter = _tracer_setup()
        lp, log_exporter = _logger_setup()
        plugin = OpenTelemetryPlugin(
            tracer_provider=tp,
            logger_provider=lp,
            watch_events=frozenset({GlobalFinishEvent}),
        )
        machine = ActionProductMachine(plugins=[plugin])

        await machine.run(Context(), PingAction(), PingAction.Params())
        bodies = [ld.log_record.body for ld in log_exporter.get_finished_logs()]
        assert bodies, "expected at least the finish log"
        assert all(b == "aoa.action.finish" for b in bodies)
        assert "aoa.action.start" not in bodies

        # GlobalStartEvent was filtered out, so the root span was never created.
        assert span_exporter.get_finished_spans() == ()


# ═════════════════════════════════════════════════════════════════════════════
# Logs — a gate that could not complete
# ═════════════════════════════════════════════════════════════════════════════


def _gate_failure_records(exporter: Any) -> list[Any]:
    """The log records this run wrote about a gate that could not complete."""
    return [r for r in exporter.get_finished_logs() if getattr(r.log_record, "body", None) == "aoa.access.gate_failed"]


class TestAccessGateFailureRecord:
    @pytest.mark.asyncio
    async def test_the_record_names_the_step_and_the_kind_of_failure(self) -> None:
        lp, logs = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(logger_provider=lp)])

        with pytest.raises(AccessUndecided):
            await machine.run(Context(), OtelFailingGateAction(), OtelOrderParams(order_id="ORD-1"))

        (record,) = _gate_failure_records(logs)
        attributes = record.log_record.attributes
        assert str(attributes["aoa.action"]).endswith("OtelFailingGateAction")
        assert attributes["aoa.gate"] == "ACCESS_DECIDE"
        assert attributes["aoa.error_type"] == "ConnectionError"
        assert record.log_record.severity_number == SeverityNumber.ERROR

    @pytest.mark.asyncio
    async def test_the_failure_text_is_never_written(self) -> None:
        lp, logs = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(logger_provider=lp)])

        with pytest.raises(AccessUndecided):
            await machine.run(Context(), OtelFailingGateAction(), OtelOrderParams(order_id="ORD-1"))

        for record in logs.get_finished_logs():
            assert _FAILURE_TEXT not in str(record.log_record.body)
            assert _FAILURE_TEXT not in str(record.log_record.attributes)

    @pytest.mark.asyncio
    async def test_it_is_correlated_with_the_run_it_stopped(self) -> None:
        """Each failing run writes under its own trace, not under nothing.

        The root span of a run stopped at a gate is never closed — there is no
        ``GlobalFinish`` to close it — so there is no exported span to compare against; what
        the record carries is that run's trace id all the same, and two runs differ.
        """
        tp, _spans = _tracer_setup()
        lp, logs = _logger_setup()
        machine = ActionProductMachine(
            plugins=[OpenTelemetryPlugin(tracer_provider=tp, logger_provider=lp)]
        )

        for _ in range(2):
            with pytest.raises(AccessUndecided):
                await machine.run(Context(), OtelFailingGateAction(), OtelOrderParams(order_id="ORD-1"))

        first, second = _gate_failure_records(logs)
        assert first.log_record.trace_id != 0
        assert first.log_record.trace_id != second.log_record.trace_id

    @pytest.mark.asyncio
    async def test_the_request_identity_travels_when_the_context_has_one(self) -> None:
        lp, logs = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(logger_provider=lp)])
        caller = Context(request=RequestInfo(trace_id="trace-1"))

        with pytest.raises(AccessUndecided):
            await machine.run(caller, OtelFailingGateAction(), OtelOrderParams(order_id="ORD-1"))

        (record,) = _gate_failure_records(logs)
        assert record.log_record.attributes["aoa.trace_id"] == "trace-1"

    @pytest.mark.asyncio
    async def test_it_is_absent_when_the_context_has_none(self) -> None:
        lp, logs = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(logger_provider=lp)])

        with pytest.raises(AccessUndecided):
            await machine.run(Context(), OtelFailingGateAction(), OtelOrderParams(order_id="ORD-1"))

        (record,) = _gate_failure_records(logs)
        assert "aoa.trace_id" not in record.log_record.attributes

    @pytest.mark.asyncio
    async def test_a_refusal_writes_no_such_record(self) -> None:
        """A refusal is an answer, not a failure: it is never reported as one."""
        lp, logs = _logger_setup()
        machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(logger_provider=lp)])

        with pytest.raises(AccessDenied):
            await machine.run(Context(), OtelRefusingGateAction(), OtelOrderParams(order_id="ORD-1"))

        assert _gate_failure_records(logs) == []

    @pytest.mark.asyncio
    async def test_nothing_is_written_without_a_logger_provider(self) -> None:
        """No logs configured, no logs written — and the call still behaves the same."""
        tp, _spans = _tracer_setup()
        plugin = OpenTelemetryPlugin(tracer_provider=tp)
        machine = ActionProductMachine(plugins=[plugin])

        with pytest.raises(AccessUndecided):
            await machine.run(Context(), OtelFailingGateAction(), OtelOrderParams(order_id="ORD-1"))

        assert plugin._otel_logger is None
