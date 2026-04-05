# src/action_machine/core/base_action.py
"""
Базовый класс для всех действий ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseAction — абстрактный базовый класс, от которого наследуются все
действия (Action) в системе. Параметризован типами Params и Result,
которые должны соответствовать протоколу ReadableDataProtocol.
Оба типа — read-only после создания (frozen).

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЕ ДЕКОРАТОРЫ
═══════════════════════════════════════════════════════════════════════════════

Каждое действие обязано иметь два декоратора:

1. ``@meta(description="...", domain=...)`` — описание и доменная
   принадлежность. Контролируется ActionMetaGateHost. MetadataBuilder
   при сборке проверяет: если класс наследует ActionMetaGateHost
   и содержит аспекты — @meta обязателен. Без него — TypeError.

2. ``@check_roles(...)`` — ролевые ограничения. Контролируется
   RoleGateHost. ActionProductMachine при выполнении проверяет:
   если действие не имеет @check_roles — TypeError.

═══════════════════════════════════════════════════════════════════════════════
АСПЕКТЫ
═══════════════════════════════════════════════════════════════════════════════

Аспекты действий (регулярные и summary) определяются в наследниках
с помощью декораторов @regular_aspect и @summary_aspect из модуля aspects.
BaseAction не содержит методов аспектов — только общую инфраструктуру.

Аспекты принимают параметр state типа BaseState (frozen-объект),
что обеспечивает единообразный интерфейс (resolve, get, keys, items)
и запрет записи. Аспект не может мутировать state — только вернуть
dict с новыми полями, который машина провалидирует чекерами.

═══════════════════════════════════════════════════════════════════════════════
УПРАВЛЯЕМЫЙ ДОСТУП К КОНТЕКСТУ
═══════════════════════════════════════════════════════════════════════════════

Прямой доступ к контексту через ToolsBox закрыт. Единственный легальный
способ получить данные контекста в аспекте — через декоратор
@context_requires, который декларирует необходимые поля, и параметр
ctx: ContextView, который машина передаёт как последний аргумент.

Без @context_requires аспект не имеет доступа к контексту вообще
и вызывается с 5 параметрами: (self, params, state, box, connections).
С @context_requires — с 6 параметрами: (self, params, state, box,
connections, ctx).

Контролируется ContextRequiresGateHost. MetadataBuilder при сборке
проверяет: если метод имеет _required_context_keys, класс обязан
наследовать ContextRequiresGateHost.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТЧИКИ ОШИБОК (@on_error)
═══════════════════════════════════════════════════════════════════════════════

Действия могут объявлять обработчики неперехваченных исключений аспектов
через декоратор @on_error. Контролируется OnErrorGateHost. Когда аспект
бросает исключение, ActionProductMachine ищет подходящий обработчик
по типу исключения (isinstance) и вызывает его. Обработчик создаёт
и возвращает новый Result, подменяя результат действия.

Обработчики НЕ наследуются от родительского Action — каждый Action
объявляет свои обработчики явно. Имя метода обязано заканчиваться
на "_on_error". Сигнатура без контекста: (self, params, state, box,
connections, error) — 6 параметров. С @context_requires: (self, params,
state, box, connections, error, ctx) — 7 параметров.

═══════════════════════════════════════════════════════════════════════════════
МЕТАДАННЫЕ
═══════════════════════════════════════════════════════════════════════════════

Управление метаданными (описание, домен, роли, зависимости, чекеры, аспекты,
соединения, обработчики ошибок, контекстные зависимости) осуществляется
через GateCoordinator и ClassMetadata. Машина (ActionProductMachine)
получает метаданные через свой экземпляр координатора:
self._coordinator.get(action.__class__).

BaseAction НЕ содержит метода get_metadata() и НЕ обращается к
GateCoordinator напрямую. Координатор — ответственность машины.

═══════════════════════════════════════════════════════════════════════════════
ГЕЙТ-ХОСТЫ (МАРКЕРНЫЕ МИКСИНЫ)
═══════════════════════════════════════════════════════════════════════════════

BaseAction наследует девять маркерных миксинов, каждый из которых
разрешает применение соответствующего декоратора:

    ActionMetaGateHost       → разрешает и ТРЕБУЕТ @meta
    RoleGateHost             → разрешает @check_roles
    DependencyGateHost       → разрешает @depends
    CheckerGateHost          → разрешает чекеры (@result_string и др.)
    AspectGateHost           → разрешает @regular_aspect и @summary_aspect
    ConnectionGateHost       → разрешает @connection
    OnErrorGateHost          → разрешает @on_error
    ContextRequiresGateHost  → разрешает @context_requires

Миксины не содержат логики — только служат проверочными маркерами
для issubclass(). Декораторы уровня класса (@meta, @check_roles, @depends,
@connection) проверяют гейт-хост самостоятельно при применении.
Декораторы уровня метода (@regular_aspect, @summary_aspect, чекеры,
@on_error, @context_requires) не могут проверить гейт-хост в момент
применения (класс ещё не создан), поэтому проверка выполняется
в MetadataBuilder при первом обращении к классу через GateCoordinator.

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТ ИМЕНОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

Каждый класс, наследующий BaseAction (прямо или косвенно), обязан иметь
суффикс "Action" в имени. Проверка выполняется в __init_subclass__
при определении класса. Нарушение → NamingSuffixError.

═══════════════════════════════════════════════════════════════════════════════
КЕШИРОВАНИЕ ИМЕНИ КЛАССА
═══════════════════════════════════════════════════════════════════════════════

Метод get_full_class_name() формирует полное имя класса (module.ClassName)
и кеширует его на уровне класса (cls._full_class_name), а не экземпляра.
Это означает, что все экземпляры одного класса разделяют один кеш.

═══════════════════════════════════════════════════════════════════════════════
FROZEN CORE-ТИПЫ
═══════════════════════════════════════════════════════════════════════════════

Оба generic-параметра P и R соответствуют ReadableDataProtocol —
оба read-only после создания. P (Params) — frozen pydantic,
R (Result) — frozen pydantic. Это единый контракт: все данные,
проходящие через конвейер, неизменяемы.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    >>> @meta(description="Проверка доступности сервиса")
    ... @check_roles(ROLE_NONE)
    ... class PingAction(BaseAction[BaseParams, BaseResult]):
    ...     @summary_aspect("Pong response")
    ...     async def pong_summary(self, params, state, box, connections):
    ...         return BaseResult()

    >>> @meta(description="Создание заказа", domain=OrdersDomain)
    ... @check_roles("manager")
    ... @depends(PaymentService)
    ... @connection(PostgresManager, key="db")
    ... class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    ...     @regular_aspect("Аудит")
    ...     @context_requires(Ctx.User.user_id)
    ...     async def audit_aspect(self, params, state, box, connections, ctx):
    ...         user_id = ctx.get(Ctx.User.user_id)
    ...         return {}
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
from action_machine.context.context_requires_gate_host import ContextRequiresGateHost
from action_machine.core.exceptions import NamingSuffixError
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.core.protocols import ReadableDataProtocol
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.on_error.on_error_gate_host import OnErrorGateHost
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost

# Суффикс, обязательный для всех классов, наследующих BaseAction.
_REQUIRED_SUFFIX = "Action"


class BaseAction[P: ReadableDataProtocol, R: ReadableDataProtocol](
    ABC,
    ActionMetaGateHost,
    RoleGateHost,
    DependencyGateHost[object],
    CheckerGateHost,
    AspectGateHost,
    ConnectionGateHost,
    OnErrorGateHost,
    ContextRequiresGateHost,
):
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @regular_aspect
    и @summary_aspect, а обработчики ошибок — через @on_error. Аспекты
    и обработчики могут декларировать доступ к полям контекста через
    @context_requires. Не содержит состояния — все данные передаются
    через params (frozen) и state (frozen BaseState).

    Каждое действие обязано иметь декораторы @meta и @check_roles.

    Каждый класс, наследующий BaseAction, обязан иметь суффикс "Action"
    в имени. Проверяется при определении класса через __init_subclass__.

    Оба generic-параметра P и R соответствуют ReadableDataProtocol —
    оба read-only после создания.

    Атрибуты класса:
        _full_class_name : str | None
            Кешированное полное имя класса (module.ClassName).
            None до первого вызова get_full_class_name().
            Хранится на уровне класса, а не экземпляра.
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
        из общего кеша.

        Возвращает:
            Строка вида 'module.path.ClassName'.
        """
        if self.__class__._full_class_name is None:
            module: str = self.__class__.__module__ or ""
            self.__class__._full_class_name = f"{module}.{self.__class__.__qualname__}"
        return self.__class__._full_class_name
