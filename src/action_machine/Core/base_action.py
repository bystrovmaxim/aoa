# src/action_machine/core/base_action.py
"""
BaseAction — базовый класс для всех действий ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BaseAction — абстрактный базовый класс, от которого наследуются все
действия (Action) в системе. Параметризован типами Params и Result,
которые должны быть наследниками BaseSchema. Оба типа — frozen
после создания (иммутабельны).

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
BaseAction не содержит methodов аспектов — только общую инфраструктуру.

Аспекты принимают параметр state типа BaseState (frozen-объект с
динамическими полями), что обеспечивает единообразный интерфейс
(resolve, get, keys, items) и запрет записи. Аспект не может мутировать
state — только вернуть dict с новыми полями, который машина провалидирует
checkerами.

═══════════════════════════════════════════════════════════════════════════════
УПРАВЛЯЕМЫЙ ДОСТУП К КОНТЕКСТУ
═══════════════════════════════════════════════════════════════════════════════

Прямой доступ к contextу через ToolsBox закрыт. Единственный легальный
способ получить данные contextа в аспекте — через декоратор
@context_requires, который декларирует необходимые поля, и параметр
ctx: ContextView, который машина передаёт как последний аргумент.

Без @context_requires аспект не имеет доступа к contextу вообще
и вызывается с 5 параметрами: (self, params, state, box, connections).
С @context_requires — с 6 параметрами: (self, params, state, box,
connections, ctx).

Контролируется ContextRequiresGateHost. MetadataBuilder при сборке
проверяет: если method имеет _required_context_keys, класс обязан
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
объявляет свои обработчики явно. Имя methodа обязано заканчиваться
на "_on_error". Сигнатура без contextа: (self, params, state, box,
connections, error) — 6 parameters. С @context_requires: (self, params,
state, box, connections, error, ctx) — 7 parameters.

═══════════════════════════════════════════════════════════════════════════════
МЕТАДАННЫЕ
═══════════════════════════════════════════════════════════════════════════════

Управление метаданными (описание, домен, роли, зависимости, checkerы, аспекты,
соединения, обработчики ошибок, contextные зависимости) задаётся декораторами
на классе (scratch) и отражается в фасетном графе координатора после
``build()``. Исполнение конвейера читает scratch с класса действия; координатор
используется машиной и инструментами для графа и ``get_snapshot``.

BaseAction НЕ содержит methodа get_metadata() и НЕ обращается к
GateCoordinator напрямую. Координатор передаётся в машину снаружи.

═══════════════════════════════════════════════════════════════════════════════
ГЕЙТ-ХОСТЫ (МАРКЕРНЫЕ МИКСИНЫ)
═══════════════════════════════════════════════════════════════════════════════

BaseAction наследует десять маркерных миксинов, каждый из которых
разрешает применение соответствующего декоратора:

    ActionMetaGateHost       → разрешает и ТРЕБУЕТ @meta
    RoleGateHost             → разрешает @check_roles
    DependencyGateHost       → разрешает @depends
    CheckerGateHost          → разрешает checkerы (@result_string и др.)
    AspectGateHost           → разрешает @regular_aspect и @summary_aspect
    CompensateGateHost       → разрешает @compensate
    ConnectionGateHost       → разрешает @connection
    OnErrorGateHost          → разрешает @on_error
    ContextRequiresGateHost  → разрешает @context_requires

Миксины не содержат логики — только служат проверочными маркерами
для issubclass(). Decoratorы уровня класса (@meta, @check_roles, @depends,
@connection) проверяют гейт-хост самостоятельно при применении.
Decoratorы уровня methodа (@regular_aspect, @summary_aspect, checkerы,
@compensate, @on_error, @context_requires) не могут проверить гейт-хост в момент
применения (класс ещё не создан), поэтому проверка выполняется
инспекторами при ``GateCoordinator.build()``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANT ИМЕНОВАНИЯ
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
GENERIC-PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

Оба generic-параметра P и R ограничены типом BaseSchema — все данные,
проходящие через конвейер, являются pydantic-моделями с dict-подобным
доступом, dot-path навигацией и иммутабельностью после создания.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    >>> @meta(description="Проверка доступности сервиса", domain=SystemDomain)
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
    ...     @regular_aspect("Validation")
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
from action_machine.compensate.compensate_gate_host import CompensateGateHost
from action_machine.context.context_requires_gate_host import ContextRequiresGateHost
from action_machine.core.base_schema import BaseSchema
from action_machine.core.exceptions import NamingSuffixError
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.on_error.on_error_gate_host import OnErrorGateHost
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost

# Суффикс, required для всех классов, наследующих BaseAction.
_REQUIRED_SUFFIX = "Action"


class BaseAction[P: BaseSchema, R: BaseSchema](
    ABC,
    ActionMetaGateHost,
    RoleGateHost,
    DependencyGateHost[object],
    CheckerGateHost,
    AspectGateHost,
    CompensateGateHost,
    ConnectionGateHost,
    OnErrorGateHost,
    ContextRequiresGateHost,
):
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @regular_aspect
    и @summary_aspect, а обработчики ошибок — через @on_error. Аспекты
    и обработчики могут декларировать доступ к полям contextа через
    @context_requires. Не содержит состояния — все данные передаются
    через params (frozen BaseParams) и state (frozen BaseState).

    Каждое действие обязано иметь декораторы @meta и @check_roles.

    Каждый класс, наследующий BaseAction, обязан иметь суффикс "Action"
    в имени. Checksся при определении класса через __init_subclass__.

    Оба generic-параметра P и R ограничены типом BaseSchema —
    все данные в конвейере являются pydantic-моделями.

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

        Checks инвариант именования: имя класса обязано заканчиваться
        на "Action". Нарушение → NamingSuffixError.

        Args:
            **kwargs: аргументы, передаваемые в type.__init_subclass__.

        Raises:
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
        Returns полное имя класса действия (модуль + имя).

        Используется для сопоставления с регулярными выражениями в плагинах,
        чтобы определить, какие обработчики плагинов должны быть вызваны
        для данного действия.

        Результат кэшируется на уровне класса после первого вызова.
        Все экземпляры одного класса получают одно и то же значение
        из общего кеша.

        Returns:
            Строка вида 'module.path.ClassName'.
        """
        if self.__class__._full_class_name is None:
            module: str = self.__class__.__module__ or ""
            self.__class__._full_class_name = f"{module}.{self.__class__.__qualname__}"
        return self.__class__._full_class_name

    # ─────────────────────────────────────────────────────────────────────
    # Scratch metadata contract (class self-description API)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _scratch_unwrap_member(attr: Any) -> Any:
        """Unwrap property to fget for metadata extraction."""
        if isinstance(attr, property) and attr.fget is not None:
            return attr.fget
        return attr

    @classmethod
    def scratch_aspects(cls) -> tuple[Any, ...]:
        """Read aspect metadata directly from class scratch attributes."""
        # Deferred: avoid import cycles with gate-host inspectors.
        from action_machine.aspects.aspect_gate_host_inspector import (  # pylint: disable=import-outside-toplevel
            AspectGateHostInspector,
        )

        result: list[Any] = []
        for name, attr in vars(cls).items():
            func = cls._scratch_unwrap_member(attr)
            if not callable(func):
                continue
            meta = getattr(func, "_new_aspect_meta", None)
            if meta is None:
                continue
            result.append(
                AspectGateHostInspector.Snapshot.Aspect(
                    method_name=name,
                    aspect_type=meta["type"],
                    description=meta.get("description", ""),
                    method_ref=func,
                    context_keys=frozenset(
                        getattr(func, "_required_context_keys", ()) or (),
                    ),
                ),
            )
        return tuple(result)

    @classmethod
    def scratch_checkers_for_aspect(
        cls,
        method_name: str,
        method_ref: Any | None = None,
    ) -> tuple[Any, ...]:
        """Read checker rows bound to one aspect method."""
        from action_machine.checkers.checker_gate_host_inspector import (  # pylint: disable=import-outside-toplevel
            CheckerGateHostInspector,
        )

        if method_ref is None:
            method_ref = getattr(cls, method_name, None)
            method_ref = cls._scratch_unwrap_member(method_ref)
        checker_list = getattr(method_ref, "_checker_meta", None)
        if not checker_list:
            return ()
        out: list[Any] = []
        for d in checker_list:
            extra = {
                k: v
                for k, v in d.items()
                if k not in ("checker_class", "field_name", "required")
            }
            out.append(
                CheckerGateHostInspector.Snapshot.Checker(
                    method_name=method_name,
                    checker_class=d["checker_class"],
                    field_name=d["field_name"],
                    required=d.get("required", False),
                    extra_params=extra,
                ),
            )
        return tuple(out)

    @classmethod
    def scratch_error_handlers(cls) -> tuple[Any, ...]:
        """Read @on_error handler metadata directly from class methods."""
        from action_machine.on_error.on_error_gate_host_inspector import (  # pylint: disable=import-outside-toplevel
            OnErrorGateHostInspector,
        )

        out: list[Any] = []
        for name, attr in vars(cls).items():
            func = cls._scratch_unwrap_member(attr)
            if not callable(func):
                continue
            meta = getattr(func, "_on_error_meta", None)
            if meta is None:
                continue
            et = meta.get("exception_types", ())
            if isinstance(et, type):
                et = (et,)
            else:
                et = tuple(et)
            out.append(
                OnErrorGateHostInspector.Snapshot.ErrorHandler(
                    method_name=name,
                    exception_types=et,
                    description=meta.get("description", ""),
                    method_ref=func,
                    context_keys=frozenset(
                        getattr(func, "_required_context_keys", ()) or (),
                    ),
                ),
            )
        return tuple(out)

    @classmethod
    def scratch_compensators(cls) -> tuple[Any, ...]:
        """Read @compensate metadata directly from class methods."""
        from action_machine.compensate.compensate_gate_host_inspector import (  # pylint: disable=import-outside-toplevel
            CompensateGateHostInspector,
        )

        out: list[Any] = []
        for name, attr in vars(cls).items():
            func = cls._scratch_unwrap_member(attr)
            if not callable(func):
                continue
            meta = getattr(func, "_compensate_meta", None)
            if meta is None:
                continue
            out.append(
                CompensateGateHostInspector.Snapshot.Compensator(
                    method_name=name,
                    target_aspect_name=meta.get("target_aspect_name", ""),
                    description=meta.get("description", ""),
                    method_ref=func,
                    context_keys=frozenset(
                        getattr(func, "_required_context_keys", ()) or (),
                    ),
                ),
            )
        return tuple(out)

    @classmethod
    def scratch_connection_keys(cls) -> tuple[str, ...]:
        """Read declared @connection keys from class-level scratch info."""
        info = getattr(cls, "_connection_info", None)
        if not info:
            return ()
        return tuple(c.key for c in info)

    @classmethod
    def scratch_role_spec(cls) -> Any:
        """Read role spec from class-level role scratch info."""
        info = getattr(cls, "_role_info", None)
        if not isinstance(info, dict):
            return None
        return info.get("spec")
