# tests/context/test_context_view.py
"""
Тесты ContextView — frozen-объект с контролируемым доступом к полям контекста.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ContextView — единственный легальный способ доступа к данным контекста
из аспектов и обработчиков ошибок. Создаётся машиной для методов,
декорированных @context_requires. Предоставляет метод get(key),
который проверяет принадлежность ключа к множеству разрешённых
и делегирует в context.resolve(key).

Обращение к незапрошенному полю → ContextAccessError.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Разрешённый доступ:
    - Доступ к user.user_id, user.roles через Ctx-константы.
    - Доступ к request.trace_id, runtime.hostname.
    - Несколько разрешённых ключей одновременно.

Запрещённый доступ:
    - Незарегистрированный ключ → ContextAccessError.
    - Ключ из другого компонента → ContextAccessError.
    - Пустое множество разрешённых ключей → всё запрещено.

Несуществующие поля:
    - Разрешённый ключ, но значение None → возвращает None.
    - Кастомный путь, поле не существует → возвращает None.

Кастомные поля через наследников Info-классов:
    - Наследник UserInfo с полем billing_plan.
    - Наследник RequestInfo с полем ab_variant.

Frozen-семантика:
    - Запись атрибутов запрещена.
    - Удаление атрибутов запрещено.

Интроспекция:
    - allowed_keys возвращает frozenset.
    - repr содержит имена ключей.
"""


import pytest
from pydantic import ConfigDict

from action_machine.intents.context.context import Context
from action_machine.intents.context.context_view import ContextView
from action_machine.intents.context.ctx_constants import Ctx
from action_machine.intents.context.request_info import RequestInfo
from action_machine.intents.context.runtime_info import RuntimeInfo
from action_machine.intents.context.user_info import UserInfo
from action_machine.model.exceptions import ContextAccessError
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Наследники Info-классов для тестов кастомных полей.
#
# UserInfo, RequestInfo, RuntimeInfo не имеют полей extra и tags
# (extra="forbid"). Расширение — только через наследование с явно
# объявленными полями.
# ═════════════════════════════════════════════════════════════════════════════


class _BillingUserInfo(UserInfo):
    """Наследник UserInfo с полем billing_plan для тестов."""
    model_config = ConfigDict(frozen=True)
    billing_plan: str | None = None


class _TaggedRequestInfo(RequestInfo):
    """Наследник RequestInfo с полем ab_variant для тестов."""
    model_config = ConfigDict(frozen=True)
    ab_variant: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# Разрешённый доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestAllowedAccess:
    """Доступ к разрешённым ключам возвращает корректные значения."""

    def test_get_user_id(self) -> None:
        """
        ContextView.get(Ctx.User.user_id) возвращает user_id из контекста.

        ContextView проверяет, что ключ "user.user_id" входит в множество
        разрешённых, и делегирует в context.resolve("user.user_id").
        """
        # Arrange — контекст с user_id, ContextView разрешает user.user_id
        context = Context(user=UserInfo(user_id="agent_007"))
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act — запрашиваем разрешённое поле
        result = view.get(Ctx.User.user_id)

        # Assert — значение из контекста
        assert result == "agent_007"

    def test_get_user_roles(self) -> None:
        """
        ContextView.get(Ctx.User.roles) возвращает кортеж типов ролей.
        """
        # Arrange — контекст с ролями, ContextView разрешает user.roles
        context = Context(user=UserInfo(roles=(AdminRole, UserRole)))
        view = ContextView(context, frozenset({Ctx.User.roles}))

        # Act — запрашиваем разрешённое поле
        result = view.get(Ctx.User.roles)

        # Assert — кортеж ролей из контекста
        assert result == (AdminRole, UserRole)

    def test_get_request_trace_id(self) -> None:
        """
        ContextView.get(Ctx.Request.trace_id) возвращает trace_id запроса.
        """
        # Arrange — контекст с trace_id в запросе
        context = Context(request=RequestInfo(trace_id="trace-abc-123"))
        view = ContextView(context, frozenset({Ctx.Request.trace_id}))

        # Act
        result = view.get(Ctx.Request.trace_id)

        # Assert
        assert result == "trace-abc-123"

    def test_get_runtime_hostname(self) -> None:
        """
        ContextView.get(Ctx.Runtime.hostname) возвращает hostname окружения.
        """
        # Arrange — контекст с hostname в runtime
        context = Context(runtime=RuntimeInfo(hostname="prod-server-01"))
        view = ContextView(context, frozenset({Ctx.Runtime.hostname}))

        # Act
        result = view.get(Ctx.Runtime.hostname)

        # Assert
        assert result == "prod-server-01"

    def test_get_multiple_allowed_keys(self) -> None:
        """
        ContextView с несколькими разрешёнными ключами — каждый доступен.
        """
        # Arrange — ContextView разрешает несколько ключей
        context = Context(
            user=UserInfo(user_id="u1", roles=(ManagerRole,)),
            request=RequestInfo(client_ip="10.0.0.1"),
        )
        allowed = frozenset({Ctx.User.user_id, Ctx.User.roles, Ctx.Request.client_ip})
        view = ContextView(context, allowed)

        # Act — запрашиваем каждое разрешённое поле
        user_id = view.get(Ctx.User.user_id)
        roles = view.get(Ctx.User.roles)
        ip = view.get(Ctx.Request.client_ip)

        # Assert — все значения корректны
        assert user_id == "u1"
        assert roles == (ManagerRole,)
        assert ip == "10.0.0.1"


# ═════════════════════════════════════════════════════════════════════════════
# Запрещённый доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestDeniedAccess:
    """Доступ к незапрошенным ключам выбрасывает ContextAccessError."""

    def test_access_denied_for_unregistered_key(self) -> None:
        """
        Обращение к незарегистрированному ключу → ContextAccessError.

        ContextView разрешает только user.user_id, но запрашивается
        user.roles — ContextAccessError с указанием ключа.
        """
        # Arrange — ContextView разрешает только user.user_id
        context = Context(user=UserInfo(user_id="u1", roles=(AdminRole,)))
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — доступ к user.roles запрещён
        with pytest.raises(ContextAccessError) as exc_info:
            view.get(Ctx.User.roles)

        # Assert — информативное сообщение с указанием ключа
        assert "user.roles" in str(exc_info.value)

    def test_access_denied_for_different_component(self) -> None:
        """
        Запрос ключа из другого компонента → ContextAccessError.

        Разрешён только user.user_id, запрашивается request.trace_id.
        """
        # Arrange — разрешён только user.user_id, но запрашиваем request.trace_id
        context = Context(
            user=UserInfo(user_id="u1"),
            request=RequestInfo(trace_id="t1"),
        )
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — доступ к полю из другого компонента запрещён
        with pytest.raises(ContextAccessError):
            view.get(Ctx.Request.trace_id)

    def test_error_contains_key_and_allowed_keys(self) -> None:
        """
        ContextAccessError содержит запрошенный ключ и множество разрешённых.
        """
        # Arrange — ContextView с двумя разрешёнными ключами
        context = Context()
        allowed = frozenset({Ctx.User.user_id, Ctx.Request.trace_id})
        view = ContextView(context, allowed)

        # Act — запрашиваем незарегистрированный ключ
        with pytest.raises(ContextAccessError) as exc_info:
            view.get(Ctx.Runtime.hostname)

        # Assert — ошибка содержит запрошенный ключ и список разрешённых
        error = exc_info.value
        assert error.key == "runtime.hostname"
        assert error.allowed_keys == allowed

    def test_empty_allowed_keys_denies_everything(self) -> None:
        """
        ContextView с пустым множеством разрешённых ключей — всё запрещено.
        """
        # Arrange — ContextView с пустым множеством разрешённых ключей
        context = Context(user=UserInfo(user_id="u1"))
        view = ContextView(context, frozenset())

        # Act / Assert — любой ключ запрещён
        with pytest.raises(ContextAccessError):
            view.get(Ctx.User.user_id)


# ═════════════════════════════════════════════════════════════════════════════
# Разрешённый ключ, но поле не существует — возвращает None
# ═════════════════════════════════════════════════════════════════════════════


class TestNonexistentButAllowedKey:
    """Разрешённый ключ, но поле не существует в контексте — возвращает None."""

    def test_allowed_but_none_value(self) -> None:
        """
        Разрешённый ключ user.user_id, значение None (по умолчанию).

        Context() создаёт UserInfo с user_id=None. Ключ разрешён,
        context.resolve("user.user_id") возвращает None.
        """
        # Arrange — контекст с user_id=None (по умолчанию), ключ разрешён
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act — поле существует, но значение None
        result = view.get(Ctx.User.user_id)

        # Assert — Context.resolve возвращает None для незаполненного поля
        assert result is None

    def test_custom_path_not_in_context(self) -> None:
        """
        Разрешённый кастомный путь, но поле не существует в контексте.

        UserInfo не имеет поля billing_plan (и не имеет extra).
        context.resolve("user.billing_plan") возвращает None для
        несуществующего пути.
        """
        # Arrange — кастомный путь разрешён, но данных нет
        context = Context(user=UserInfo())
        view = ContextView(context, frozenset({"user.billing_plan"}))

        # Act — поле не существует в контексте
        result = view.get("user.billing_plan")

        # Assert — resolve возвращает None для отсутствующего пути
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Кастомные поля через наследников Info-классов
# ═════════════════════════════════════════════════════════════════════════════


class TestCustomExtraFields:
    """
    Доступ к кастомным полям через наследников Info-классов.

    UserInfo, RequestInfo, RuntimeInfo не имеют полей extra и tags
    (extra="forbid"). Расширение — только через наследование с явно
    объявленными полями. ContextView.get() делегирует в
    context.resolve(), который обходит цепочку BaseSchema-объектов
    через __getitem__.
    """

    def test_user_extended_field(self) -> None:
        """
        ContextView предоставляет доступ к полю наследника UserInfo.

        _BillingUserInfo наследует UserInfo и добавляет поле billing_plan.
        context.resolve("user.billing_plan") обходит цепочку:
        Context → _BillingUserInfo → billing_plan.
        """
        # Arrange — наследник UserInfo с полем billing_plan
        context = Context(user=_BillingUserInfo(billing_plan="premium"))
        view = ContextView(context, frozenset({"user.billing_plan"}))

        # Act — запрашиваем кастомное поле через dot-path
        result = view.get("user.billing_plan")

        # Assert — значение из поля наследника
        assert result == "premium"

    def test_request_extended_field(self) -> None:
        """
        ContextView предоставляет доступ к полю наследника RequestInfo.

        _TaggedRequestInfo наследует RequestInfo и добавляет поле ab_variant.
        context.resolve("request.ab_variant") обходит цепочку:
        Context → _TaggedRequestInfo → ab_variant.
        """
        # Arrange — наследник RequestInfo с полем ab_variant
        context = Context(request=_TaggedRequestInfo(ab_variant="control"))
        view = ContextView(context, frozenset({"request.ab_variant"}))

        # Act
        result = view.get("request.ab_variant")

        # Assert
        assert result == "control"


# ═════════════════════════════════════════════════════════════════════════════
# Frozen-семантика
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """ContextView полностью неизменяем — запись и удаление запрещены."""

    def test_setattr_raises(self) -> None:
        """Запись нового атрибута → AttributeError с пометкой frozen."""
        # Arrange — создаём ContextView
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — запись атрибута запрещена
        with pytest.raises(AttributeError, match="frozen"):
            view.x = 42  # type: ignore[attr-defined]

    def test_delattr_raises(self) -> None:
        """Удаление атрибута → AttributeError с пометкой frozen."""
        # Arrange — создаём ContextView
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — удаление атрибута запрещено
        with pytest.raises(AttributeError, match="frozen"):
            del view._context  # type: ignore[attr-defined]

    def test_overwrite_allowed_keys_raises(self) -> None:
        """Перезапись _allowed_keys → AttributeError с пометкой frozen."""
        # Arrange — создаём ContextView
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — перезапись _allowed_keys запрещена
        with pytest.raises(AttributeError, match="frozen"):
            view._allowed_keys = frozenset()  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Интроспекция
# ═════════════════════════════════════════════════════════════════════════════


class TestAllowedKeysProperty:
    """Свойство allowed_keys доступно для интроспекции."""

    def test_returns_frozenset(self) -> None:
        """allowed_keys возвращает тот же frozenset, что передан при создании."""
        # Arrange — ContextView с двумя ключами
        allowed = frozenset({Ctx.User.user_id, Ctx.Request.trace_id})
        context = Context()
        view = ContextView(context, allowed)

        # Act
        result = view.allowed_keys

        # Assert — возвращает тот же frozenset
        assert result == allowed
        assert isinstance(result, frozenset)

    def test_empty_allowed_keys(self) -> None:
        """Пустое множество разрешённых ключей — валидно."""
        # Arrange — ContextView без разрешённых ключей
        context = Context()
        view = ContextView(context, frozenset())

        # Act / Assert
        assert view.allowed_keys == frozenset()


# ═════════════════════════════════════════════════════════════════════════════
# Строковое представление
# ═════════════════════════════════════════════════════════════════════════════


class TestRepr:
    """Строковое представление для отладки."""

    def test_repr_contains_keys(self) -> None:
        """repr содержит имя класса и имена разрешённых ключей."""
        # Arrange — ContextView с ключами
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id, Ctx.User.roles}))

        # Act
        result = repr(view)

        # Assert — repr содержит имена ключей
        assert "ContextView" in result
        assert "user.user_id" in result
        assert "user.roles" in result

    def test_repr_empty_keys(self) -> None:
        """repr для пустого множества ключей."""
        # Arrange — ContextView без ключей
        context = Context()
        view = ContextView(context, frozenset())

        # Act
        result = repr(view)

        # Assert — repr для пустого множества
        assert "ContextView" in result
