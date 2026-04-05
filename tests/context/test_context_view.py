# tests/context/test_context_view.py
"""
Тесты ContextView — frozen-объект с контролируемым доступом к полям контекста.
"""

import pytest

from action_machine.context.context import Context
from action_machine.context.context_view import ContextView
from action_machine.context.ctx_constants import Ctx
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo
from action_machine.core.exceptions import ContextAccessError


class TestAllowedAccess:
    """Доступ к разрешённым ключам возвращает корректные значения."""

    def test_get_user_id(self) -> None:
        # Arrange — контекст с user_id, ContextView разрешает user.user_id
        context = Context(user=UserInfo(user_id="agent_007"))
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act — запрашиваем разрешённое поле
        result = view.get(Ctx.User.user_id)

        # Assert — значение из контекста
        assert result == "agent_007"

    def test_get_user_roles(self) -> None:
        # Arrange — контекст с ролями, ContextView разрешает user.roles
        context = Context(user=UserInfo(roles=["admin", "user"]))
        view = ContextView(context, frozenset({Ctx.User.roles}))

        # Act — запрашиваем разрешённое поле
        result = view.get(Ctx.User.roles)

        # Assert — список ролей из контекста
        assert result == ["admin", "user"]

    def test_get_request_trace_id(self) -> None:
        # Arrange — контекст с trace_id в запросе
        context = Context(request=RequestInfo(trace_id="trace-abc-123"))
        view = ContextView(context, frozenset({Ctx.Request.trace_id}))

        # Act
        result = view.get(Ctx.Request.trace_id)

        # Assert
        assert result == "trace-abc-123"

    def test_get_runtime_hostname(self) -> None:
        # Arrange — контекст с hostname в runtime
        context = Context(runtime=RuntimeInfo(hostname="prod-server-01"))
        view = ContextView(context, frozenset({Ctx.Runtime.hostname}))

        # Act
        result = view.get(Ctx.Runtime.hostname)

        # Assert
        assert result == "prod-server-01"

    def test_get_multiple_allowed_keys(self) -> None:
        # Arrange — ContextView разрешает несколько ключей
        context = Context(
            user=UserInfo(user_id="u1", roles=["manager"]),
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
        assert roles == ["manager"]
        assert ip == "10.0.0.1"


class TestDeniedAccess:
    """Доступ к незапрошенным ключам выбрасывает ContextAccessError."""

    def test_access_denied_for_unregistered_key(self) -> None:
        # Arrange — ContextView разрешает только user.user_id
        context = Context(user=UserInfo(user_id="u1", roles=["admin"]))
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — доступ к user.roles запрещён
        with pytest.raises(ContextAccessError) as exc_info:
            view.get(Ctx.User.roles)

        # Assert — информативное сообщение с указанием ключа
        assert "user.roles" in str(exc_info.value)

    def test_access_denied_for_different_component(self) -> None:
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
        # Arrange — ContextView с пустым множеством разрешённых ключей
        context = Context(user=UserInfo(user_id="u1"))
        view = ContextView(context, frozenset())

        # Act / Assert — любой ключ запрещён
        with pytest.raises(ContextAccessError):
            view.get(Ctx.User.user_id)


class TestNonexistentButAllowedKey:
    """Разрешённый ключ, но поле не существует в контексте — возвращает None."""

    def test_allowed_but_none_value(self) -> None:
        # Arrange — контекст с user_id=None (по умолчанию), ключ разрешён
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act — поле существует, но значение None
        result = view.get(Ctx.User.user_id)

        # Assert — Context.resolve возвращает None для незаполненного поля
        assert result is None

    def test_custom_path_not_in_context(self) -> None:
        # Arrange — кастомный путь разрешён, но данных нет в extra
        context = Context(user=UserInfo())
        view = ContextView(context, frozenset({"user.extra.billing_plan"}))

        # Act — поле не существует в контексте
        result = view.get("user.extra.billing_plan")

        # Assert — resolve возвращает None для отсутствующего пути
        assert result is None


class TestCustomExtraFields:
    """Доступ к кастомным полям через extra словари."""

    def test_user_extra_field(self) -> None:
        # Arrange — user с дополнительным полем в extra
        context = Context(user=UserInfo(extra={"billing_plan": "premium"}))
        view = ContextView(context, frozenset({"user.extra.billing_plan"}))

        # Act — запрашиваем кастомное поле через dot-path
        result = view.get("user.extra.billing_plan")

        # Assert — значение из extra
        assert result == "premium"

    def test_request_tags_field(self) -> None:
        # Arrange — request с тегом в tags
        context = Context(request=RequestInfo(tags={"ab_variant": "control"}))
        view = ContextView(context, frozenset({"request.tags.ab_variant"}))

        # Act
        result = view.get("request.tags.ab_variant")

        # Assert
        assert result == "control"


class TestFrozen:
    """ContextView полностью неизменяем — запись и удаление запрещены."""

    def test_setattr_raises(self) -> None:
        # Arrange — создаём ContextView
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — запись атрибута запрещена
        with pytest.raises(AttributeError, match="frozen"):
            view.x = 42  # type: ignore[attr-defined]

    def test_delattr_raises(self) -> None:
        # Arrange — создаём ContextView
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — удаление атрибута запрещено
        with pytest.raises(AttributeError, match="frozen"):
            del view._context  # type: ignore[attr-defined]

    def test_overwrite_allowed_keys_raises(self) -> None:
        # Arrange — создаём ContextView
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — перезапись _allowed_keys запрещена
        with pytest.raises(AttributeError, match="frozen"):
            view._allowed_keys = frozenset()  # type: ignore[misc]


class TestAllowedKeysProperty:
    """Свойство allowed_keys доступно для интроспекции."""

    def test_returns_frozenset(self) -> None:
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
        # Arrange — ContextView без разрешённых ключей
        context = Context()
        view = ContextView(context, frozenset())

        # Act / Assert
        assert view.allowed_keys == frozenset()


class TestRepr:
    """Строковое представление для отладки."""

    def test_repr_contains_keys(self) -> None:
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
        # Arrange — ContextView без ключей
        context = Context()
        view = ContextView(context, frozenset())

        # Act
        result = repr(view)

        # Assert — repr для пустого множества
        assert "ContextView" in result
