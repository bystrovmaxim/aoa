# tests2/core/test_base_action.py
"""
Тесты BaseAction — абстрактный базовый класс для всех действий.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseAction[P, R] — абстрактный базовый класс, от которого наследуются
все действия в системе ActionMachine. Параметризован типами Params (P)
и Result (R). Наследует шесть маркерных миксинов (гейт-хостов), каждый
из которых разрешает применение соответствующего декоратора:

- ActionMetaGateHost — разрешает и ТРЕБУЕТ @meta.
- RoleGateHost — разрешает @check_roles.
- DependencyGateHost[object] — разрешает @depends (bound=object, любой класс).
- CheckerGateHost — разрешает чекеры (@result_string, @result_int и др.).
- AspectGateHost — разрешает @regular_aspect и @summary_aspect.
- ConnectionGateHost — разрешает @connection.

BaseAction предоставляет единственный метод get_full_class_name(),
который формирует полное имя класса (module.ClassName) и кеширует его
на уровне класса (не экземпляра). Кеш разделяется всеми экземплярами
одного класса.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

get_full_class_name():
    - Возвращает строку вида "module.path.ClassName".
    - Результат кешируется на уровне класса (_full_class_name).
    - Повторный вызов возвращает тот же объект строки (is-проверка).
    - Разные экземпляры одного класса разделяют кеш.

Наследование гейт-хостов:
    - BaseAction наследует ActionMetaGateHost.
    - BaseAction наследует RoleGateHost.
    - BaseAction наследует DependencyGateHost.
    - BaseAction наследует CheckerGateHost.
    - BaseAction наследует AspectGateHost.
    - BaseAction наследует ConnectionGateHost.

Действия из доменной модели:
    - PingAction.get_full_class_name() содержит модуль и имя класса.
    - FullAction.get_full_class_name() содержит модуль и имя класса.
    - Кеш работает для доменных действий.
"""

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.base_action import BaseAction
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost
from tests2.domain import FullAction, PingAction, SimpleAction

# ═════════════════════════════════════════════════════════════════════════════
# get_full_class_name()
# ═════════════════════════════════════════════════════════════════════════════


class TestGetFullClassName:
    """Формирование и кеширование полного имени класса действия."""

    def setup_method(self) -> None:
        """
        Сброс кеша перед каждым тестом.

        _full_class_name — class-level атрибут. Если предыдущий тест
        его заполнил, следующий тест увидит закешированное значение.
        Сбрасываем для изоляции тестов.
        """
        PingAction._full_class_name = None
        FullAction._full_class_name = None
        SimpleAction._full_class_name = None

    def test_returns_module_and_class_name(self) -> None:
        """
        get_full_class_name() возвращает "module.ClassName".

        Формат: f"{cls.__module__}.{cls.__qualname__}". Используется
        для сопоставления с регулярными выражениями в плагинах
        (action_filter в @on) и для идентификации в логах.
        """
        # Arrange — экземпляр PingAction из доменной модели
        action = PingAction()

        # Act — формирование полного имени
        full_name = action.get_full_class_name()

        # Assert — содержит модуль и имя класса, разделённые точкой.
        # Модуль: tests2.domain.ping_action, класс: PingAction
        assert "PingAction" in full_name
        assert "tests2.domain.ping_action" in full_name
        assert full_name == "tests2.domain.ping_action.PingAction"

    def test_full_action_class_name(self) -> None:
        """
        get_full_class_name() для FullAction включает его модуль.
        """
        # Arrange — экземпляр FullAction
        action = FullAction()

        # Act — формирование полного имени
        full_name = action.get_full_class_name()

        # Assert — модуль full_action, класс FullAction
        assert full_name == "tests2.domain.full_action.FullAction"

    def test_result_is_cached_on_class_level(self) -> None:
        """
        Результат кешируется в cls._full_class_name (class-level).

        После первого вызова get_full_class_name() результат записывается
        в PingAction._full_class_name через self.__class__._full_class_name.
        Это class-attribute, а не instance-attribute — все экземпляры
        одного класса разделяют один кеш.
        """
        # Arrange — до вызова кеш пуст (сброшен в setup_method)
        assert PingAction._full_class_name is None
        action = PingAction()

        # Act — первый вызов заполняет кеш
        full_name = action.get_full_class_name()

        # Assert — кеш заполнен на уровне класса
        assert PingAction._full_class_name is not None
        assert PingAction._full_class_name == full_name

    def test_repeated_call_returns_same_object(self) -> None:
        """
        Повторный вызов возвращает тот же объект строки (is-проверка).

        Первый вызов формирует строку и записывает в кеш. Второй вызов
        обнаруживает, что cls._full_class_name is not None, и возвращает
        закешированное значение без повторного формирования.
        """
        # Arrange — экземпляр PingAction
        action = PingAction()

        # Act — два вызова подряд
        first = action.get_full_class_name()
        second = action.get_full_class_name()

        # Assert — один и тот же объект в памяти (is, а не ==)
        assert first is second

    def test_different_instances_share_cache(self) -> None:
        """
        Два экземпляра одного класса используют общий кеш.

        _full_class_name — class-level атрибут. Первый экземпляр
        заполняет кеш, второй экземпляр читает из него.
        """
        # Arrange — два разных экземпляра PingAction
        action1 = PingAction()
        action2 = PingAction()

        # Act — первый экземпляр заполняет кеш
        name1 = action1.get_full_class_name()

        # Act — второй экземпляр читает из кеша
        name2 = action2.get_full_class_name()

        # Assert — одинаковый результат, один объект строки
        assert name1 == name2
        assert name1 is name2

    def test_different_classes_different_names(self) -> None:
        """
        Разные классы действий имеют разные полные имена.

        Каждый класс имеет свой _full_class_name. PingAction и FullAction
        находятся в разных модулях и имеют разные имена.
        """
        # Arrange — экземпляры разных классов
        ping = PingAction()
        full = FullAction()

        # Act — формирование имён
        ping_name = ping.get_full_class_name()
        full_name = full.get_full_class_name()

        # Assert — разные строки
        assert ping_name != full_name
        assert "PingAction" in ping_name
        assert "FullAction" in full_name


# ═════════════════════════════════════════════════════════════════════════════
# Наследование гейт-хостов
# ═════════════════════════════════════════════════════════════════════════════


class TestGateHostInheritance:
    """
    BaseAction наследует шесть маркерных миксинов (гейт-хостов).

    Каждый гейт-хост — маркерный класс без логики. Его наличие в MRO
    разрешает применение соответствующего декоратора. Декораторы проверяют
    issubclass(cls, GateHost) при применении и бросают TypeError если
    гейт-хост отсутствует.
    """

    def test_inherits_action_meta_gate_host(self) -> None:
        """
        BaseAction наследует ActionMetaGateHost.

        ActionMetaGateHost обозначает, что @meta обязателен для классов
        с аспектами. MetadataBuilder проверяет: если класс наследует
        ActionMetaGateHost и содержит аспекты — @meta обязателен.
        """
        # Arrange & Act — проверка MRO через issubclass
        # Assert — BaseAction входит в иерархию ActionMetaGateHost
        assert issubclass(BaseAction, ActionMetaGateHost)

        # Assert — конкретные действия тоже наследуют
        assert issubclass(PingAction, ActionMetaGateHost)
        assert issubclass(FullAction, ActionMetaGateHost)

    def test_inherits_role_gate_host(self) -> None:
        """
        BaseAction наследует RoleGateHost.

        RoleGateHost разрешает применение @check_roles. Декоратор
        @check_roles при применении проверяет issubclass(cls, RoleGateHost)
        и бросает TypeError если не найден.
        """
        # Arrange & Act & Assert
        assert issubclass(BaseAction, RoleGateHost)
        assert issubclass(PingAction, RoleGateHost)

    def test_inherits_dependency_gate_host(self) -> None:
        """
        BaseAction наследует DependencyGateHost[object].

        DependencyGateHost[T] — generic-миксин. T определяет bound:
        какие классы допустимы как зависимости. Для BaseAction T=object,
        что означает любой класс допустим в @depends.
        """
        # Arrange & Act & Assert
        assert issubclass(BaseAction, DependencyGateHost)
        assert issubclass(FullAction, DependencyGateHost)

    def test_inherits_checker_gate_host(self) -> None:
        """
        BaseAction наследует CheckerGateHost.

        CheckerGateHost разрешает декораторы чекеров (@result_string,
        @result_int и др.) на методах-аспектах.
        """
        # Arrange & Act & Assert
        assert issubclass(BaseAction, CheckerGateHost)

    def test_inherits_aspect_gate_host(self) -> None:
        """
        BaseAction наследует AspectGateHost.

        AspectGateHost разрешает @regular_aspect и @summary_aspect
        на методах класса.
        """
        # Arrange & Act & Assert
        assert issubclass(BaseAction, AspectGateHost)

    def test_inherits_connection_gate_host(self) -> None:
        """
        BaseAction наследует ConnectionGateHost.

        ConnectionGateHost разрешает @connection(ResourceManager, key="db")
        для объявления подключений к внешним ресурсам.
        """
        # Arrange & Act & Assert
        assert issubclass(BaseAction, ConnectionGateHost)

    def test_depends_bound_is_object(self) -> None:
        """
        DependencyGateHost[object] — bound=object, любой класс допустим.

        BaseAction объявлен как DependencyGateHost[object], что означает
        @depends может принимать любой класс как зависимость: сервисы,
        ресурсные менеджеры, утилиты.
        """
        # Arrange — проверяем bound через class-method get_depends_bound()
        # Act
        bound = PingAction.get_depends_bound()

        # Assert — bound=object, допускается любой класс
        assert bound is object
