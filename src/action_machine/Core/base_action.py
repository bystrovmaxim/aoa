# src/action_machine/core/base_action.py
"""
Базовый класс для всех действий ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseAction — абстрактный базовый класс, от которого наследуются все
действия (Action) в системе. Параметризован типами Params и Result,
которые должны соответствовать протоколам ReadableDataProtocol
и WritableDataProtocol.

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЕ ДЕКОРАТОРЫ
═══════════════════════════════════════════════════════════════════════════════

Каждое действие обязано иметь два декоратора:

1. @meta(description="...", domain=...) — описание и доменная принадлежность.
   Контролируется ActionMetaGateHost. MetadataBuilder при сборке проверяет:
   если класс наследует ActionMetaGateHost и содержит аспекты — @meta
   обязателен. Без него — TypeError.

2. @check_roles(...) — ролевые ограничения. Контролируется RoleGateHost.
   ActionProductMachine при выполнении проверяет: если действие не имеет
   @check_roles — TypeError.

═══════════════════════════════════════════════════════════════════════════════
АСПЕКТЫ
═══════════════════════════════════════════════════════════════════════════════

Аспекты действий (регулярные и summary) определяются в наследниках
с помощью декораторов @regular_aspect и @summary_aspect из модуля aspects.
BaseAction не содержит методов аспектов — только общую инфраструктуру.

Аспекты принимают параметр state типа BaseState (вместо dict[str, Any]),
что обеспечивает единообразный интерфейс (resolve, get, write, items)
и контролируемую запись.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТЧИКИ ОШИБОК (@on_error)
═══════════════════════════════════════════════════════════════════════════════

Действия могут объявлять обработчики неперехваченных исключений аспектов
через декоратор @on_error. Контролируется OnErrorGateHost. Когда аспект
бросает исключение, ActionProductMachine ищет подходящий обработчик
по типу исключения (isinstance) и вызывает его. Обработчик может
вернуть Result, подменяя результат действия.

Обработчики НЕ наследуются от родительского Action — каждый Action
объявляет свои обработчики явно. Имя метода обязано заканчиваться
на "_on_error". Сигнатура: (self, params, state, box, connections, error).

═══════════════════════════════════════════════════════════════════════════════
МЕТАДАННЫЕ
═══════════════════════════════════════════════════════════════════════════════

Управление метаданными (описание, домен, роли, зависимости, чекеры, аспекты,
соединения, обработчики ошибок) осуществляется через GateCoordinator
и ClassMetadata. Машина (ActionProductMachine) получает метаданные через
свой экземпляр координатора: self._coordinator.get(action.__class__).

BaseAction НЕ содержит метода get_metadata() и НЕ обращается к
GateCoordinator напрямую. Координатор — ответственность машины.

═══════════════════════════════════════════════════════════════════════════════
ГЕЙТ-ХОСТЫ (МАРКЕРНЫЕ МИКСИНЫ)
═══════════════════════════════════════════════════════════════════════════════

BaseAction наследует семь маркерных миксинов, каждый из которых
разрешает применение соответствующего декоратора:

    ActionMetaGateHost  → разрешает и ТРЕБУЕТ @meta
    RoleGateHost        → разрешает @check_roles
    DependencyGateHost  → разрешает @depends
    CheckerGateHost     → разрешает чекеры (@result_string и др.)
    AspectGateHost      → разрешает @regular_aspect и @summary_aspect
    ConnectionGateHost  → разрешает @connection
    OnErrorGateHost     → разрешает @on_error

Миксины не содержат логики — только служат проверочными маркерами
для issubclass(). Декораторы уровня класса (@meta, @check_roles, @depends,
@connection) проверяют гейт-хост самостоятельно при применении.
Декораторы уровня метода (@regular_aspect, @summary_aspect, чекеры,
@on_error) не могут проверить гейт-хост в момент применения (класс ещё
не создан), поэтому проверка выполняется в MetadataBuilder.

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТ ИМЕНОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

Каждый класс, наследующий BaseAction (прямо или косвенно), обязан иметь
суффикс "Action" в имени. Проверка выполняется в __init_subclass__
при определении класса. Нарушение → NamingSuffixError.

Примеры:
    class CreateOrderAction(BaseAction[...]):  ← OK
    class PingAction(BaseAction[...]):         ← OK
    class MockAction(BaseAction[...]):         ← OK
    class CreateOrder(BaseAction[...]):        ← NamingSuffixError

═══════════════════════════════════════════════════════════════════════════════
КЕШИРОВАНИЕ ИМЕНИ КЛАССА
═══════════════════════════════════════════════════════════════════════════════

Метод get_full_class_name() формирует полное имя класса (module.ClassName)
и кеширует его на уровне класса (cls._full_class_name), а не экземпляра.
Это означает, что все экземпляры одного класса разделяют один кеш.
Запись выполняется через cls._full_class_name, а не self._full_class_name,
чтобы избежать создания instance-attribute, затеняющего class-attribute.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    >>> @meta(description="Проверка доступности сервиса")
    ... @check_roles(ROLE_NONE)
    ... class PingAction(BaseAction[BaseParams, BaseResult]):
    ...     @summary_aspect("Pong response")
    ...     async def pong_summary(self, params, state, box, connections):
    ...         return BaseResult(message="pong")

    >>> @meta(description="Создание заказа", domain=OrdersDomain)
    ... @check_roles("manager")
    ... @depends(PaymentService)
    ... @connection(PostgresManager, key="db")
    ... class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    ...     @regular_aspect("Валидация")
    ...     async def validate_aspect(self, params, state, box, connections):
    ...         return {}
    ...     @summary_aspect("Результат")
    ...     async def build_result_summary(self, params, state, box, connections):
    ...         return OrderResult(...)
    ...     @on_error(ValueError, description="Ошибка валидации")
    ...     async def validation_on_error(self, params, state, box, connections, error):
    ...         return OrderResult(order_id="ERR", status="error", total=0)
"""

from abc import ABC
from typing import Any

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.exceptions import NamingSuffixError
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.core.protocols import ReadableDataProtocol, WritableDataProtocol
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.on_error.on_error_gate_host import OnErrorGateHost
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost

# Суффикс, обязательный для всех классов, наследующих BaseAction.
_REQUIRED_SUFFIX = "Action"


class BaseAction[P: ReadableDataProtocol, R: WritableDataProtocol](
    ABC,
    ActionMetaGateHost,
    RoleGateHost,
    DependencyGateHost[object],
    CheckerGateHost,
    AspectGateHost,
    ConnectionGateHost,
    OnErrorGateHost,
):
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @regular_aspect
    и @summary_aspect, а обработчики ошибок — через @on_error. Не содержит
    состояния — все данные передаются через params и state (объект BaseState).

    Каждое действие обязано иметь декораторы @meta и @check_roles.
    @meta задаёт описание и опциональный домен. @check_roles задаёт
    ролевые ограничения.

    Каждый класс, наследующий BaseAction, обязан иметь суффикс "Action"
    в имени. Проверяется при определении класса через __init_subclass__.

    Метаданные (описание, домен, роли, зависимости, чекеры, аспекты,
    соединения, обработчики ошибок) собираются автоматически при первом
    обращении к классу через GateCoordinator. Доступ к метаданным
    осуществляется через координатор машины:
        metadata = machine._coordinator.get(action.__class__)

    Атрибуты класса:
        _full_class_name : str | None
            Кешированное полное имя класса (module.ClassName).
            None до первого вызова get_full_class_name().
            Хранится на уровне класса, а не экземпляра — все экземпляры
            одного класса разделяют один кеш.
    """

    _full_class_name: str | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается Python при создании любого подкласса BaseAction.

        Проверяет инвариант именования: имя класса обязано заканчиваться
        на "Action". Нарушение → NamingSuffixError.

        Аргументы:
            **kwargs: аргументы, передаваемые в type.__init_subclass__.

        Исключения:
            NamingSuffixError: если имя класса не заканчивается на "Action".
        """
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Класс '{cls.__name__}' наследует BaseAction, но не имеет "
                f"суффикса '{_REQUIRED_SUFFIX}'. "
                f"Переименуйте в '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

    def get_full_class_name(self) -> str:
        """
        Возвращает полное имя класса действия (модуль + имя).

        Используется для сопоставления с регулярными выражениями в плагинах,
        чтобы определить, какие обработчики плагинов должны быть вызваны
        для данного действия.

        Результат кэшируется на уровне класса после первого вызова.
        Все экземпляры одного класса получают одно и то же значение
        из общего кеша. Запись выполняется через __class__._full_class_name,
        чтобы не создавать instance-attribute на каждом экземпляре.

        Возвращает:
            Строка вида 'module.path.ClassName'.
        """
        if self.__class__._full_class_name is None:
            module: str = self.__class__.__module__ or ""
            self.__class__._full_class_name = f"{module}.{self.__class__.__qualname__}"
        return self.__class__._full_class_name
