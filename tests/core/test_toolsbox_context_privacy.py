# tests/core/test_toolsbox_context_privacy.py
"""
Тесты приватности контекста в ToolsBox.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет ключевой инвариант: ToolsBox НЕ предоставляет публичного
доступа к контексту выполнения (Context) [1]. Аспекты получают данные
контекста исключительно через ContextView, создаваемый машиной
при наличии @context_requires [1].

Также проверяет frozen-семантику ToolsBox: запись и удаление
атрибутов запрещены после создания.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.scoped_logger import ScopedLogger


# ═════════════════════════════════════════════════════════════════════════════
# Фикстура создания ToolsBox
# ═════════════════════════════════════════════════════════════════════════════

def _make_toolsbox(context: Context | None = None) -> ToolsBox:
    """
    Создаёт ToolsBox с минимальными заглушками для тестирования.

    Все зависимости (run_child, factory, log) замокированы.
    Контекст передаётся как аргумент — именно он должен быть
    недоступен через публичный API.
    """
    ctx = context or Context(user=UserInfo(user_id="test_user", roles=["tester"]))
    return ToolsBox(
        run_child=AsyncMock(),
        factory=DependencyFactory(()),
        resources=None,
        context=ctx,
        log=MagicMock(spec=ScopedLogger),
        nested_level=0,
        rollup=False,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Приватность контекста
# ═════════════════════════════════════════════════════════════════════════════

class TestToolsBoxContextPrivacy:
    """Тесты отсутствия публичного доступа к Context через ToolsBox."""

    def test_no_context_attribute(self) -> None:
        """Атрибут box.context не существует — AttributeError."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert — прямой доступ к context запрещён
        with pytest.raises(AttributeError):
            _ = box.context  # type: ignore[attr-defined]

    def test_no_context_in_dir(self) -> None:
        """dir(box) не содержит 'context' без подчёркиваний."""
        # Arrange
        box = _make_toolsbox()

        # Act
        public_attrs = [name for name in dir(box) if not name.startswith("_")]

        # Assert — слово 'context' отсутствует в публичных атрибутах
        assert "context" not in public_attrs

    def test_no_get_context_method(self) -> None:
        """Метод get_context() не существует."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert not hasattr(box, "get_context")

    def test_no_ctx_attribute(self) -> None:
        """Атрибут box.ctx не существует."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert not hasattr(box, "ctx")

    def test_getitem_context_raises(self) -> None:
        """Попытка box["context"] не возвращает Context."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert — ToolsBox не наследует BaseSchema и не имеет
        # __getitem__, поэтому доступ по ключу невозможен
        with pytest.raises((TypeError, KeyError, AttributeError)):
            _ = box["context"]  # type: ignore[index]

    def test_public_properties_do_not_leak_context(self) -> None:
        """Ни одно публичное свойство не возвращает объект типа Context."""
        # Arrange
        ctx = Context(user=UserInfo(user_id="secret_user", roles=["admin"]))
        box = _make_toolsbox(context=ctx)

        # Act — собираем значения всех публичных свойств
        public_names = [name for name in dir(box) if not name.startswith("_")]
        public_values = []
        for name in public_names:
            try:
                val = getattr(box, name)
                if not callable(val):
                    public_values.append(val)
            except Exception:
                pass

        # Assert — ни одно значение не является Context
        for val in public_values:
            assert not isinstance(val, Context), (
                f"Публичное свойство вернуло Context: {val!r}"
            )

    def test_context_stored_via_name_mangling(self) -> None:
        """
        Context хранится через name mangling (_ToolsBox__context).

        Это не публичный API — тест документирует механизм хранения.
        Доступ через mangled-имя является нарушением контракта фреймворка,
        но физически возможен в Python. Тест подтверждает, что context
        действительно передан и хранится внутри.
        """
        # Arrange
        ctx = Context(user=UserInfo(user_id="hidden_user"))
        box = _make_toolsbox(context=ctx)

        # Act — доступ через mangled-имя (нарушение контракта, но работает)
        mangled_ctx = object.__getattribute__(box, "_ToolsBox__context")

        # Assert — context действительно хранится внутри
        assert mangled_ctx is ctx
        assert mangled_ctx.user.user_id == "hidden_user"


# ═════════════════════════════════════════════════════════════════════════════
# Frozen-семантика ToolsBox
# ═════════════════════════════════════════════════════════════════════════════

class TestToolsBoxFrozen:
    """Тесты неизменяемости ToolsBox после создания."""

    def test_setattr_raises(self) -> None:
        """Запись атрибутов запрещена — AttributeError."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        with pytest.raises(AttributeError, match="frozen"):
            box.custom_attr = "value"  # type: ignore[misc]

    def test_delattr_raises(self) -> None:
        """Удаление атрибутов запрещено — AttributeError."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert — попытка удалить публичное свойство
        with pytest.raises(AttributeError, match="frozen"):
            del box.nested_level  # type: ignore[misc]

    def test_cannot_overwrite_factory(self) -> None:
        """Нельзя подменить factory после создания."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        with pytest.raises(AttributeError, match="frozen"):
            box.factory = DependencyFactory(())  # type: ignore[misc]

    def test_cannot_add_context_property(self) -> None:
        """Нельзя добавить атрибут context на экземпляре."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert — __slots__ + __setattr__ запрещают
        with pytest.raises(AttributeError):
            box.context = Context()  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Публичные свойства работают корректно
# ═════════════════════════════════════════════════════════════════════════════

class TestToolsBoxPublicAPI:
    """Тесты корректности публичных свойств ToolsBox."""

    def test_nested_level(self) -> None:
        """Свойство nested_level возвращает уровень вложенности."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert box.nested_level == 0

    def test_rollup(self) -> None:
        """Свойство rollup возвращает флаг автоотката."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert box.rollup is False

    def test_factory(self) -> None:
        """Свойство factory возвращает DependencyFactory."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert isinstance(box.factory, DependencyFactory)

    def test_resources_none(self) -> None:
        """Свойство resources возвращает None если не переданы."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert box.resources is None

    def test_run_child(self) -> None:
        """Свойство run_child возвращает callable (замыкание)."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert callable(box.run_child)