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

2. @CheckRoles(...) — ролевые ограничения. Контролируется RoleGateHost.
   ActionProductMachine при выполнении проверяет: если действие не имеет
   @CheckRoles — TypeError.

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
МЕТАДАННЫЕ
═══════════════════════════════════════════════════════════════════════════════

Управление метаданными (описание, домен, роли, зависимости, чекеры, аспекты,
соединения) осуществляется через GateCoordinator и ClassMetadata. Машина
(ActionProductMachine) получает метаданные через свой экземпляр
координатора: self._coordinator.get(action.__class__).

BaseAction НЕ содержит метода get_metadata() и НЕ обращается к
GateCoordinator напрямую. Координатор — ответственность машины.

═══════════════════════════════════════════════════════════════════════════════
ГЕЙТ-ХОСТЫ (МАРКЕРНЫЕ МИКСИНЫ)
═══════════════════════════════════════════════════════════════════════════════

BaseAction наследует шесть маркерных миксинов, каждый из которых
разрешает применение соответствующего декоратора:

    ActionMetaGateHost  → разрешает и ТРЕБУЕТ @meta
    RoleGateHost        → разрешает @CheckRoles
    DependencyGateHost  → разрешает @depends
    CheckerGateHost     → разрешает чекеры (@ResultStringChecker и др.)
    AspectGateHost      → разрешает @regular_aspect и @summary_aspect
    ConnectionGateHost  → разрешает @connection

Миксины не содержат логики — только служат проверочными маркерами
для issubclass(). Декораторы уровня класса (@meta, @CheckRoles, @depends,
@connection) проверяют гейт-хост самостоятельно при применении.
Декораторы уровня метода (@regular_aspect, @summary_aspect, чекеры)
не могут проверить гейт-хост в момент применения (класс ещё не создан),
поэтому проверка выполняется в MetadataBuilder.

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
    ... @CheckRoles(CheckRoles.NONE, desc="No authentication")
    ... class PingAction(BaseAction[BaseParams, BaseResult]):
    ...     @summary_aspect("Pong response")
    ...     async def summary(self, params, state, box, connections):
    ...         return BaseResult(message="pong")

    >>> @meta(description="Создание заказа", domain=OrdersDomain)
    ... @CheckRoles("manager")
    ... @depends(PaymentService)
    ... @connection(PostgresManager, key="db")
    ... class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    ...     @regular_aspect("Валидация")
    ...     async def validate(self, params, state, box, connections):
    ...         return {}
    ...     @summary_aspect("Результат")
    ...     async def build_result(self, params, state, box, connections):
    ...         return OrderResult(...)
"""

from abc import ABC

from action_machine.aspects.aspect_gate_host import AspectGateHost

# Маркерные миксины — разрешают применение соответствующих декораторов
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.core.protocols import ReadableDataProtocol, WritableDataProtocol
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost


class BaseAction[P: ReadableDataProtocol, R: WritableDataProtocol](
    ABC,
    ActionMetaGateHost,
    RoleGateHost,
    DependencyGateHost[object],
    CheckerGateHost,
    AspectGateHost,
    ConnectionGateHost,
):
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @regular_aspect
    и @summary_aspect. Не содержит состояния — все данные передаются
    через params и state (объект BaseState).

    Каждое действие обязано иметь декораторы @meta и @CheckRoles.
    @meta задаёт описание и опциональный домен. @CheckRoles задаёт
    ролевые ограничения.

    Метаданные (описание, домен, роли, зависимости, чекеры, аспекты,
    соединения) собираются автоматически при первом обращении к классу
    через GateCoordinator. Доступ к метаданным осуществляется через
    координатор машины:
        metadata = machine._coordinator.get(action.__class__)

    Атрибуты класса:
        _full_class_name : str | None
            Кешированное полное имя класса (module.ClassName).
            None до первого вызова get_full_class_name().
            Хранится на уровне класса, а не экземпляра — все экземпляры
            одного класса разделяют один кеш.
    """

    _full_class_name: str | None = None

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
