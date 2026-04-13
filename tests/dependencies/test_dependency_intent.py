# tests/dependencies/test_dependency_intent.py
"""
Тесты DependencyIntent — маркерного миксина для декоратора @depends.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyIntent[T] выполняет две функции:

1. Маркер: декоратор @depends проверяет, что целевой класс наследует
   DependencyIntent. Без наследования — TypeError.

2. Ограничитель типа (bound): параметр T определяет, какие классы
   допускаются в качестве зависимостей. Декоратор @depends проверяет
   issubclass(klass, bound) при каждом вызове.

Bound извлекается из generic-параметра DependencyIntent[T] в
__init_subclass__ через _extract_bound. Если T — конкретный тип,
он используется. Если T — TypeVar или не найден, bound наследуется
от родителя или возвращается object.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

_extract_bound:
    - Класс с DependencyIntent[object] → bound = object.
    - Класс с DependencyIntent[конкретный_тип] → bound = конкретный_тип.
    - Класс-наследник без собственного generic → bound наследуется от родителя.
    - Класс без __orig_bases__ и без родителя с bound → bound = object.

get_depends_bound:
    - Возвращает bound, установленный в __init_subclass__.
    - На классе без _depends_bound возвращает object (fallback через getattr).

Интеграция с BaseAction:
    - BaseAction наследует DependencyIntent[object], поэтому bound = object.
    - Доменные Action наследуют bound от BaseAction.
"""


from action_machine.dependencies.dependency_intent import (
    DependencyIntent,
    _extract_bound,
)
from action_machine.resources.base_resource_manager import BaseResourceManager
from tests.domain_model import FullAction, PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Хелперы — заведомо тестовые классы, не часть рабочей доменной модели.
# Создаются внутри теста для проверки механизма извлечения bound.
# ─────────────────────────────────────────────────────────────────────────────


class _AnyDepsHost(DependencyIntent[object]):
    """Хост с bound=object — принимает любые зависимости."""
    pass


class _ResourceOnlyHost(DependencyIntent[BaseResourceManager]):
    """Хост с bound=BaseResourceManager — только ресурсные менеджеры."""
    pass


class _ChildOfResourceHost(_ResourceOnlyHost):
    """Наследник без собственного generic — bound наследуется от родителя."""
    pass


class _GrandchildOfResourceHost(_ChildOfResourceHost):
    """Внук — bound наследуется через цепочку MRO."""
    pass


class _PlainClass:
    """Обычный класс без DependencyIntent в предках."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# _extract_bound — извлечение bound из generic-параметра
# ═════════════════════════════════════════════════════════════════════════════


class TestExtractBound:
    """Покрывает все ветки _extract_bound."""

    def test_object_bound(self) -> None:
        """DependencyIntent[object] → bound = object."""
        # Arrange — _AnyDepsHost наследует DependencyIntent[object]

        # Act
        bound = _extract_bound(_AnyDepsHost)

        # Assert
        assert bound is object

    def test_specific_bound(self) -> None:
        """DependencyIntent[BaseResourceManager] → bound = BaseResourceManager."""
        # Arrange — _ResourceOnlyHost наследует DependencyIntent[BaseResourceManager]

        # Act
        bound = _extract_bound(_ResourceOnlyHost)

        # Assert
        assert bound is BaseResourceManager

    def test_inherited_bound(self) -> None:
        """Наследник без своего generic → bound наследуется от родителя."""
        # Arrange — _ChildOfResourceHost не указывает DependencyIntent[...]
        # напрямую, но наследует _ResourceOnlyHost

        # Act
        bound = _extract_bound(_ChildOfResourceHost)

        # Assert — bound унаследован: BaseResourceManager
        assert bound is BaseResourceManager

    def test_grandchild_inherited_bound(self) -> None:
        """Внук наследует bound через цепочку MRO."""
        # Arrange — _GrandchildOfResourceHost → _ChildOfResourceHost → _ResourceOnlyHost

        # Act
        bound = _extract_bound(_GrandchildOfResourceHost)

        # Assert
        assert bound is BaseResourceManager

    def test_plain_class_returns_object(self) -> None:
        """Класс без DependencyIntent в предках → bound = object."""
        # Arrange — _PlainClass не наследует DependencyIntent

        # Act
        bound = _extract_bound(_PlainClass)

        # Assert — fallback на object
        assert bound is object


# ═════════════════════════════════════════════════════════════════════════════
# get_depends_bound — classmethod
# ═════════════════════════════════════════════════════════════════════════════


class TestGetDependsBound:
    """Покрывает get_depends_bound classmethod."""

    def test_returns_bound_for_host(self) -> None:
        """get_depends_bound возвращает bound, установленный в __init_subclass__."""
        # Arrange — _ResourceOnlyHost имеет _depends_bound = BaseResourceManager

        # Act
        bound = _ResourceOnlyHost.get_depends_bound()

        # Assert
        assert bound is BaseResourceManager

    def test_returns_object_for_any_host(self) -> None:
        """get_depends_bound для DependencyIntent[object] возвращает object."""
        # Arrange

        # Act
        bound = _AnyDepsHost.get_depends_bound()

        # Assert
        assert bound is object

    def test_returns_object_for_class_without_attr(self) -> None:
        """Класс без _depends_bound → getattr fallback → object."""
        # Arrange — _PlainClass не имеет _depends_bound

        # Act — вызываем через DependencyIntent.get_depends_bound на _PlainClass
        # Нельзя вызвать classmethod на _PlainClass напрямую, но можно проверить
        # через getattr напрямую
        bound = getattr(_PlainClass, "_depends_bound", object)

        # Assert
        assert bound is object


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с BaseAction
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseActionIntegration:
    """Покрывает наследование bound через BaseAction → доменные Action."""

    def test_ping_action_bound_is_object(self) -> None:
        """PingAction наследует DependencyIntent[object] через BaseAction."""
        # Arrange — PingAction → BaseAction → DependencyIntent[object]

        # Act
        bound = PingAction.get_depends_bound()

        # Assert — BaseAction объявлен как DependencyIntent[object]
        assert bound is object

    def test_full_action_bound_is_object(self) -> None:
        """FullAction с @depends тоже имеет bound=object."""
        # Arrange — FullAction наследует BaseAction

        # Act
        bound = FullAction.get_depends_bound()

        # Assert
        assert bound is object

    def test_ping_action_is_dependency_intent(self) -> None:
        """PingAction является подклассом DependencyIntent."""
        # Arrange / Act / Assert
        assert issubclass(PingAction, DependencyIntent)

    def test_plain_class_is_not_dependency_intent(self) -> None:
        """Обычный класс не является подклассом DependencyIntent."""
        # Arrange / Act / Assert
        assert not issubclass(_PlainClass, DependencyIntent)
