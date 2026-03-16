"""
Тесты для ActionMachine с демонстрацией вложенности действий, отступов в плагинах
и использования параметра factory декоратора @depends для интеграции с внешними DI-контейнерами.
Все тесты асинхронные, используют anyio.
State в аспектах типизируется через TypedDict.
"""

import sys
import os
import asyncio
from typing import Any, List, Tuple, cast
from typing_extensions import TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass

import inject
import pytest

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
from ActionMachine.Plugins.PluginEvent import PluginEvent
from ActionMachine.Plugins.Decorators import on
from ActionMachine.ResourceManagers.BaseResourceManager import BaseResourceManager

# ---------- Тестовые сервисы ----------

class EmailService:
    """Тестовый сервис отправки email."""
    def send(self, to: str, msg: str) -> None:
        """Отправляет email."""
        print(f"Sending email to {to}: {msg}")

class SmsService:
    """Тестовый сервис отправки SMS."""
    def send(self, to: str, msg: str) -> None:
        """Отправляет SMS."""
        print(f"Sending SMS to {to}: {msg}")

# ---------- TypedDict для state ----------

class NotificationState(TypedDict, total=False):
    """Состояние для NotificationAction."""
    service: EmailService | SmsService
    selected_channel: str

class ChildState(TypedDict, total=False):
    """Состояние для ChildAction."""
    prepared: bool

class ParentState(TypedDict, total=False):
    """Состояние для ParentAction."""
    child_result: int

class InjectState(TypedDict, total=False):
    """Состояние для ActionWithInject (пустое)."""
    pass

# ---------- Тестовые действия ----------

@depends(EmailService, description="Сервис email")
@depends(SmsService, description="Сервис SMS")
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class NotificationAction(BaseAction['NotificationAction.Params', 'NotificationAction.Result']):
    """Действие отправки уведомления через выбранный канал."""

    @dataclass(frozen=True)
    class Params(BaseParams):
        """Параметры действия: канал, сообщение, получатель."""
        channel: str
        message: str
        recipient: str

    @dataclass
    class Result(BaseResult):
        """Результат: успех операции."""
        success: bool

    @aspect("Выбор канала")
    @InstanceOfChecker("service", (EmailService, SmsService), desc="В state должен быть объект EmailService или SmsService")
    @StringFieldChecker("selected_channel", desc="Канал, который был выбран", required=False)
    async def choose_channel(
        self,
        params: Params,
        state: NotificationState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> NotificationState:
        """Выбирает сервис на основе канала и сохраняет его в state."""
        if params["channel"] == 'email':
            return NotificationState(
                service=deps.get(EmailService),
                selected_channel='email',
            )
        elif params["channel"] == 'sms':
            return NotificationState(
                service=deps.get(SmsService),
                selected_channel='sms',
            )
        else:
            raise ValueError("Unknown channel")

    @summary_aspect("Отправка")
    async def send(
        self,
        params: Params,
        state: NotificationState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> Result:
        """Отправляет уведомление через выбранный сервис."""
        service = state["service"]
        recipient = cast(str, params["recipient"])
        message = cast(str, params["message"])
        service.send(recipient, message)
        return NotificationAction.Result(success=True)


@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ChildAction(BaseAction['ChildAction.Params', 'ChildAction.Result']):
    """Дочернее действие, удваивающее число."""

    @dataclass(frozen=True)
    class Params(BaseParams):
        """Параметры: число для удвоения."""
        value: int

    @dataclass
    class Result(BaseResult):
        """Результат: удвоенное число."""
        doubled: int

    @aspect("Подготовка")
    @BoolFieldChecker("prepared", desc="Флаг подготовки", required=True)
    async def prepare(
        self,
        params: Params,
        state: ChildState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> ChildState:
        """Аспект подготовки: устанавливает флаг prepared в True."""
        print("\033[91m[ChildAction] Аспект 'prepare' выполняется\033[0m")
        return ChildState(prepared=True)

    @summary_aspect("Удвоить")
    async def handle(
        self,
        params: Params,
        state: ChildState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> Result:
        """Основная логика: удваивает число."""
        print("\033[91m[ChildAction] Summary-аспект 'handle' выполняется\033[0m")
        value = cast(int, params["value"])
        return ChildAction.Result(value * 2)


@depends(ChildAction, description="Дочернее действие")
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ParentAction(BaseAction['ParentAction.Params', 'ParentAction.Result']):
    """Родительское действие, вызывающее дочернее."""

    @dataclass(frozen=True)
    class Params(BaseParams):
        """Параметры: число для обработки."""
        num: int

    @dataclass
    class Result(BaseResult):
        """Результат: число + 10."""
        result: int

    @aspect("Задержка")
    async def delay(
        self,
        params: Params,
        state: ParentState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> ParentState:
        """Аспект с небольшой задержкой (имитация работы)."""
        print("\033[91m[ParentAction] Аспект 'delay' начал работу\033[0m")
        await asyncio.sleep(0.1)
        print("\033[91m[ParentAction] Аспект 'delay' завершил работу\033[0m")
        return ParentState()

    @aspect("Доп. проверка")
    @IntFieldChecker("child_result", desc="Результат дочернего действия", required=True)
    async def extra_check(
        self,
        params: Params,
        state: ParentState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> ParentState:
        """Аспект, вызывающий дочернее действие и сохраняющий результат."""
        print("\033[91m[ParentAction] Аспект 'extra_check' начинает дочернее действие\033[0m")
        child_result = cast(
            ChildAction.Result,
            await deps.run_action(
                ChildAction,
                ChildAction.Params(cast(int, params["num"])),
                connections=connections,
            )
        )
        print(f"\033[91m[ParentAction] Аспект 'extra_check' завершился, результат дочернего: {child_result}\033[0m")
        return ParentState(child_result=child_result.doubled)

    @summary_aspect("Родитель")
    async def handle(
        self,
        params: Params,
        state: ParentState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> Result:
        """Основная логика: вызывает дочернее действие и прибавляет 10."""
        child_result = cast(
            ChildAction.Result,
            await deps.run_action(
                ChildAction,
                ChildAction.Params(cast(int, params["num"])),
                connections=connections,
            )
        )
        assert isinstance(child_result, ChildAction.Result)
        return ParentAction.Result(child_result.doubled + 10)


# ---------- Тестовые плагины ----------

def indent(level: int) -> str:
    """Возвращает строку отступа из 2 пробелов на уровень."""
    return "  " * level


class ConsoleLoggingPlugin(Plugin):
    """Плагин для цветного логирования в консоль с отступами (первый вариант)."""

    def __init__(self, name: str = "PluginA") -> None:
        """Инициализирует плагин с именем."""
        self.name = name

    def get_initial_state(self) -> object:
        """Начальное состояние плагина."""
        return {}

    @on('global_start', '.*', ignore_exceptions=True)
    async def on_global_start(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик глобального старта."""
        print(f"{indent(event.nest_level)}\033[93m[{event.event_name}] {self.name}: Action '{event.action_name}' started with params: {dict(event.params.items())}\033[0m")
        return state_plugin

    @on('global_finish', '.*', ignore_exceptions=True)
    async def on_global_finish(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик глобального завершения."""
        print(f"{indent(event.nest_level)}\033[93m[{event.event_name}] {self.name}: Action '{event.action_name}' finished, duration: {event.duration:.4f}s, result: {event.result}\033[0m")
        return state_plugin

    @on('before:.*', '.*', ignore_exceptions=True)
    async def on_before_aspect(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик перед аспектом."""
        print(f"{indent(event.nest_level + 1)}\033[92m[{event.event_name}] {self.name}: before aspect, current state: {event.state_aspect}\033[0m")
        return state_plugin

    @on('after:.*', '.*', ignore_exceptions=True)
    async def on_after_aspect(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик после аспекта."""
        print(f"{indent(event.nest_level + 1)}\033[92m[{event.event_name}] {self.name}: after aspect, duration: {event.duration:.4f}s, new state: {event.state_aspect}\033[0m")
        return state_plugin


class AnotherLoggingPlugin(Plugin):
    """Плагин для цветного логирования в консоль с отступами (второй вариант)."""

    def __init__(self, name: str = "PluginB") -> None:
        """Инициализирует плагин с именем."""
        self.name = name

    def get_initial_state(self) -> object:
        """Начальное состояние плагина."""
        return {}

    @on('global_start', '.*', ignore_exceptions=True)
    async def on_global_start(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик глобального старта."""
        print(f"{indent(event.nest_level)}\033[94m[{event.event_name}] {self.name}: Action '{event.action_name}' started with params: {dict(event.params.items())}\033[0m")
        return state_plugin

    @on('global_finish', '.*', ignore_exceptions=True)
    async def on_global_finish(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик глобального завершения."""
        print(f"{indent(event.nest_level)}\033[94m[{event.event_name}] {self.name}: Action '{event.action_name}' finished, duration: {event.duration:.4f}s, result: {event.result}\033[0m")
        return state_plugin

    @on('before:.*', '.*', ignore_exceptions=True)
    async def on_before_aspect(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик перед аспектом."""
        print(f"{indent(event.nest_level + 1)}\033[94m[{event.event_name}] {self.name}: before aspect, state: {event.state_aspect}\033[0m")
        return state_plugin

    @on('after:.*', '.*', ignore_exceptions=True)
    async def on_after_aspect(self, state_plugin: object, event: PluginEvent) -> object:
        """Обработчик после аспекта."""
        print(f"{indent(event.nest_level + 1)}\033[94m[{event.event_name}] {self.name}: after aspect, duration: {event.duration:.4f}s, new state: {event.state_aspect}\033[0m")
        return state_plugin


# ---------- Тесты ----------

@pytest.mark.anyio
async def test_choose_channel_aspect() -> None:
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

    empty_conns: dict[str, BaseResourceManager] = {}

    params = NotificationAction.Params(channel='email', message='hi', recipient='a@b.c')
    state: NotificationState = {}
    result_state = await action.choose_channel(params, state, factory, empty_conns)
    assert result_state['service'] is fake_email
    assert result_state['selected_channel'] == 'email'

    params2 = NotificationAction.Params(channel='sms', message='hi', recipient='123')
    state2: NotificationState = {}
    result_state2 = await action.choose_channel(params2, state2, factory, empty_conns)
    assert result_state2['service'] is fake_sms
    assert result_state2['selected_channel'] == 'sms'


@pytest.mark.anyio
async def test_choose_channel_aspect_unknown() -> None:
    """Тест: аспект choose_channel выбрасывает ValueError для неизвестного канала."""
    fake_email: Any = object()
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({EmailService: fake_email}, context=context)
    factory: DependencyFactory = machine.build_factory(NotificationAction)
    action: NotificationAction = NotificationAction()
    params = NotificationAction.Params(channel='fax', message='hi', recipient='x')
    empty_conns: dict[str, BaseResourceManager] = {}

    with pytest.raises(ValueError, match="Unknown channel"):
        await action.choose_channel(params, {}, factory, empty_conns)


@pytest.mark.anyio
async def test_notification_action_with_mock_services() -> None:
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
    params = NotificationAction.Params(channel='email', message='Hello', recipient='user@example.com')
    result = await machine.run(action, params)
    assert result.success is True
    assert fake_email.sent == [('user@example.com', 'Hello')]
    assert fake_sms.sent == []


@pytest.mark.anyio
async def test_parent_action_with_mock_child() -> None:
    """Тест: ParentAction с замоканным результатом дочернего действия."""
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({
        ChildAction: ChildAction.Result(20)
    }, context=context)
    action = ParentAction()
    params = ParentAction.Params(5)
    result = await machine.run(action, params)
    assert result.result == 30  # 20 + 10


@pytest.mark.anyio
async def test_parent_action_with_side_effect() -> None:
    """Тест: ParentAction с side_effect для дочернего действия."""
    def child_side_effect(params: ChildAction.Params) -> ChildAction.Result:
        return ChildAction.Result(params.value * 3)

    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine(
        {ChildAction: child_side_effect}, context=context
    )
    action = ParentAction()
    params = ParentAction.Params(5)
    result = await machine.run(action, params)
    assert result.result == 25  # 5 * 3 = 15 + 10


@pytest.mark.anyio
async def test_parent_action_with_real_child() -> None:
    """Тест: ParentAction с реальным дочерним действием (без плагинов)."""
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine(context=context)
    action = ParentAction()
    params = ParentAction.Params(5)
    result = await machine.run(action, params)
    assert result.result == 20  # 5 * 2 = 10 + 10


@pytest.mark.anyio
async def test_parent_action_with_real_child_and_plugins() -> None:
    """Тест: ParentAction вызывает ChildAction, плагины показывают вложенность с отступами."""
    plugin_a = ConsoleLoggingPlugin("PluginA")
    plugin_b = AnotherLoggingPlugin("PluginB")
    context = Context(user=UserInfo(roles=["user"]))
    machine = ActionTestMachine(context=context)
    machine._plugins.append(plugin_a)
    machine._plugins.append(plugin_b)

    action = ParentAction()
    params = ParentAction.Params(5)
    result = await machine.run(action, params)
    assert result.result == 20


@pytest.mark.anyio
async def test_mock_action_call_tracking() -> None:
    """Тест: MockAction корректно считает вызовы и запоминает параметры."""
    mock_action: MockAction = MockAction(result=ChildAction.Result(100))
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine(
        {ChildAction: mock_action}, context=context
    )
    action = ParentAction()
    params = ParentAction.Params(7)
    result = await machine.run(action, params)
    assert result.result == 110  # 100 + 10
    assert mock_action.call_count == 2
    assert isinstance(mock_action.last_params, ChildAction.Params)
    assert mock_action.last_params.value == 7


# ---------- Тест с inject ----------

class DatabaseService:
    """Пример сервиса, который будет получен через DI-контейнер."""
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def query(self, sql: str) -> str:
        return f"Executing '{sql}' on {self.connection_string}"


def configure_inject(binder: inject.Binder) -> None:
    """Конфигурация inject для теста."""
    binder.bind(DatabaseService, DatabaseService("test_db_connection"))


@depends(DatabaseService, factory=lambda: inject.instance(DatabaseService))
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ActionWithInject(BaseAction['ActionWithInject.Params', 'ActionWithInject.Result']):
    """Действие, получающее зависимость из inject через factory."""

    @dataclass(frozen=True)
    class Params(BaseParams):
        """Параметры: SQL-запрос."""
        sql: str

    @dataclass
    class Result(BaseResult):
        """Результат: строка с ответом."""
        output: str

    @summary_aspect("Использование сервиса из inject")
    async def execute(
        self,
        params: Params,
        state: InjectState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager]
    ) -> Result:
        """Выполняет запрос через сервис из inject."""
        db_service = deps.get(DatabaseService)
        output = db_service.query(cast(str, params["sql"]))
        return ActionWithInject.Result(output)


@pytest.mark.anyio
async def test_depends_factory_with_inject() -> None:
    """Тест интеграции с inject через параметр factory в @depends."""
    inject.clear_and_configure(configure_inject)

    context = Context(user=UserInfo(roles=["user"]))
    machine = ActionTestMachine(context=context)
    action = ActionWithInject()
    params = ActionWithInject.Params(sql="SELECT * FROM users")
    result = await machine.run(action, params)
    assert result.output == "Executing 'SELECT * FROM users' on test_db_connection"

    inject.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])