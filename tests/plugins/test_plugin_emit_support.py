# tests/plugins/test_plugin_emit_support.py
"""Unit tests for ``PluginEmitSupport`` — plugin event payload helpers."""

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.plugin_emit_support import PluginEmitSupport
from tests.domain_model import PingAction


def test_base_fields_shape() -> None:
    """base_fields returns action_class, action_name, nest_level, context, params."""
    log = LogCoordinator(loggers=[])
    emit = PluginEmitSupport(
        log,
        machine_class_name="ActionProductMachine",
        mode="test",
    )
    action = PingAction()
    ctx = Context(user=UserInfo(user_id="u1", roles=[]))
    params = PingAction.Params()

    fields = emit.base_fields(action, ctx, params, nest_level=2)

    assert fields["action_class"] is type(action)
    assert fields["action_name"] == action.get_full_class_name()
    assert fields["nest_level"] == 2
    assert fields["context"] is ctx
    assert fields["params"] is params


def test_emit_extra_kwargs_shape() -> None:
    """emit_extra_kwargs returns log_coordinator, machine_name, mode."""
    log = LogCoordinator(loggers=[])
    emit = PluginEmitSupport(
        log,
        machine_class_name="SyncActionProductMachine",
        mode="prod",
    )

    extra = emit.emit_extra_kwargs(99)

    assert extra["log_coordinator"] is log
    assert extra["machine_name"] == "SyncActionProductMachine"
    assert extra["mode"] == "prod"


def test_properties_expose_config() -> None:
    """machine_class_name, mode, log_coordinator match constructor."""
    log = LogCoordinator(loggers=[])
    emit = PluginEmitSupport(
        log,
        machine_class_name="X",
        mode="m",
    )
    assert emit.log_coordinator is log
    assert emit.machine_class_name == "X"
    assert emit.mode == "m"
