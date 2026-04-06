# src/action_machine/adapters/base_route_record.py
"""
BaseRouteRecord — абстрактный frozen-датакласс конфигурации маршрута адаптера.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord хранит конфигурацию одного зарегистрированного маршрута
адаптера. Содержит поля, общие для любого протокола. Протокольно-
специфичные поля определяются в наследниках.

BaseRouteRecord нельзя инстанцировать напрямую — только через наследников.

═══════════════════════════════════════════════════════════════════════════════
АВТОИЗВЛЕЧЕНИЕ ТИПОВ ИЗ ACTION
═══════════════════════════════════════════════════════════════════════════════

params_type и result_type ВСЕГДА извлекаются автоматически из generic-
параметров BaseAction[P, R] при создании записи. Разработчик никогда
не указывает их вручную. Это обеспечивает единый источник правды:
типы определены в классе действия и не дублируются.

Извлечение выполняется функцией ``extract_action_types(action_class)``,
которая обходит ``__orig_bases__`` в MRO класса и находит запись вида
``BaseAction[P, R]``. Аргументы P и R могут быть:

- Конкретными типами (type) — используются напрямую.
- Строковыми ForwardRef (при вложенных Params/Result внутри Action) —
  резолвятся через модуль, в котором определён класс действия.

Это позволяет использовать паттерн вложенных моделей:

    class CreateOrderAction(BaseAction["CreateOrderAction.Params", "CreateOrderAction.Result"]):
        class Params(BaseParams): ...
        class Result(BaseResult): ...

Результат извлечения кешируется в приватных полях ``_cached_params_type``
и ``_cached_result_type`` через ``object.__setattr__`` (обход frozen).

═══════════════════════════════════════════════════════════════════════════════
ОПЦИОНАЛЬНЫЕ ПОЛЯ
═══════════════════════════════════════════════════════════════════════════════

    request_model : type | None
        Модель входящего запроса на протокольном уровне. Если None —
        используется params_type (типы совпадают, маппер не нужен).
        Если указана и отличается от params_type — params_mapper обязателен.

    response_model : type | None
        Модель ответа на протокольном уровне. Если None — используется
        result_type. Если указана и отличается от result_type —
        response_mapper обязателен.

    params_mapper : Callable[[request_model], params_type] | None
        Преобразование протокольного запроса в параметры действия.
        Обязателен если request_model указан и отличается от params_type.
        Назван по тому, что возвращает: params.

    response_mapper : Callable[[result_type], response_model] | None
        Преобразование результата действия в протокольный ответ.
        Обязателен если response_model указан и отличается от result_type.
        Назван по тому, что возвращает: response.

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ ИНВАРИАНТОВ
═══════════════════════════════════════════════════════════════════════════════

При создании экземпляра (в __post_init__) проверяются инварианты:

1. Нельзя создать экземпляр BaseRouteRecord напрямую → TypeError.
2. action_class должен быть подклассом BaseAction → TypeError.
3. Из action_class должны извлекаться P и R → TypeError если не удалось.
4. Если request_model указан, отличается от params_type, и params_mapper
   не указан → ValueError.
5. Если response_model указан, отличается от result_type, и response_mapper
   не указан → ValueError.

═══════════════════════════════════════════════════════════════════════════════
КЕШИРОВАНИЕ ИЗВЛЕЧЁННЫХ ТИПОВ
═══════════════════════════════════════════════════════════════════════════════

Frozen dataclass не позволяет записывать атрибуты через ``self.attr = val``.
Для кеширования результата ``extract_action_types()`` используется
``object.__setattr__(self, "_cached_params_type", p_type)`` — тот же
приём, что в pydantic frozen-моделях. Pylint не видит эти атрибуты —
подавлено через ``# pylint: disable=no-member`` на свойствах.

═══════════════════════════════════════════════════════════════════════════════
ВЫЧИСЛЯЕМЫЕ СВОЙСТВА
═══════════════════════════════════════════════════════════════════════════════

    params_type : type
        Тип параметров действия (P из BaseAction[P, R]).

    result_type : type
        Тип результата действия (R из BaseAction[P, R]).

    effective_request_model : type
        Фактическая модель запроса: request_model если указан, иначе params_type.

    effective_response_model : type
        Фактическая модель ответа: response_model если указан, иначе result_type.

═══════════════════════════════════════════════════════════════════════════════
КОНВЕНЦИЯ ИМЕНОВАНИЯ МАППЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый маппер назван по тому, что он ВОЗВРАЩАЕТ:

    params_mapper   → возвращает params   (преобразует request → params)
    response_mapper → возвращает response (преобразует result  → response)

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА НАСЛЕДОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseRouteRecord (frozen, нельзя инстанцировать)
        │
        ├── FastApiRouteRecord (frozen)
        │       Поля: method, path, tags, summary, ...
        │
        ├── MCPRouteRecord (frozen)
        │       Поля: tool_name, description, ...
        │
        └── GRPCRouteRecord (frozen)
                Поля: service_name, method_name, ...
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
    Резолвит ForwardRef в конкретный тип, используя контекст модуля
    и пространство имён класса действия.

    ForwardRef возникает, когда generic-параметры BaseAction указаны
    строками (forward references):

        class MyAction(BaseAction["MyAction.Params", "MyAction.Result"]):
            class Params(BaseParams): ...
            class Result(BaseResult): ...

    Python записывает строки как ForwardRef в __orig_bases__. Для резолва
    нужен globalns (из модуля, где определён класс) и localns (атрибуты
    самого класса для вложенных классов).

    Аргументы:
        ref: объект ForwardRef для резолва.
        action_class: класс действия, в контексте которого выполняется резолв.

    Возвращает:
        Конкретный тип (type) или None если резолв не удался.
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
    Резолвит один generic-аргумент в конкретный тип.

    Обрабатывает три случая:
    1. arg уже является type → возвращает как есть.
    2. arg является ForwardRef → резолвит через _resolve_forward_ref.
    3. arg является строкой → оборачивает в ForwardRef и резолвит.

    Аргументы:
        arg: generic-аргумент из get_args(base).
        action_class: класс действия для контекста резолва.

    Возвращает:
        Конкретный тип (type) или None если резолв не удался.
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
    Извлекает типы P (params) и R (result) из BaseAction[P, R].

    Обходит ``__orig_bases__`` текущего класса и всех родителей в MRO.
    Ищет запись вида ``BaseAction[P, R]``. Аргументы P и R могут быть:

    - Конкретными типами (type) — используются напрямую.
    - ForwardRef (строковые forward references) — резолвятся через
      модуль и пространство имён класса действия.

    Это обеспечивает поддержку паттерна вложенных моделей:

        class MyAction(BaseAction["MyAction.Params", "MyAction.Result"]):
            class Params(BaseParams): ...
            class Result(BaseResult): ...

    Аргументы:
        action_class: класс действия (наследник BaseAction).

    Возвращает:
        Кортеж (params_type, result_type).

    Исключения:
        TypeError: если не удалось извлечь или резолвить generic-параметры.
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
        f"Не удалось извлечь generic-параметры P и R из {action_class.__name__}. "
        f"Класс действия должен быть объявлен как "
        f"BaseAction[ConcreteParams, ConcreteResult], например: "
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