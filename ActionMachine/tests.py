# ActionMachine/tests.py
"""
Тесты для ActionMachine с демонстрацией вложенности действий и отступов в плагинах.
"""

import sys
import os
import time
from typing import Any, Dict, List, Optional, Tuple, cast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass

from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Core.MockAction import MockAction
from ActionMachine.Core.ActionTestMachine import ActionTestMachine
from ActionMachine.Core.DependencyFactory import DependencyFactory
from ActionMachine.Checkers.InstanceOfChecker import InstanceOfChecker
from ActionMachine.Checkers.StringFieldChecker import StringFieldChecker
from ActionMachine.Checkers.IntFieldChecker import IntFieldChecker
from ActionMachine.Checkers.BoolFieldChecker import BoolFieldChecker
from ActionMachine.Auth.CheckRoles import CheckRoles
from ActionMachine.Context.UserInfo import UserInfo
from ActionMachine.Context.Context import Context
from ActionMachine.Plugins.Plugin import Plugin
from ActionMachine.Plugins.Decorators import on
import pytest


# ---------- Тестовые сервисы ----------

class EmailService:
    def send(self, to: str, msg: str) -> None:
        print(f"Sending email to {to}: {msg}")


class SmsService:
    def send(self, to: str, msg: str) -> None:
        print(f"Sending SMS to {to}: {msg}")


# ---------- Тестовые действия ----------

@depends(EmailService, description="Сервис email")
@depends(SmsService, description="Сервис SMS")
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class NotificationAction(BaseAction['NotificationAction.Params', 'NotificationAction.Result']):
    @dataclass(frozen=True)
    class Params(BaseParams):
        channel: str
        message: str
        recipient: str

    @dataclass(frozen=True)
    class Result(BaseResult):
        success: bool

    @aspect("Выбор канала")
    @InstanceOfChecker("service", (EmailService, SmsService),
                       desc="В state должен быть объект EmailService или SmsService")
    @StringFieldChecker("selected_channel", desc="Канал, который был выбран", required=False)
    def choose_channel(
        self, params: Params, state: Dict[str, Any], deps: DependencyFactory
    ) -> Dict[str, Any]:
        if params.channel == 'email':
            state['service'] = deps.get(EmailService)
            state['selected_channel'] = 'email'
        elif params.channel == 'sms':
            state['service'] = deps.get(SmsService)
            state['selected_channel'] = 'sms'
        else:
            raise ValueError("Unknown channel")
        return state

    @summary_aspect("Отправка")
    def send(
        self, params: Params, state: Dict[str, Any], deps: DependencyFactory
    ) -> Result:
        service = state['service']
        service.send(params.recipient, params.message)
        return NotificationAction.Result(success=True)


@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ChildAction(BaseAction['ChildAction.Params', 'ChildAction.Result']):
    @dataclass(frozen=True)
    class Params(BaseParams):
        value: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        doubled: int

    @aspect("Подготовка")
    @BoolFieldChecker("prepared", desc="Флаг подготовки", required=True)
    def prepare(
        self, params: Params, state: Dict[str, Any], deps: DependencyFactory
    ) -> Dict[str, Any]:
        print(f"\033[91m[ChildAction] Аспект 'prepare' выполняется\033[0m")
        state['prepared'] = True
        return state

    @summary_aspect("Удвоить")
    def handle(
        self, params: Params, state: Dict[str, Any], deps: DependencyFactory
    ) -> Result:
        print(f"\033[91m[ChildAction] Summary-аспект 'handle' выполняется\033[0m")
        return ChildAction.Result(params.value * 2)


@depends(ChildAction, description="Дочернее действие")
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ParentAction(BaseAction['ParentAction.Params', 'ParentAction.Result']):
    @dataclass(frozen=True)
    class Params(BaseParams):
        num: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        result: int

    @aspect("Задержка")
    def delay(
        self, params: Params, state: Dict[str, Any], deps: DependencyFactory
    ) -> Dict[str, Any]:
        print(f"\033[91m[ParentAction] Аспект 'delay' начал работу\033[0m")
        time.sleep(2)
        print(f"\033[91m[ParentAction] Аспект 'delay' завершил работу\033[0m")
        return state

    @aspect("Доп. проверка")
    @IntFieldChecker("child_result", desc="Результат дочернего действия", required=True)
    def extra_check(
        self, params: Params, state: Dict[str, Any], deps: DependencyFactory
    ) -> Dict[str, Any]:
        print(f"\033[91m[ParentAction] Аспект 'extra_check' начинает дочернее действие\033[0m")
        child_result = cast(ChildAction.Result, deps.run_action(ChildAction, ChildAction.Params(params.num)))
        print(f"\033[91m[ParentAction] Аспект 'extra_check' завершился, результат дочернего: {child_result}\033[0m")
        state['child_result'] = child_result.doubled
        return state

    @summary_aspect("Родитель")
    def handle(
        self, params: Params, state: Dict[str, Any], deps: DependencyFactory
    ) -> Result:
        child_result = cast(ChildAction.Result, deps.run_action(ChildAction, ChildAction.Params(params.num)))
        assert isinstance(child_result, ChildAction.Result)
        return ParentAction.Result(child_result.doubled + 10)


# ---------- Тестовые плагины для консольного вывода с отступами ----------

def indent(level: int) -> str:
    """Возвращает строку отступа из 2 пробелов на уровень."""
    return "  " * level


class ConsoleLoggingPlugin(Plugin):
    def __init__(self, name: str = "PluginA") -> None:
        self.name = name

    def get_initial_state(self) -> Dict[str, Any]:
        return {}

    @on('global_start', '.*', ignore_exceptions=True)
    async def on_global_start(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Any,
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: Any,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level)}\033[93m[{event_name}] {self.name}: Action '{action_name}' started with params: {params}\033[0m")
        return state_plugin

    @on('global_finish', '.*', ignore_exceptions=True)
    async def on_global_finish(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Any,
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: float,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level)}\033[93m[{event_name}] {self.name}: Action '{action_name}' finished, duration: {duration:.4f}s, result: {result}\033[0m")
        return state_plugin

    @on('before:.*', '.*', ignore_exceptions=True)
    async def on_before_aspect(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Dict[str, Any],
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: Any,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level+1)}\033[92m[{event_name}] {self.name}: before aspect, current state: {state_aspect}\033[0m")
        return state_plugin

    @on('after:.*', '.*', ignore_exceptions=True)
    async def on_after_aspect(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Dict[str, Any],
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: float,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level+1)}\033[92m[{event_name}] {self.name}: after aspect, duration: {duration:.4f}s, new state: {state_aspect}\033[0m")
        return state_plugin


class AnotherLoggingPlugin(Plugin):
    def __init__(self, name: str = "PluginB") -> None:
        self.name = name

    def get_initial_state(self) -> Dict[str, Any]:
        return {}

    @on('global_start', '.*', ignore_exceptions=True)
    async def on_global_start(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Any,
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: Any,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level)}\033[94m[{event_name}] {self.name}: Action '{action_name}' started with params: {params}\033[0m")
        return state_plugin

    @on('global_finish', '.*', ignore_exceptions=True)
    async def on_global_finish(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Any,
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: float,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level)}\033[94m[{event_name}] {self.name}: Action '{action_name}' finished, duration: {duration:.4f}s, result: {result}\033[0m")
        return state_plugin

    @on('before:.*', '.*', ignore_exceptions=True)
    async def on_before_aspect(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Dict[str, Any],
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: Any,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level+1)}\033[94m[{event_name}] {self.name}: before aspect, state: {state_aspect}\033[0m")
        return state_plugin

    @on('after:.*', '.*', ignore_exceptions=True)
    async def on_after_aspect(
        self,
        state_plugin: Dict[str, Any],
        event_name: str,
        action_name: str,
        params: BaseParams,
        state_aspect: Dict[str, Any],
        is_summary: bool,
        deps: DependencyFactory,
        context: Context,
        result: Any,
        duration: float,
        nest_level: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        print(f"{indent(nest_level+1)}\033[94m[{event_name}] {self.name}: after aspect, duration: {duration:.4f}s, new state: {state_aspect}\033[0m")
        return state_plugin


# ---------- Тесты для отдельных аспектов ----------

def test_choose_channel_aspect() -> None:
    """Тест: аспект choose_channel корректно выбирает email и sms сервисы."""
    fake_email: Any = object()
    fake_sms: Any = object()
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({
        EmailService: fake_email,
        SmsService: fake_sms
    }, context=context)
    factory: DependencyFactory = machine.build_factory(NotificationAction)
    action: NotificationAction = NotificationAction()

    params = NotificationAction.Params(channel='email', message='hi', recipient='a@b.c')
    state: Dict[str, Any] = {}
    result_state = action.choose_channel(params, state, factory)
    assert result_state['service'] is fake_email
    assert result_state['selected_channel'] == 'email'

    params2 = NotificationAction.Params(channel='sms', message='hi', recipient='123')
    state2: Dict[str, Any] = {}
    result_state2 = action.choose_channel(params2, state2, factory)
    assert result_state2['service'] is fake_sms
    assert result_state2['selected_channel'] == 'sms'


def test_choose_channel_aspect_unknown() -> None:
    """Тест: аспект choose_channel выбрасывает ValueError для неизвестного канала."""
    fake_email: Any = object()
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({EmailService: fake_email}, context=context)
    factory: DependencyFactory = machine.build_factory(NotificationAction)
    action: NotificationAction = NotificationAction()
    params = NotificationAction.Params(channel='fax', message='hi', recipient='x')
    with pytest.raises(ValueError, match="Unknown channel"):
        action.choose_channel(params, {}, factory)


# ---------- Тесты для целых действий (через синхронный run) ----------

def test_notification_action_with_mock_services() -> None:
    """Тест: полный запуск NotificationAction с мок-сервисами."""
    class FakeEmail(EmailService):
        def __init__(self) -> None:
            self.sent: List[Tuple[str, str]] = []
        def send(self, to: str, msg: str) -> None:
            self.sent.append((to, msg))

    class FakeSms(SmsService):
        def __init__(self) -> None:
            self.sent: List[Tuple[str, str]] = []
        def send(self, to: str, msg: str) -> None:
            self.sent.append((to, msg))

    fake_email: FakeEmail = FakeEmail()
    fake_sms: FakeSms = FakeSms()
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({
        EmailService: fake_email,
        SmsService: fake_sms
    }, context=context)
    action = NotificationAction()
    params = NotificationAction.Params(channel='email', message='Hello', recipient='test@test.com')
    result = machine.run(action, params)
    assert result.success is True
    assert fake_email.sent == [('test@test.com', 'Hello')]
    assert fake_sms.sent == []


def test_parent_action_with_mock_child() -> None:
    """Тест: ParentAction с замоканным результатом дочернего действия."""
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({
        ChildAction: ChildAction.Result(20)
    }, context=context)
    action = ParentAction()
    params = ParentAction.Params(5)
    result = machine.run(action, params)
    assert result.result == 30  # 20 + 10


def test_parent_action_with_side_effect() -> None:
    """Тест: ParentAction с side_effect для дочернего действия."""
    def child_side_effect(params: ChildAction.Params) -> ChildAction.Result:
        return ChildAction.Result(params.value * 3)

    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine(
        {ChildAction: child_side_effect}, context=context
    )
    action = ParentAction()
    params = ParentAction.Params(5)
    result = machine.run(action, params)
    assert result.result == 25  # 5*3=15 + 10


def test_parent_action_with_real_child() -> None:
    """Тест: ParentAction с реальным дочерним действием (без плагинов)."""
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine(context=context)
    action = ParentAction()
    params = ParentAction.Params(5)
    result = machine.run(action, params)
    assert result.result == 20  # 5*2=10 + 10


def test_parent_action_with_real_child_and_plugins() -> None:
    """Тест: ParentAction вызывает ChildAction, плагины показывают вложенность с отступами."""
    plugin_a = ConsoleLoggingPlugin("PluginA")
    plugin_b = AnotherLoggingPlugin("PluginB")
    context = Context(user=UserInfo(roles=["user"]))
    machine = ActionTestMachine(context=context)
    machine._plugins.append(plugin_a)
    machine._plugins.append(plugin_b)

    action = ParentAction()
    params = ParentAction.Params(5)
    result = machine.run(action, params)
    assert result.result == 20


def test_mock_action_call_tracking() -> None:
    """Тест: MockAction корректно считает вызовы и запоминает параметры."""
    mock_action: MockAction = MockAction(result=ChildAction.Result(100))
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine(
        {ChildAction: mock_action}, context=context
    )
    action = ParentAction()
    params = ParentAction.Params(7)
    result = machine.run(action, params)
    assert result.result == 110  # 100 + 10
    assert mock_action.call_count == 2  # два вызова: в extra_check и в handle
    assert isinstance(mock_action.last_params, ChildAction.Params)
    assert mock_action.last_params.value == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])