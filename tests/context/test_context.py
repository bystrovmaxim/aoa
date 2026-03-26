# tests/context/test_context.py
"""
Тесты для класса Context.

Проверяем:
- Создание с компонентами и без
- Доступ через атрибуты и dict-протокол
- Подстановку значений по умолчанию
"""

from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo


class TestContext:
    """Тесты для Context."""

    def test_create_with_components(self):
        """Создание Context с переданными компонентами."""
        user = UserInfo(user_id="123")
        request = RequestInfo(trace_id="abc")
        env = RuntimeInfo(hostname="test")

        ctx = Context(user=user, request=request, runtime=env)

        assert ctx.user is user
        assert ctx.request is request
        assert ctx.runtime is env

    def test_default_components_are_created(self):
        """Если компоненты не переданы, создаются пустые экземпляры."""
        ctx = Context()

        assert isinstance(ctx.user, UserInfo)
        assert isinstance(ctx.request, RequestInfo)
        assert isinstance(ctx.runtime, RuntimeInfo)

    def test_extra_dict(self):
        """Context имеет поле _extra для произвольных данных."""
        ctx = Context()
        ctx._extra["key"] = "value"
        assert ctx._extra["key"] == "value"

    def test_dict_protocol_access_to_components(self):
        """Доступ к компонентам через __getitem__."""
        user = UserInfo(user_id="123")
        ctx = Context(user=user)

        assert ctx["user"] is user
        assert ctx["request"] is ctx.request
        assert ctx["runtime"] is ctx.runtime

    def test_dict_protocol_contains(self):
        """Проверка наличия ключей."""
        ctx = Context()
        assert "user" in ctx
        assert "request" in ctx
        assert "runtime" in ctx
        assert "missing" not in ctx