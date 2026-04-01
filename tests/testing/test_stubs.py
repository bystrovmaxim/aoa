# tests/testing/test_stubs.py
"""
Тесты для стабов контекста — готовых объектов с дефолтными значениями для тестов.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

UserInfoStub:
    - Дефолтные значения (user_id, roles).
    - Переопределение полей.
    - Является экземпляром настоящего UserInfo.

RuntimeInfoStub:
    - Дефолтные значения (hostname, service_name, service_version).
    - Переопределение полей.

RequestInfoStub:
    - Дефолтные значения (trace_id, request_path, protocol, request_method).
    - Переопределение полей.

ContextStub:
    - Собирает все три стаба с дефолтами.
    - Переопределение отдельных компонентов не влияет на остальные.
    - Поддерживает resolve() для dot-path навигации.
"""

from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo
from action_machine.testing import (
    ContextStub,
    RequestInfoStub,
    RuntimeInfoStub,
    UserInfoStub,
)


class TestUserInfoStub:

    def test_defaults(self):
        """
        Проверяет дефолтные значения UserInfoStub:

        1. user_id="test_user" — стандартный тестовый пользователь.
        2. roles=["tester"] — одна роль, достаточная для действий с ROLE_ANY.

        Дефолты должны проходить любую валидацию: непустая строка, непустой список ролей.
        """
        user = UserInfoStub()
        assert user.user_id == "test_user"
        assert user.roles == ["tester"]

    def test_custom_values(self):
        """UserInfoStub должен принимать пользовательские user_id и roles."""
        user = UserInfoStub(user_id="admin", roles=["admin", "manager"])
        assert user.user_id == "admin"
        assert user.roles == ["admin", "manager"]

    def test_empty_roles(self):
        """UserInfoStub с пустыми ролями — для тестирования действий с ROLE_NONE."""
        assert UserInfoStub(roles=[]).roles == []

    def test_is_real_user_info(self):
        """
        Проверяет, что стаб — экземпляр настоящего UserInfo:

        Это гарантирует, что isinstance-проверки в машине (проверка ролей,
        доступ к user.roles) работают со стабом так же, как с реальным объектом.
        """
        assert isinstance(UserInfoStub(), UserInfo)

    def test_dict_access(self):
        """UserInfoStub поддерживает dict-доступ через ReadableMixin."""
        assert UserInfoStub()["user_id"] == "test_user"
        assert "roles" in UserInfoStub()


class TestRuntimeInfoStub:

    def test_defaults(self):
        """
        Проверяет дефолтные значения RuntimeInfoStub:

        1. hostname="test-host" — идентифицирует хост в логах.
        2. service_name="test-service" — имя сервиса.
        3. service_version="0.0.1" — версия.
        """
        runtime = RuntimeInfoStub()
        assert runtime.hostname == "test-host"
        assert runtime.service_name == "test-service"
        assert runtime.service_version == "0.0.1"

    def test_custom_values(self):
        """RuntimeInfoStub должен принимать пользовательские значения."""
        runtime = RuntimeInfoStub(hostname="prod-01", service_version="2.0.0")
        assert runtime.hostname == "prod-01"
        assert runtime.service_version == "2.0.0"

    def test_is_real_runtime_info(self):
        """Стаб — экземпляр настоящего RuntimeInfo для совместимости с Context."""
        assert isinstance(RuntimeInfoStub(), RuntimeInfo)


class TestRequestInfoStub:

    def test_defaults(self):
        """
        Проверяет дефолтные значения RequestInfoStub:

        1. trace_id="test-trace-000" — для сквозной трассировки в логах.
        2. request_path="/test" — путь запроса.
        3. protocol="test" — протокол вызова.
        4. request_method="TEST" — метод.
        """
        req = RequestInfoStub()
        assert req.trace_id == "test-trace-000"
        assert req.request_path == "/test"
        assert req.protocol == "test"
        assert req.request_method == "TEST"

    def test_custom_values(self):
        """RequestInfoStub должен принимать пользовательские значения."""
        req = RequestInfoStub(trace_id="abc", protocol="https", request_method="POST")
        assert req.trace_id == "abc"
        assert req.protocol == "https"
        assert req.request_method == "POST"

    def test_is_real_request_info(self):
        """Стаб — экземпляр настоящего RequestInfo для совместимости с Context."""
        assert isinstance(RequestInfoStub(), RequestInfo)


class TestContextStub:

    def test_defaults(self):
        """
        Проверяет, что ContextStub без аргументов собирает все три стаба с дефолтами:

        1. user из UserInfoStub — user_id="test_user".
        2. request из RequestInfoStub — trace_id="test-trace-000".
        3. runtime из RuntimeInfoStub — hostname="test-host".

        Одна строка ctx = ContextStub() создаёт полный рабочий контекст для теста.
        """
        ctx = ContextStub()
        assert ctx.user.user_id == "test_user"
        assert ctx.user.roles == ["tester"]
        assert ctx.request.trace_id == "test-trace-000"
        assert ctx.runtime.hostname == "test-host"

    def test_custom_user_preserves_other_defaults(self):
        """
        Проверяет, что переопределение одного компонента не влияет на остальные:

        Передаём custom user — request и runtime остаются дефолтными.
        Без этой гарантии переопределение user сбросит request и runtime.
        """
        ctx = ContextStub(user=UserInfoStub(user_id="admin", roles=["admin"]))
        assert ctx.user.user_id == "admin"
        assert ctx.request.trace_id == "test-trace-000"
        assert ctx.runtime.hostname == "test-host"

    def test_custom_request(self):
        """ContextStub должен принимать пользовательский request."""
        ctx = ContextStub(request=RequestInfoStub(trace_id="custom"))
        assert ctx.request.trace_id == "custom"

    def test_custom_runtime(self):
        """ContextStub должен принимать пользовательский runtime."""
        ctx = ContextStub(runtime=RuntimeInfoStub(hostname="prod"))
        assert ctx.runtime.hostname == "prod"

    def test_is_real_context(self):
        """Стаб — экземпляр настоящего Context для совместимости с машиной."""
        assert isinstance(ContextStub(), Context)

    def test_resolve_nested_paths(self):
        """
        Проверяет, что ContextStub поддерживает dot-path resolve:

        1. resolve("user.user_id") — навигация во вложенный объект user.
        2. resolve("request.trace_id") — навигация в request.
        3. resolve("runtime.hostname") — навигация в runtime.

        Это необходимо для шаблонов логирования вида {%context.user.user_id}.
        """
        ctx = ContextStub()
        assert ctx.resolve("user.user_id") == "test_user"
        assert ctx.resolve("request.trace_id") == "test-trace-000"
        assert ctx.resolve("runtime.hostname") == "test-host"
