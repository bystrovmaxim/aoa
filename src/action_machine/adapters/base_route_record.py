# src/action_machine/adapters/base_route_record.py
"""
BaseRouteRecord — abstract frozen dataclass for adapter route configuration.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord stores the configuration for a single registered adapter
route. It contains fields common to any protocol. Protocol-specific fields are
defined in subclasses.

BaseRouteRecord cannot be instantiated directly — only through subclasses.

═══════════════════════════════════════════════════════════════════════════════
TYPE EXTRACTION FROM ACTION
═══════════════════════════════════════════════════════════════════════════════

params_type and result_type are ALWAYS extracted automatically from the
generic parameters BaseAction[P, R] when the record is created. The developer
never specifies them manually. This provides a single source of truth: the
types are defined in the action class and are not duplicated.

Extraction is performed by the ``extract_action_types(action_class)`` function,
which walks ``__orig_bases__`` in the class MRO and finds a base of the form
``BaseAction[P, R]``. The P and R arguments may be:

- concrete types (type) — used directly.
- string ForwardRefs (for nested Params/Result inside the Action) — resolved
  using the module where the action class is defined.

This supports the nested model pattern:

    class CreateOrderAction(BaseAction["CreateOrderAction.Params", "CreateOrderAction.Result"]):
        class Params(BaseParams): ...
        class Result(BaseResult): ...

The extraction result is cached in private fields ``_cached_params_type`` and
``_cached_result_type`` using ``object.__setattr__`` (to bypass frozen).

═══════════════════════════════════════════════════════════════════════════════
OPTIONAL FIELDS
═══════════════════════════════════════════════════════════════════════════════

    request_model : type | None
        Protocol-level request model. If None, params_type is used (types match,
        no mapper needed). If provided and different from params_type,
        params_mapper is required.

    response_model : type | None
        Protocol-level response model. If None, result_type is used. If provided
        and different from result_type, response_mapper is required.

    params_mapper : Callable[[request_model], params_type] | None
        Transforms the protocol request into action params.
        Required if request_model is provided and differs from params_type.
        Named for what it returns: params.

    response_mapper : Callable[[result_type], response_model] | None
        Transforms the action result into a protocol response.
        Required if response_model is provided and differs from result_type.
        Named for what it returns: response.

═══════════════════════════════════════════════════════════════════════════════
INVARIANT VALIDATION
═══════════════════════════════════════════════════════════════════════════════

The following invariants are checked during instance creation (in __post_init__):

1. BaseRouteRecord cannot be instantiated directly → TypeError.
2. action_class must be a subclass of BaseAction → TypeError.
3. P and R must be extractable from action_class → TypeError if extraction fails.
4. If request_model is provided, differs from params_type, and params_mapper is
   not provided → ValueError.
5. If response_model is provided, differs from result_type, and response_mapper
   is not provided → ValueError.

═══════════════════════════════════════════════════════════════════════════════
CACHING EXTRACTED TYPES
═══════════════════════════════════════════════════════════════════════════════

A frozen dataclass does not allow assignment via ``self.attr = val``. To cache the
result of ``extract_action_types()``, ``object.__setattr__(self,
"_cached_params_type", p_type)`` is used — the same pattern as in pydantic
frozen models. Pylint does not recognize these attributes and is suppressed with
``# pylint: disable=no-member`` on the properties.

═══════════════════════════════════════════════════════════════════════════════
COMPUTED PROPERTIES
═══════════════════════════════════════════════════════════════════════════════

    params_type : type
        The action params type (P from BaseAction[P, R]).

    result_type : type
        The action result type (R from BaseAction[P, R]).

    effective_request_model : type
        The effective request model: request_model if provided, otherwise params_type.

    effective_response_model : type
        The effective response model: response_model if provided, otherwise result_type.

═══════════════════════════════════════════════════════════════════════════════
MAPPER NAMING CONVENTION
═══════════════════════════════════════════════════════════════════════════════

Each mapper is named for what it RETURNS:

    params_mapper   → returns params   (transforms request → params)
    response_mapper → returns response (transforms result  → response)

═══════════════════════════════════════════════════════════════════════════════
INHERITANCE ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    BaseRouteRecord (frozen, cannot be instantiated)
        │
        ├── FastApiRouteRecord (frozen)
        │       Fields: method, path, tags, summary, ...
        │
        ├── MCPRouteRecord (frozen)
        │       Fields: tool_name, description, ...
        │
        └── GRPCRouteRecord (frozen)
                Fields: service_name, method_name, ...
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ForwardRef, get_args, get_origin

from action_machine.core.base_action import BaseAction

# ═════════════════════════════════════════════════════════════════════════════
# Резолв ForwardRef → конкретный тип
# ═════════════════════════════════════════════════════════════════════════════

def _resolve_forward_ref(ref: ForwardRef, action_class: type) -> type | None:
    """
    Resolves a ForwardRef to a concrete type using the module context and the
    action class namespace.

    ForwardRef occurs when the generic parameters of BaseAction are specified
    as strings (forward references):

        class MyAction(BaseAction["MyAction.Params", "MyAction.Result"]):
            class Params(BaseParams): ...
            class Result(BaseResult): ...

    Python stores these strings as ForwardRef objects in __orig_bases__. To resolve
    them, a globalns (from the module where the class is defined) and a localns
    (the class attributes for nested classes) are needed.

    Args:
        ref: the ForwardRef object to resolve.
        action_class: the action class in whose context the resolution occurs.

    Returns:
        A concrete type or None if resolution fails.
    """
    # Пространство имён модуля, где определён action_class
    module = sys.modules.get(action_class.__module__, None)
    globalns: dict[str, Any] = vars(module) if module else {}

    # Локальное пространство — сам класс (для вложенных Params/Result)
    localns: dict[str, Any] = {action_class.__name__: action_class}

    # Резолв через eval строкового представления ForwardRef
    # в контексте globalns + localns. Безопасно, потому что строка
    # приходит из аннотации типа в исходном коде, а не от пользователя.
    ref_str: str = ref.__forward_arg__
    try:
        resolved = eval(ref_str, globalns, localns)  # pylint: disable=eval-used
        if isinstance(resolved, type):
            return resolved
    except Exception:
        pass

    return None


def _resolve_generic_arg(arg: Any, action_class: type) -> type | None:
    """
    Resolves one generic argument to a concrete type.

    Handles three cases:
    1. arg is already a type → returns it.
    2. arg is a ForwardRef → resolves it via _resolve_forward_ref.
    3. arg is a string → wraps it in a ForwardRef and resolves it.

    Args:
        arg: generic argument from get_args(base).
        action_class: the action class used as the resolution context.

    Returns:
        A concrete type or None if resolution fails.
    """
    if isinstance(arg, type):
        return arg
    if isinstance(arg, ForwardRef):
        return _resolve_forward_ref(arg, action_class)
    if isinstance(arg, str):
        return _resolve_forward_ref(ForwardRef(arg), action_class)
    return None


# ═════════════════════════════════════════════════════════════════════════════
# Извлечение generic-параметров P и R из BaseAction[P, R]
# ═════════════════════════════════════════════════════════════════════════════

def extract_action_types(action_class: type) -> tuple[type, type]:
    """
    Extracts P (params) and R (result) types from BaseAction[P, R].

    Walks ``__orig_bases__`` of the current class and all parents in the MRO.
    It looks for a base of the form ``BaseAction[P, R]``. The P and R arguments
    may be:

    - concrete types (type) — used directly.
    - ForwardRef (string forward references) — resolved using the module and
      action class namespace.

    This supports the nested model pattern:

        class MyAction(BaseAction["MyAction.Params", "MyAction.Result"]):
            class Params(BaseParams): ...
            class Result(BaseResult): ...

    Args:
        action_class: the action class (subclass of BaseAction).

    Returns:
        A tuple (params_type, result_type).

    Raises:
        TypeError: if generic parameters could not be extracted or resolved.
    """
    for klass in action_class.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is BaseAction:
                args = get_args(base)
                if len(args) >= 2:
                    p_type = _resolve_generic_arg(args[0], action_class)
                    r_type = _resolve_generic_arg(args[1], action_class)
                    if p_type is not None and r_type is not None:
                        return p_type, r_type

    raise TypeError(
        f"Failed to extract generic parameters P and R from {action_class.__name__}. "
        f"The action class must be declared as "
        f"BaseAction[ConcreteParams, ConcreteResult], for example: "
        f"class {action_class.__name__}(BaseAction[MyParams, MyResult]): ..."
    )


# ═════════════════════════════════════════════════════════════════════════════
# BaseRouteRecord
# ═════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BaseRouteRecord:
    """
    Абстрактный frozen-датакласс конфигурации одного маршрута адаптера.

    Содержит поля, общие для любого протокола. Протокольно-специфичные
    поля определяются в наследниках.

    Frozen — после создания ни одно поле изменить нельзя.
    Нельзя инстанцировать напрямую — только через конкретных наследников.

    Атрибуты (поля dataclass):
        action_class : type[BaseAction]
            Класс действия ActionMachine. Обязательный.
        request_model : type | None
            Модель входящего запроса. Если None — используется params_type.
        response_model : type | None
            Модель ответа. Если None — используется result_type.
        params_mapper : Callable | None
            Преобразование request_model → params_type.
        response_mapper : Callable | None
            Преобразование result_type → response_model.

    Кешированные атрибуты (создаются в __post_init__ через object.__setattr__):
        _cached_params_type : type
            Кеш P из BaseAction[P, R].
        _cached_result_type : type
            Кеш R из BaseAction[P, R].
    """

    # ── Обязательное поле ──────────────────────────────────────────────
    action_class: type[BaseAction[Any, Any]]

    # ── Опциональные поля ──────────────────────────────────────────────
    request_model: type | None = None
    response_model: type | None = None
    params_mapper: Callable[..., Any] | None = None
    response_mapper: Callable[..., Any] | None = None

    # ── Валидация и кеширование ────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Проверяет инварианты и кеширует извлечённые типы.

        Порядок:
        1. Запрет прямого инстанцирования BaseRouteRecord.
        2. Проверка action_class — подкласс BaseAction.
        3. Извлечение и кеширование P и R (с поддержкой ForwardRef).
        4. Валидация params_mapper.
        5. Валидация response_mapper.

        Исключения:
            TypeError: прямое создание BaseRouteRecord; action_class
                       не BaseAction; не удалось извлечь P и R.
            ValueError: маппер отсутствует при различающихся типах.
        """
        # ── 1. Запрет прямого инстанцирования ──
        if self.__class__ is BaseRouteRecord:
            raise TypeError(
                "BaseRouteRecord нельзя инстанцировать напрямую. "
                "Создайте конкретный наследник с протокольно-специфичными "
                "полями (FastAPIRouteRecord, MCPRouteRecord и др.)."
            )

        # ── 2. Проверка action_class ──
        if not isinstance(self.action_class, type) or not issubclass(self.action_class, BaseAction):
            raise TypeError(
                f"action_class должен быть подклассом BaseAction, "
                f"получен {self.action_class!r}."
            )

        # ── 3. Извлечение и кеширование P и R ──
        p_type, r_type = extract_action_types(self.action_class)
        object.__setattr__(self, "_cached_params_type", p_type)
        object.__setattr__(self, "_cached_result_type", r_type)

        # ── 4. Валидация params_mapper ──
        if (
            self.request_model is not None
            and self.request_model is not p_type
            and self.params_mapper is None
        ):
            raise ValueError(
                f"request_model ({self.request_model.__name__}) отличается от "
                f"params_type ({p_type.__name__}), но params_mapper не указан. "
                f"Укажите params_mapper для преобразования "
                f"{self.request_model.__name__} → {p_type.__name__}."
            )

        # ── 5. Валидация response_mapper ──
        if (
            self.response_model is not None
            and self.response_model is not r_type
            and self.response_mapper is None
        ):
            raise ValueError(
                f"response_model ({self.response_model.__name__}) отличается от "
                f"result_type ({r_type.__name__}), но response_mapper не указан. "
                f"Укажите response_mapper для преобразования "
                f"{r_type.__name__} → {self.response_model.__name__}."
            )

    # ── Вычисляемые свойства ───────────────────────────────────────────

    @property
    def params_type(self) -> type:
        """
        Тип параметров действия (P из BaseAction[P, R]).

        Атрибут _cached_params_type создаётся динамически в __post_init__
        через object.__setattr__ (обход frozen dataclass). Pylint не видит
        его в определении класса — подавлено через disable=no-member.
        """
        return self._cached_params_type  # type: ignore[attr-defined, no-any-return]  # pylint: disable=no-member

    @property
    def result_type(self) -> type:
        """
        Тип результата действия (R из BaseAction[P, R]).

        Атрибут _cached_result_type создаётся динамически в __post_init__
        через object.__setattr__ (обход frozen dataclass). Pylint не видит
        его в определении класса — подавлено через disable=no-member.
        """
        return self._cached_result_type  # type: ignore[attr-defined, no-any-return]  # pylint: disable=no-member

    @property
    def effective_request_model(self) -> type:
        """Фактическая модель запроса: request_model или params_type."""
        if self.request_model is not None:
            return self.request_model
        return self.params_type

    @property
    def effective_response_model(self) -> type:
        """Фактическая модель ответа: response_model или result_type."""
        if self.response_model is not None:
            return self.response_model
        return self.result_type
