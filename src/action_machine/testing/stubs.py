# src/action_machine/testing/stubs.py
"""
Стабы контекста для тестирования действий ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль предоставляет готовые стабы с разумными значениями по умолчанию
для всех компонентов контекста выполнения: пользователь (UserInfo),
информация о запросе (RequestInfo), информация об окружении (RuntimeInfo)
и полный контекст (Context).

Стабы избавляют от необходимости вручную создавать и настраивать контекст
в каждом тесте. Типичный тест-кейс начинается с одной строки:

    ctx = ContextStub()

Все стабы поддерживают переопределение любого поля через именованные
аргументы:

    ctx = ContextStub(user=UserInfoStub(user_id="admin", roles=(AdminRole,)))

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- **UserInfoStub** — стаб информации о пользователе.
  Дефолты: user_id="test_user", roles=(StubTesterRole,).

- **RuntimeInfoStub** — стаб информации об окружении выполнения.
  Дефолты: hostname="test-host", service_name="test-service",
  service_version="0.0.1".

- **RequestInfoStub** — стаб информации о входящем запросе.
  Дефолты: trace_id="test-trace-000", request_path="/test",
  protocol="test".

- **ContextStub** — стаб полного контекста выполнения. Объединяет
  UserInfoStub, RequestInfoStub и RuntimeInfoStub. Создаётся без
  аргументов для типичного тест-кейса или с переопределением
  отдельных компонентов.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. РАЗУМНЫЕ ДЕФОЛТЫ. Каждый стаб содержит значения, которые проходят
   любую валидацию: непустые строки, корректные форматы, валидные роли.
   Тестировщику не нужно думать о минимально валидном контексте.

2. ПЕРЕОПРЕДЕЛЯЕМОСТЬ. Любое поле может быть переопределено через
   именованные аргументы. Для добавления кастомных полей — создаётся
   наследник соответствующего Info-класса.

3. ТИПОБЕЗОПАСНОСТЬ. Стабы возвращают экземпляры реальных классов
   (UserInfo, RequestInfo, RuntimeInfo, Context), поэтому они проходят
   isinstance-проверки и совместимы со всеми компонентами системы.

4. НЕЗАВИСИМОСТЬ. Каждый стаб самодостаточен. UserInfoStub можно
   использовать отдельно от ContextStub.

5. СТРОГАЯ СТРУКТУРА. Все Info-классы имеют extra="forbid". Стабы
   принимают только объявленные поля — произвольные kwargs запрещены.
   Расширение — через наследование Info-класса с явными полями.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing import (
        ContextStub,
        UserInfoStub,
        RequestInfoStub,
        RuntimeInfoStub,
    )

    # Минимальный тест — одна строка для контекста:
    result = await machine.run(
        context=ContextStub(),
        action=PingAction(),
        params=PingAction.Params(),
        rollup=False,
    )

    # Тест с конкретным пользователем:
    admin_ctx = ContextStub(
        user=UserInfoStub(user_id="admin_1", roles=(AdminRole, ManagerRole)),
    )

    # Тест с конкретным trace_id:
    traced_ctx = ContextStub(
        request=RequestInfoStub(trace_id="trace-abc-123"),
    )

    # Отдельные стабы:
    user = UserInfoStub(roles=(AdminRole,))
    runtime = RuntimeInfoStub(hostname="prod-server-01")
    request = RequestInfoStub(request_path="/api/v1/orders", protocol="https")

    # Расширение через наследование Info-класса:
    class TenantUserInfo(UserInfo):
        tenant_id: str = "default"

    tenant_user = TenantUserInfo(user_id="admin", roles=(AdminRole,), tenant_id="acme")
    ctx = ContextStub(user=tenant_user)
"""

from action_machine.auth.application_role import ApplicationRole
from action_machine.auth.base_role import BaseRole
from action_machine.auth.role_mode import RoleMode, role_mode
from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo


@role_mode(RoleMode.ALIVE)
class StubTesterRole(ApplicationRole):
    """Default assignable role for ``UserInfoStub`` and TestBench user defaults."""

    name = "tester"
    description = "Default role for UserInfoStub in tests."


def UserInfoStub(
    user_id: str = "test_user",
    roles: tuple[type[BaseRole], ...] | list[type[BaseRole]] | None = None,
) -> UserInfo:
    """
    Создаёт стаб информации о пользователе с разумными дефолтами.

    Возвращает экземпляр реального класса UserInfo, заполненный
    тестовыми значениями. Все объявленные поля могут быть переопределены.

    Аргументы:
        user_id: идентификатор пользователя. По умолчанию "test_user".
        roles: кортеж (или список) подклассов ``BaseRole``. По умолчанию
            ``(StubTesterRole,)``.

    Возвращает:
        UserInfo — стаб с тестовыми значениями.

    Пример:
        user = UserInfoStub()
        assert user.user_id == "test_user"
        assert user.roles == (StubTesterRole,)

        admin = UserInfoStub(user_id="admin_1", roles=(StubTesterRole,))
        assert StubTesterRole in admin.roles
    """
    resolved: tuple[type[BaseRole], ...] = (
        (StubTesterRole,) if roles is None else tuple(roles)
    )
    return UserInfo(user_id=user_id, roles=resolved)


def RuntimeInfoStub(
    hostname: str = "test-host",
    service_name: str = "test-service",
    service_version: str = "0.0.1",
    container_id: str | None = None,
    pod_name: str | None = None,
) -> RuntimeInfo:
    """
    Создаёт стаб информации об окружении выполнения с разумными дефолтами.

    Возвращает экземпляр реального класса RuntimeInfo, заполненный
    тестовыми значениями.

    Аргументы:
        hostname: имя хоста. По умолчанию "test-host".
        service_name: название сервиса. По умолчанию "test-service".
        service_version: версия сервиса. По умолчанию "0.0.1".
        container_id: идентификатор Docker-контейнера. По умолчанию None.
        pod_name: имя пода Kubernetes. По умолчанию None.

    Возвращает:
        RuntimeInfo — стаб с тестовыми значениями.

    Пример:
        runtime = RuntimeInfoStub()
        assert runtime.hostname == "test-host"

        prod = RuntimeInfoStub(hostname="prod-01", service_version="2.3.0")
    """
    return RuntimeInfo(
        hostname=hostname,
        service_name=service_name,
        service_version=service_version,
        container_id=container_id,
        pod_name=pod_name,
    )


def RequestInfoStub(
    trace_id: str = "test-trace-000",
    request_path: str = "/test",
    protocol: str = "test",
    request_method: str = "TEST",
    full_url: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    request_timestamp: None = None,
) -> RequestInfo:
    """
    Создаёт стаб информации о входящем запросе с разумными дефолтами.

    Возвращает экземпляр реального класса RequestInfo, заполненный
    тестовыми значениями.

    Аргументы:
        trace_id: уникальный идентификатор запроса. По умолчанию "test-trace-000".
        request_path: путь запроса. По умолчанию "/test".
        protocol: протокол вызова. По умолчанию "test".
        request_method: HTTP-метод или тип вызова. По умолчанию "TEST".
        full_url: полный URL запроса. По умолчанию None.
        client_ip: IP-адрес клиента. По умолчанию None.
        user_agent: заголовок User-Agent. По умолчанию None.
        request_timestamp: время получения запроса. По умолчанию None.

    Возвращает:
        RequestInfo — стаб с тестовыми значениями.

    Пример:
        request = RequestInfoStub()
        assert request.trace_id == "test-trace-000"

        http = RequestInfoStub(
            request_path="/api/v1/orders",
            protocol="https",
            request_method="POST",
            client_ip="192.168.1.1",
        )
    """
    return RequestInfo(
        trace_id=trace_id,
        request_path=request_path,
        protocol=protocol,
        request_method=request_method,
        full_url=full_url,
        client_ip=client_ip,
        user_agent=user_agent,
        request_timestamp=request_timestamp,
    )


def ContextStub(
    user: UserInfo | None = None,
    request: RequestInfo | None = None,
    runtime: RuntimeInfo | None = None,
) -> Context:
    """
    Создаёт стаб полного контекста выполнения с разумными дефолтами.

    Объединяет UserInfoStub, RequestInfoStub и RuntimeInfoStub в один
    объект Context. Каждый компонент может быть переопределён.

    Если компонент не передан — создаётся стаб с дефолтными значениями.

    Аргументы:
        user: информация о пользователе. По умолчанию UserInfoStub().
        request: информация о запросе. По умолчанию RequestInfoStub().
        runtime: информация об окружении. По умолчанию RuntimeInfoStub().

    Возвращает:
        Context — стаб контекста с тестовыми значениями.

    Пример:
        # Минимальный контекст:
        ctx = ContextStub()
        assert ctx.user.user_id == "test_user"
        assert ctx.request.trace_id == "test-trace-000"
        assert ctx.runtime.hostname == "test-host"

        # Контекст с конкретным пользователем:
        ctx = ContextStub(user=UserInfoStub(user_id="admin", roles=(StubTesterRole,)))
        assert ctx.user.user_id == "admin"

        # Контекст с конкретным trace_id:
        ctx = ContextStub(request=RequestInfoStub(trace_id="my-trace"))
        assert ctx.request.trace_id == "my-trace"
    """
    return Context(
        user=user if user is not None else UserInfoStub(),
        request=request if request is not None else RequestInfoStub(),
        runtime=runtime if runtime is not None else RuntimeInfoStub(),
    )
