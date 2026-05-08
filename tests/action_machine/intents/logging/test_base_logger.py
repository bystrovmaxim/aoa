# tests/intents/logging/test_base_logger.py
"""BaseLogger tests via RecordingLogger: subscribe/match_filters.

Coverage: Anything accepted without subscriptions; by channel, level, domain; And inside
subscriptions, OR between subscriptions; subscribe validation errors; unsubscribe;
call chains."""

from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import Channel, channel_mask_label
from aoa.action_machine.logging.level import Level, level_label
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState
from tests.action_machine.scenarios.domain_model.domains import OrdersDomain, SystemDomain


def _v(**extra: Any) -> dict[str, Any]:
    """Minimum var as after LogCoordinator (for handle/match_filters)."""
    li = extra.pop("level", Level.info)
    cd = extra.pop("channels", Channel.debug)
    return {
        "level": LogLevelPayload(mask=li, name=level_label(li)),
        "channels": LogChannelPayload(mask=cd, names=channel_mask_label(cd)),
        "domain": None,
        "domain_name": None,
        **extra,
    }


class RecordingLogger(BaseLogger):
    """Spy: writes to records everything that reaches write."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, Any]] = []

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        self.records.append(
            {
                "scope": scope,
                "message": message,
                "var": var.copy(),
                "ctx": ctx,
                "state": state.to_dict(),
                "params": params,
                "indent": indent,
            }
        )


class OrdersSubdomainDomain(OrdersDomain):
    """The domain subclass to check issubclass in the subscription."""

    name = "orders_sub"
    description = "Child orders domain for subscription tests"


@pytest.fixture
def empty_context() -> Context:
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    return BaseParams()


@pytest.fixture
def simple_scope() -> LogScope:
    return LogScope(action="TestAction")


@pytest.fixture
def detailed_scope() -> LogScope:
    return LogScope(action="TestAction", aspect="validate", event="before")


class TestWithoutSubscriptions:
    """No subscriptions - all messages are accepted."""

    @pytest.mark.anyio
    async def test_passes_all_messages(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        var = _v(key="value")

        await logger.handle(
            simple_scope, "test message", var,
            empty_context, empty_state, empty_params, 0,
        )

        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "test message"

    @pytest.mark.anyio
    async def test_multiple_messages(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        var = _v()

        await logger.handle(simple_scope, "first", var, empty_context, empty_state, empty_params, 0)
        await logger.handle(simple_scope, "second", var, empty_context, empty_state, empty_params, 1)
        await logger.handle(simple_scope, "third", var, empty_context, empty_state, empty_params, 2)

        assert len(logger.records) == 3
        assert [r["message"] for r in logger.records] == ["first", "second", "third"]


class TestSubscriptionByChannel:
    @pytest.mark.anyio
    async def test_channel_match(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("c", channels=Channel.business)

        await logger.handle(
            simple_scope, "x", _v(channels=Channel.business),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_channel_no_overlap_rejects(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("c", channels=Channel.business)

        await logger.handle(
            simple_scope, "x", _v(channels=Channel.debug),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 0

    @pytest.mark.anyio
    async def test_channel_bitmask_intersection(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("c", channels=Channel.debug | Channel.business)

        await logger.handle(
            simple_scope, "x", _v(channels=Channel.debug),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 1


class TestSubscriptionByLevel:
    @pytest.mark.anyio
    async def test_level_match(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("l", levels=Level.warning)

        await logger.handle(
            simple_scope, "x", _v(level=Level.warning),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_level_mask_warning_or_critical(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("l", levels=Level.warning | Level.critical)

        await logger.handle(
            simple_scope, "w", _v(level=Level.warning),
            empty_context, empty_state, empty_params, 0,
        )
        await logger.handle(
            simple_scope, "c", _v(level=Level.critical),
            empty_context, empty_state, empty_params, 0,
        )
        await logger.handle(
            simple_scope, "i", _v(level=Level.info),
            empty_context, empty_state, empty_params, 0,
        )

        assert len(logger.records) == 2
        assert logger.records[0]["message"] == "w"
        assert logger.records[1]["message"] == "c"


class TestSubscriptionByDomain:
    @pytest.mark.anyio
    async def test_domain_match(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("d", domains=OrdersDomain)

        await logger.handle(
            simple_scope,
            "x",
            _v(domain=OrdersDomain, domain_name="orders"),
            empty_context,
            empty_state,
            empty_params,
            0,
        )
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_domain_subclass_matches(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("d", domains=OrdersDomain)

        await logger.handle(
            simple_scope,
            "x",
            _v(domain=OrdersSubdomainDomain, domain_name="orders_sub"),
            empty_context,
            empty_state,
            empty_params,
            0,
        )
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_domain_none_no_match(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("d", domains=OrdersDomain)

        await logger.handle(
            simple_scope, "x", _v(domain=None, domain_name=None),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 0


class TestSubscriptionAndOr:
    @pytest.mark.anyio
    async def test_channels_and_levels_both_required(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("both", channels=Channel.business, levels=Level.info)

        await logger.handle(
            simple_scope, "ok", _v(channels=Channel.business, level=Level.info),
            empty_context, empty_state, empty_params, 0,
        )
        await logger.handle(
            simple_scope, "bad", _v(channels=Channel.debug, level=Level.info),
            empty_context, empty_state, empty_params, 0,
        )

        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "ok"

    @pytest.mark.anyio
    async def test_two_subscriptions_or(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("a", channels=Channel.debug)
        logger.subscribe("b", channels=Channel.compliance)

        await logger.handle(
            simple_scope, "d", _v(channels=Channel.debug),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 1

        logger2 = RecordingLogger()
        logger2.subscribe("a", channels=Channel.debug)
        logger2.subscribe("b", channels=Channel.compliance)
        await logger2.handle(
            simple_scope, "c", _v(channels=Channel.compliance),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger2.records) == 1


class TestSubscribeValidation:
    def test_duplicate_key_raises(self) -> None:
        logger = RecordingLogger()
        logger.subscribe("k", channels=Channel.debug)
        with pytest.raises(ValueError, match="already exists"):
            logger.subscribe("k", channels=Channel.business)

    def test_empty_key_raises(self) -> None:
        logger = RecordingLogger()
        with pytest.raises(ValueError, match="non-empty string"):
            logger.subscribe("", channels=Channel.debug)
        with pytest.raises(ValueError, match="non-empty string"):
            logger.subscribe("   ", channels=Channel.debug)

    def test_invalid_channel_bits_raises(self) -> None:
        logger = RecordingLogger()
        bad = Channel(32)  # one bit beyond the five defined channels (mask 31)
        with pytest.raises(ValueError, match="unknown bits"):
            logger.subscribe("k", channels=bad)

    def test_zero_levels_raises(self) -> None:
        logger = RecordingLogger()
        with pytest.raises(ValueError, match="cannot be zero"):
            logger.subscribe("k", levels=Level(0))

    def test_invalid_domain_type_raises(self) -> None:
        logger = RecordingLogger()
        with pytest.raises(TypeError, match="BaseDomain"):
            logger.subscribe("k", domains=str)  # type: ignore[arg-type]

    def test_empty_domains_list_raises(self) -> None:
        logger = RecordingLogger()
        with pytest.raises(ValueError, match="cannot be empty"):
            logger.subscribe("k", domains=[])

    def test_empty_domains_tuple_raises(self) -> None:
        logger = RecordingLogger()
        with pytest.raises(ValueError, match="cannot be empty"):
            logger.subscribe("k", domains=())

    def test_single_domain_class_works(self) -> None:
        logger = RecordingLogger()
        logger.subscribe("k", domains=SystemDomain)
        assert "k" in logger._subscriptions

    def test_domains_list_works(self) -> None:
        logger = RecordingLogger()
        logger.subscribe("k", domains=[OrdersDomain, SystemDomain])
        assert logger._subscriptions["k"].domains == (OrdersDomain, SystemDomain)

    def test_domains_tuple_works(self) -> None:
        logger = RecordingLogger()
        logger.subscribe("k", domains=(OrdersDomain, SystemDomain))
        assert logger._subscriptions["k"].domains == (OrdersDomain, SystemDomain)

    def test_subscribe_chain_returns_self(self) -> None:
        logger = RecordingLogger()
        out = logger.subscribe("a", channels=Channel.debug).subscribe(
            "b", channels=Channel.business,
        )
        assert out is logger
        assert len(logger._subscriptions) == 2


class TestUnsubscribe:
    def test_unsubscribe_existing(self) -> None:
        logger = RecordingLogger()
        logger.subscribe("k", channels=Channel.debug)
        logger.unsubscribe("k")
        assert "k" not in logger._subscriptions

    def test_unsubscribe_missing_raises(self) -> None:
        logger = RecordingLogger()
        with pytest.raises(KeyError, match="not found"):
            logger.unsubscribe("missing")

    @pytest.mark.anyio
    async def test_unsubscribe_then_subscribe_same_key(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        logger.subscribe("k", channels=Channel.debug)
        logger.unsubscribe("k")
        logger.subscribe("k", channels=Channel.business)

        await logger.handle(
            simple_scope, "x", _v(channels=Channel.business),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 1


class TestParameterPassing:
    @pytest.mark.anyio
    async def test_passes_all_params(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        state = BaseState(total=100, processed=True)
        var = _v(key="value", count=42)
        indent = 3

        await logger.handle(
            simple_scope, "test message", var,
            empty_context, state, empty_params, indent,
        )

        record = logger.records[0]
        assert record["scope"] is simple_scope
        assert record["message"] == "test message"
        assert record["var"] == var
        assert record["ctx"] is empty_context
        assert record["state"] == {"total": 100, "processed": True}
        assert record["params"] is empty_params
        assert record["indent"] == indent

    @pytest.mark.anyio
    async def test_does_not_modify_original_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        original_var = _v(key="value")
        var_copy = original_var.copy()

        await logger.handle(
            simple_scope, "test", original_var,
            empty_context, empty_state, empty_params, 0,
        )

        assert original_var == var_copy

    @pytest.mark.anyio
    async def test_does_not_modify_original_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        original_state = BaseState(total=100)
        original_dict = original_state.to_dict()

        await logger.handle(
            simple_scope, "test", _v(),
            empty_context, original_state, empty_params, 0,
        )

        assert original_state.to_dict() == original_dict


class TestEdgeCases:
    @pytest.mark.anyio
    async def test_empty_message(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        await logger.handle(
            simple_scope, "", _v(),
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == ""

    @pytest.mark.anyio
    async def test_minimal_var_only_system_keys(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        var = _v()
        await logger.handle(
            simple_scope, "test", var,
            empty_context, empty_state, empty_params, 0,
        )
        assert len(logger.records) == 1
        assert set(logger.records[0]["var"].keys()) >= {
            "level", "channels", "domain", "domain_name",
        }

    @pytest.mark.anyio
    async def test_complex_var_values(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        var = _v(
            **{
                "string": "text",
                "integer": 42,
                "float": 3.14,
                "boolean": True,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "none": None,
            },
        )

        await logger.handle(
            simple_scope, "complex", var,
            empty_context, empty_state, empty_params, 0,
        )

        assert len(logger.records) == 1
        assert logger.records[0]["var"] == var
        assert logger.records[0]["var"] == var
