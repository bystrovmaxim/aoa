# tests/context/test_context.py
"""
Тесты Context — корневой объект контекста выполнения действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Context — корневой объект, объединяющий UserInfo, RequestInfo и RuntimeInfo.
Передаётся в машину при вызове run() и доступен аспектам через ContextView,
плагинам через event.context, шаблонам логирования через {%context.*}.

Context наследует BaseSchema, что обеспечивает:
- Dict-подобный доступ: ctx["user"], ctx.get("request").
- Навигация по вложенным компонентам: ctx.resolve("user.user_id"),
  ctx.resolve("request.trace_id"), ctx.resolve("runtime.hostname").

При создании без аргументов все компоненты инициализируются дефолтами:
UserInfo(), RequestInfo(), RuntimeInfo(). Явный None в любом компоненте
заменяется дефолтным экземпляром через field_validator. Это гарантирует,
что ctx.user, ctx.request, ctx.runtime никогда не равны None.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - С полным набором компонентов — production-контекст.
    - Без аргументов — все компоненты по умолчанию (не None).
    - С частичными данными — только user.
    - None-компоненты заменяются дефолтами (field_validator).

BaseSchema — dict-подобный доступ:
    - __getitem__, __contains__, get, keys.

Навигация через resolve:
    - Два уровня: ctx.resolve("user.user_id").
    - Три уровня: ctx.resolve("user.org") через наследника UserInfo.
    - Все компоненты: user, request, runtime.
    - Отсутствующие пути на любом уровне.

Интеграция с компонентами:
    - ctx.user — экземпляр UserInfo.
    - ctx.request — экземпляр RequestInfo.
    - ctx.runtime — экземпляр RuntimeInfo.

Расширение через наследование:
    - Наследники UserInfo, RequestInfo, RuntimeInfo с явно объявленными
      полями используются для тестирования трёхуровневой навигации.
      Это единственный способ добавить поля — extra="forbid" на всех
      Info-классах запрещает произвольные поля.
"""

from typing import Any

from pydantic import ConfigDict

from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo
from tests.domain_model.roles import AdminRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Наследники Info-классов для тестов трёхуровневой навигации.
#
# UserInfo, RequestInfo, RuntimeInfo не имеют поля extra (extra="forbid").
# Расширение — только через наследование с явно объявленными полями.
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """Наследник UserInfo с дополнительными полями для тестов."""
    model_config = ConfigDict(frozen=True)
    org: str | None = None
    settings: dict[str, Any] = {}


class _ExtendedRequestInfo(RequestInfo):
    """Наследник RequestInfo с дополнительным полем для тестов."""
    model_config = ConfigDict(frozen=True)
    correlation_id: str | None = None


class _ExtendedRuntimeInfo(RuntimeInfo):
    """Наследник RuntimeInfo с дополнительным полем для тестов."""
    model_config = ConfigDict(frozen=True)
    region: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestContextCreation:
    """Создание Context с разными комбинациями компонентов."""

    def test_create_full(self) -> None:
        """
        Context с полным набором компонентов — production-контекст.

        AuthCoordinator.process() создаёт Context с аутентифицированным
        пользователем, метаданными запроса и информацией об окружении.
        """
        # Arrange — все три компонента
        user = UserInfo(user_id="agent_007", roles=(AdminRole,))
        request = RequestInfo(trace_id="trace-123", request_path="/api/v1/orders")
        runtime = RuntimeInfo(hostname="pod-xyz", service_name="order-service")

        # Act — создание полного контекста
        ctx = Context(user=user, request=request, runtime=runtime)

        # Assert — все компоненты установлены
        assert ctx.user is user
        assert ctx.request is request
        assert ctx.runtime is runtime

    def test_create_default(self) -> None:
        """
        Context без аргументов — все компоненты создаются по умолчанию.

        Гарантирует, что ctx.user, ctx.request, ctx.runtime никогда
        не равны None — всегда валидные объекты с дефолтными значениями.
        """
        # Arrange & Act — без аргументов
        ctx = Context()

        # Assert — компоненты не None, а дефолтные экземпляры
        assert ctx.user is not None
        assert ctx.request is not None
        assert ctx.runtime is not None
        assert isinstance(ctx.user, UserInfo)
        assert isinstance(ctx.request, RequestInfo)
        assert isinstance(ctx.runtime, RuntimeInfo)

    def test_create_default_user_values(self) -> None:
        """
        Context() создаёт UserInfo с дефолтами: user_id=None, roles=().
        Это анонимный контекст, создаваемый NoAuthCoordinator.
        """
        # Arrange & Act
        ctx = Context()

        # Assert — дефолтный UserInfo
        assert ctx.user.user_id is None
        assert ctx.user.roles == ()

    def test_create_with_user_only(self) -> None:
        """
        Context только с user — request и runtime создаются по умолчанию.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=(ManagerRole,))

        # Act — только user
        ctx = Context(user=user)

        # Assert — user задан, остальное по умолчанию
        assert ctx.user.user_id == "u1"
        assert ctx.request is not None
        assert ctx.runtime is not None
        assert ctx.request.trace_id is None
        assert ctx.runtime.hostname is None

    def test_none_components_replaced_with_defaults(self) -> None:
        """
        Явный None в компоненте заменяется дефолтным экземпляром.

        Context(user=None) эквивалентен Context() — user будет
        UserInfo() с дефолтами, а не None. Реализовано через
        field_validator("user", mode="before") в модели Context.
        """
        # Arrange & Act — явные None
        ctx = Context(user=None, request=None, runtime=None)

        # Assert — None заменены на дефолтные объекты
        assert ctx.user is not None
        assert ctx.request is not None
        assert ctx.runtime is not None
        assert isinstance(ctx.user, UserInfo)
        assert isinstance(ctx.request, RequestInfo)
        assert isinstance(ctx.runtime, RuntimeInfo)


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — dict-подобный доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestContextDictAccess:
    """Dict-подобный доступ к компонентам Context через BaseSchema."""

    def test_getitem_user(self) -> None:
        """
        ctx["user"] → объект UserInfo.

        BaseSchema.__getitem__ делегирует в getattr(self, "user").
        """
        # Arrange
        user = UserInfo(user_id="u1")
        ctx = Context(user=user)

        # Act & Assert — доступ через скобки возвращает тот же объект
        assert ctx["user"] is user

    def test_getitem_request(self) -> None:
        """
        ctx["request"] → объект RequestInfo.
        """
        # Arrange
        request = RequestInfo(trace_id="t1")
        ctx = Context(request=request)

        # Act & Assert
        assert ctx["request"] is request

    def test_getitem_runtime(self) -> None:
        """
        ctx["runtime"] → объект RuntimeInfo.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="h1")
        ctx = Context(runtime=runtime)

        # Act & Assert
        assert ctx["runtime"] is runtime

    def test_contains(self) -> None:
        """
        "user" in ctx → True; "nonexistent" in ctx → False.
        """
        # Arrange
        ctx = Context()

        # Act & Assert
        assert "user" in ctx
        assert "request" in ctx
        assert "runtime" in ctx
        assert "nonexistent" not in ctx

    def test_get(self) -> None:
        """
        ctx.get("user") → UserInfo; ctx.get("missing") → None.
        """
        # Arrange
        ctx = Context(user=UserInfo(user_id="u1"))

        # Act & Assert
        assert ctx.get("user") is not None
        assert ctx.get("user").user_id == "u1"
        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", "fallback") == "fallback"

    def test_keys(self) -> None:
        """
        keys() содержит user, request, runtime.

        Context хранит три компонента как pydantic-поля.
        BaseSchema.keys() возвращает model_fields.keys().
        """
        # Arrange
        ctx = Context()

        # Act
        keys = ctx.keys()

        # Assert — три компонента присутствуют
        assert "user" in keys
        assert "request" in keys
        assert "runtime" in keys


# ═════════════════════════════════════════════════════════════════════════════
# Навигация через resolve — два уровня
# ═════════════════════════════════════════════════════════════════════════════


class TestContextResolveTwoLevels:
    """resolve через два уровня: Context → компонент → поле."""

    def test_resolve_user_id(self) -> None:
        """
        resolve("user.user_id") — Context → UserInfo → user_id.

        Первый шаг: BaseSchema.__getitem__(ctx, "user") → UserInfo.
        Второй шаг: BaseSchema.__getitem__(UserInfo, "user_id") → "agent_007".
        """
        # Arrange
        ctx = Context(user=UserInfo(user_id="agent_007"))

        # Act
        result = ctx.resolve("user.user_id")

        # Assert
        assert result == "agent_007"

    def test_resolve_user_roles(self) -> None:
        """
        resolve("user.roles") → кортеж типов ролей.
        """
        # Arrange
        ctx = Context(user=UserInfo(roles=(AdminRole, UserRole)))

        # Act
        result = ctx.resolve("user.roles")

        # Assert
        assert result == (AdminRole, UserRole)

    def test_resolve_request_trace_id(self) -> None:
        """
        resolve("request.trace_id") — Context → RequestInfo → trace_id.
        """
        # Arrange
        ctx = Context(request=RequestInfo(trace_id="trace-abc"))

        # Act
        result = ctx.resolve("request.trace_id")

        # Assert
        assert result == "trace-abc"

    def test_resolve_request_path(self) -> None:
        """
        resolve("request.request_path") → путь запроса.
        """
        # Arrange
        ctx = Context(request=RequestInfo(request_path="/api/v1/orders"))

        # Act
        result = ctx.resolve("request.request_path")

        # Assert
        assert result == "/api/v1/orders"

    def test_resolve_runtime_hostname(self) -> None:
        """
        resolve("runtime.hostname") — Context → RuntimeInfo → hostname.
        """
        # Arrange
        ctx = Context(runtime=RuntimeInfo(hostname="pod-xyz-42"))

        # Act
        result = ctx.resolve("runtime.hostname")

        # Assert
        assert result == "pod-xyz-42"

    def test_resolve_runtime_service_name(self) -> None:
        """
        resolve("runtime.service_name") → имя сервиса.
        """
        # Arrange
        ctx = Context(runtime=RuntimeInfo(service_name="order-service"))

        # Act
        result = ctx.resolve("runtime.service_name")

        # Assert
        assert result == "order-service"


# ═════════════════════════════════════════════════════════════════════════════
# Навигация через resolve — три уровня (через наследников Info-классов)
# ═════════════════════════════════════════════════════════════════════════════


class TestContextResolveThreeLevels:
    """
    resolve через три уровня: Context → наследник Info → поле наследника.

    UserInfo, RequestInfo, RuntimeInfo не имеют поля extra (extra="forbid").
    Трёхуровневая навигация тестируется через наследников с явно
    объявленными полями — единственный способ расширения в новой
    архитектуре.
    """

    def test_resolve_user_extended_field(self) -> None:
        """
        resolve("user.org") — Context → _ExtendedUserInfo → org.

        Три уровня: BaseSchema (Context) → BaseSchema (_ExtendedUserInfo)
        → значение поля.
        """
        # Arrange — наследник UserInfo с полем org
        ctx = Context(user=_ExtendedUserInfo(org="acme"))

        # Act
        result = ctx.resolve("user.org")

        # Assert
        assert result == "acme"

    def test_resolve_request_extended_field(self) -> None:
        """
        resolve("request.correlation_id") — Context → _ExtendedRequestInfo
        → correlation_id.
        """
        # Arrange — наследник RequestInfo с полем correlation_id
        ctx = Context(request=_ExtendedRequestInfo(correlation_id="corr-001"))

        # Act
        result = ctx.resolve("request.correlation_id")

        # Assert
        assert result == "corr-001"

    def test_resolve_runtime_extended_field(self) -> None:
        """
        resolve("runtime.region") — Context → _ExtendedRuntimeInfo → region.
        """
        # Arrange — наследник RuntimeInfo с полем region
        ctx = Context(runtime=_ExtendedRuntimeInfo(region="eu-west-1"))

        # Act
        result = ctx.resolve("runtime.region")

        # Assert
        assert result == "eu-west-1"

    def test_resolve_deep_nested_dict_field(self) -> None:
        """
        resolve("user.settings.theme") — четыре уровня навигации.

        Context → _ExtendedUserInfo → settings (dict) → theme (значение).
        Навигация переключается со стратегии __getitem__ (BaseSchema)
        на прямой доступ по ключу (dict).
        """
        # Arrange — наследник UserInfo с полем settings (dict)
        ctx = Context(user=_ExtendedUserInfo(
            settings={"theme": "dark", "lang": "ru"},
        ))

        # Act
        result = ctx.resolve("user.settings.theme")

        # Assert
        assert result == "dark"


# ═════════════════════════════════════════════════════════════════════════════
# Навигация через resolve — отсутствующие пути
# ═════════════════════════════════════════════════════════════════════════════


class TestContextResolveMissing:
    """resolve для отсутствующих путей возвращает default."""

    def test_missing_component_attribute(self) -> None:
        """
        resolve("user.nonexistent") — атрибут не существует в UserInfo.
        """
        # Arrange
        ctx = Context(user=UserInfo(user_id="u1"))

        # Act
        result = ctx.resolve("user.nonexistent", default="N/A")

        # Assert
        assert result == "N/A"

    def test_missing_intermediate(self) -> None:
        """
        resolve("user.nonexistent.deep") — промежуточный атрибут не найден.

        Цепочка прерывается на "nonexistent", оставшиеся сегменты
        не обрабатываются.
        """
        # Arrange
        ctx = Context()

        # Act
        result = ctx.resolve("user.nonexistent.deep", default="fallback")

        # Assert
        assert result == "fallback"

    def test_missing_extended_field_key(self) -> None:
        """
        resolve("user.settings.missing_key") — ключ не существует в dict.

        _ExtendedUserInfo имеет поле settings: dict. Навигация доходит
        до dict, но ключ "missing_key" в нём отсутствует → default.
        """
        # Arrange — наследник UserInfo с полем settings
        ctx = Context(user=_ExtendedUserInfo(
            settings={"org": "acme"},
        ))

        # Act
        result = ctx.resolve("user.settings.missing_key", default="none")

        # Assert
        assert result == "none"

    def test_missing_top_level(self) -> None:
        """
        resolve("nonexistent") — атрибут не существует на Context.
        """
        # Arrange
        ctx = Context()

        # Act
        result = ctx.resolve("nonexistent")

        # Assert — None по умолчанию
        assert result is None

    def test_missing_without_default(self) -> None:
        """
        resolve("user.nonexistent") без default → None.

        resolve никогда не бросает исключение — безопасен для шаблонов
        логирования.
        """
        # Arrange
        ctx = Context()

        # Act
        result = ctx.resolve("user.nonexistent")

        # Assert
        assert result is None
