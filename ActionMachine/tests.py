# ActionMachine/tests.py
import sys
import os
from typing import Any, Dict, List, Tuple
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
from ActionMachine.Auth.CheckRoles import CheckRoles
from ActionMachine.Context.UserInfo import UserInfo
from ActionMachine.Context.Context import Context
import pytest


class EmailService:
    def send(self, to: str, msg: str) -> None:
        print(f"Sending email to {to}: {msg}")


class SmsService:
    def send(self, to: str, msg: str) -> None:
        print(f"Sending SMS to {to}: {msg}")


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
    @InstanceOfChecker("service", (EmailService, SmsService), desc="В state должен быть объект EmailService или SmsService")
    @StringFieldChecker("selected_channel", desc="Канал, который был выбран", required=False)
    def choose_channel(self, params: Params, state: Dict[str, Any], deps: DependencyFactory) -> Dict[str, Any]:
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
    def send(self, params: Params, state: Dict[str, Any], deps: DependencyFactory) -> Result:
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

    @summary_aspect("Удвоить")
    def handle(self, params: Params, state: Dict[str, Any], deps: DependencyFactory) -> Result:
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

    @summary_aspect("Родитель")
    def handle(self, params: Params, state: Dict[str, Any], deps: DependencyFactory) -> Result:
        child_result = deps.run_action(ChildAction, ChildAction.Params(params.num))
        assert isinstance(child_result, ChildAction.Result)
        return ParentAction.Result(child_result.doubled + 10)


def test_choose_channel_aspect() -> None:
    fake_email: Any = object()
    fake_sms: Any = object()
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({
        EmailService: fake_email,
        SmsService: fake_sms
    }, context=context)
    factory: DependencyFactory = machine.build_factory(NotificationAction)
    action: NotificationAction = NotificationAction()
    params: NotificationAction.Params = NotificationAction.Params(channel='email', message='hi', recipient='a@b.c')
    state: Dict[str, Any] = {}
    result_state: Dict[str, Any] = action.choose_channel(params, state, factory)
    assert result_state['service'] is fake_email
    assert result_state['selected_channel'] == 'email'
    params2 = NotificationAction.Params(channel='sms', message='hi', recipient='123')
    state2: Dict[str, Any] = {}
    result_state2 = action.choose_channel(params2, state2, factory)
    assert result_state2['service'] is fake_sms
    assert result_state2['selected_channel'] == 'sms'


def test_choose_channel_aspect_unknown() -> None:
    fake_email: Any = object()
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({EmailService: fake_email}, context=context)
    factory: DependencyFactory = machine.build_factory(NotificationAction)
    action: NotificationAction = NotificationAction()
    params: NotificationAction.Params = NotificationAction.Params(channel='fax', message='hi', recipient='x')
    with pytest.raises(ValueError, match="Unknown channel"):
        action.choose_channel(params, {}, factory)


def test_notification_action_with_mock_services() -> None:
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
    action: NotificationAction = NotificationAction()
    params: NotificationAction.Params = NotificationAction.Params(channel='email', message='Hello', recipient='test@ex.com')
    result: NotificationAction.Result = machine.run(action, params)
    assert result.success is True
    assert fake_email.sent == [('test@ex.com', 'Hello')]
    assert fake_sms.sent == []


def test_parent_action_with_mock_child() -> None:
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({
        ChildAction: ChildAction.Result(20)
    }, context=context)
    action: ParentAction = ParentAction()
    params: ParentAction.Params = ParentAction.Params(5)
    result: ParentAction.Result = machine.run(action, params)
    assert result.result == 30


def test_parent_action_with_side_effect() -> None:
    def child_side_effect(params: ChildAction.Params) -> ChildAction.Result:
        return ChildAction.Result(params.value * 3)

    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({ChildAction: child_side_effect}, context=context)
    action: ParentAction = ParentAction()
    params: ParentAction.Params = ParentAction.Params(5)
    result: ParentAction.Result = machine.run(action, params)
    assert result.result == 25


def test_parent_action_with_real_child() -> None:
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine(context=context)
    action: ParentAction = ParentAction()
    params: ParentAction.Params = ParentAction.Params(5)
    result: ParentAction.Result = machine.run(action, params)
    assert result.result == 20


def test_mock_action_call_tracking() -> None:
    mock_action: MockAction = MockAction(result=ChildAction.Result(100))
    context = Context(user=UserInfo(roles=["user"]))
    machine: ActionTestMachine = ActionTestMachine({ChildAction: mock_action}, context=context)
    action: ParentAction = ParentAction()
    params: ParentAction.Params = ParentAction.Params(7)
    result: ParentAction.Result = machine.run(action, params)
    assert result.result == 110
    assert mock_action.call_count == 1
    assert isinstance(mock_action.last_params, ChildAction.Params)
    assert mock_action.last_params.value == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])