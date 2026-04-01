# tests/metadata/test_builder_inheritance.py
"""
Тесты MetadataBuilder — наследование метаданных между классами.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, как MetadataBuilder обрабатывает наследование: какие метаданные
наследуются от родителя, какие нет, и как дочерний класс может их
переопределить.

Правила наследования ActionMachine:
    - role: наследуется (если дочерний не переопределяет).
    - dependencies: наследуются (дочерний добавляет к родительским).
    - connections: наследуются (дочерний добавляет к родительским).
    - aspects: НЕ наследуются (дочерний определяет свои или не имеет).
    - subscriptions: НЕ наследуются.
    - sensitive_fields: наследуются.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestInheritRole
    - Дочерний класс без @check_roles наследует role от родителя.

TestInheritDependencies
    - Дочерний класс наследует зависимости родителя.
    - Дочерний класс добавляет свои зависимости к родительским.

TestAspectsNotInherited
    - Дочерний класс без аспектов не наследует аспекты родителя.
    - Дочерний класс с собственными аспектами игнорирует родительские.
    - Дочерний класс, переопределяющий аспекты, должен определять все заново.

TestInheritSensitiveFields
    - Sensitive-поля наследуются от родителя.

TestSubscriptionsNotInherited
    - Подписки (subscriptions) НЕ наследуются.
"""


from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta
from action_machine.dependencies.depends import depends
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.metadata.builder import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class _Params(BaseParams):
    """Параметры для тестовых действий."""
    pass


class _Result(BaseResult):
    """Результат для тестовых действий."""
    pass


class _ServiceA:
    """Тестовая зависимость A."""
    pass


class _ServiceB:
    """Тестовая зависимость B."""
    pass


class _ServiceC:
    """Тестовая зависимость C (дочерняя)."""
    pass


# ─── Родитель с ролью и зависимостями ────────────────────────────────────


@meta("Родительское действие")
@check_roles("admin")
@depends(_ServiceA)
class _ParentAction(BaseAction["_Params", "_Result"]):
    """Родительское действие с ролью, зависимостью и аспектами."""

    @regular_aspect("Родительский шаг")
    async def parent_step(self, params, state, box, connections):
        return {"data": "parent"}

    @summary_aspect("Родительский итог")
    async def parent_summary(self, params, state, box, connections):
        return {"result": "parent_done"}


# ─── Дочерний без переопределений ────────────────────────────────────────


class _ChildNoOverrides(_ParentAction):
    """Дочерний класс без переопределений — наследует role и dependencies."""
    pass


# ─── Дочерний с дополнительной зависимостью ──────────────────────────────


@depends(_ServiceC)
class _ChildWithExtraDep(_ParentAction):
    """Дочерний класс с дополнительной зависимостью."""
    pass


# ─── Дочерний со своими аспектами ────────────────────────────────────────


@meta("Дочернее действие с аспектами")
class _ChildWithOwnAspects(_ParentAction):
    """Дочерний класс с собственными аспектами — игнорирует родительские."""

    @regular_aspect("Дочерний шаг")
    async def child_step(self, params, state, box, connections):
        return {"data": "child"}

    @summary_aspect("Дочерний итог")
    async def child_summary(self, params, state, box, connections):
        return {"result": "child_done"}


# ─── Родитель с sensitive-полем ──────────────────────────────────────────


@meta("Родитель с sensitive")
@check_roles(ROLE_NONE)
class _ParentWithSensitive(BaseAction["_Params", "_Result"]):
    """Родительское действие с sensitive-полем."""

    def __init__(self):
        self._phone = "+7-999-123-4567"

    @sensitive()
    @property
    def phone(self):
        return self._phone

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


class _ChildOfSensitive(_ParentWithSensitive):
    """Дочерний класс — наследует sensitive-поля."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Наследование роли
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritRole:
    """Проверяет наследование роли от родителя."""

    def test_child_inherits_parent_role(self):
        """Дочерний класс без @check_roles наследует role."""
        # Arrange & Act
        result = MetadataBuilder().build(_ChildNoOverrides)

        # Assert
        assert result.has_role() is True
        assert result.role.spec == "admin"

    def test_parent_role_unchanged(self):
        """Роль родителя не изменяется из-за дочернего класса."""
        # Arrange & Act
        parent_meta = MetadataBuilder().build(_ParentAction)

        # Assert
        assert parent_meta.role.spec == "admin"


# ═════════════════════════════════════════════════════════════════════════════
# Наследование зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritDependencies:
    """Проверяет наследование и расширение зависимостей."""

    def test_child_inherits_parent_dependencies(self):
        """Дочерний класс наследует зависимости родителя."""
        # Arrange & Act
        result = MetadataBuilder().build(_ChildNoOverrides)

        # Assert
        assert result.has_dependencies() is True
        classes = result.get_dependency_classes()
        assert _ServiceA in classes

    def test_child_adds_own_dependencies(self):
        """Дочерний класс добавляет свои зависимости к родительским."""
        # Arrange & Act
        result = MetadataBuilder().build(_ChildWithExtraDep)

        # Assert
        classes = result.get_dependency_classes()
        assert _ServiceA in classes
        assert _ServiceC in classes

    def test_parent_dependencies_not_mutated(self):
        """Зависимости родителя не изменяются при добавлении в дочернем."""
        # Arrange & Act
        parent_meta = MetadataBuilder().build(_ParentAction)
        child_meta = MetadataBuilder().build(_ChildWithExtraDep)

        # Assert
        assert len(parent_meta.dependencies) < len(child_meta.dependencies)
        assert _ServiceC not in parent_meta.get_dependency_classes()


# ═════════════════════════════════════════════════════════════════════════════
# Аспекты НЕ наследуются
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectsNotInherited:
    """Проверяет, что аспекты не наследуются от родителя."""

    def test_child_without_aspects_has_none(self):
        """Дочерний класс без собственных аспектов не наследует родительские."""
        # Arrange & Act
        result = MetadataBuilder().build(_ChildNoOverrides)

        # Assert
        assert result.has_aspects() is False

    def test_child_with_own_aspects_ignores_parent(self):
        """Дочерний класс с собственными аспектами игнорирует родительские."""
        # Arrange & Act
        result = MetadataBuilder().build(_ChildWithOwnAspects)

        # Assert
        assert result.has_aspects() is True
        method_names = [a.method_name for a in result.aspects]
        assert "child_step" in method_names
        assert "child_summary" in method_names
        assert "parent_step" not in method_names
        assert "parent_summary" not in method_names

    def test_parent_aspects_unchanged(self):
        """Аспекты родителя не изменяются дочерним классом."""
        # Arrange & Act
        parent_meta = MetadataBuilder().build(_ParentAction)

        # Assert
        method_names = [a.method_name for a in parent_meta.aspects]
        assert "parent_step" in method_names
        assert "parent_summary" in method_names


# ═════════════════════════════════════════════════════════════════════════════
# Наследование sensitive-полей
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritSensitiveFields:
    """Проверяет наследование sensitive-полей."""

    def test_parent_has_sensitive_field(self):
        """Родитель имеет sensitive-поле."""
        # Arrange & Act
        result = MetadataBuilder().build(_ParentWithSensitive)

        # Assert
        assert result.has_sensitive_fields() is True
        assert len(result.sensitive_fields) >= 1

    def test_child_inherits_sensitive_fields(self):
        """Дочерний класс наследует sensitive-поля родителя."""
        # Arrange & Act
        result = MetadataBuilder().build(_ChildOfSensitive)

        # Assert
        assert result.has_sensitive_fields() is True
        property_names = [sf.property_name for sf in result.sensitive_fields]
        assert "phone" in property_names
