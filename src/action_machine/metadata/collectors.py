# src/action_machine/metadata/collectors.py
"""
Модуль: collectors — функции извлечения метаданных из временных атрибутов класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит все функции сбора, которые читают временные атрибуты,
оставленные декораторами, и возвращают структурированные данные
для ``ClassMetadata``.

Включает сбор описаний полей Params и Result из pydantic model_fields.
Generic-параметры P и R извлекаются из BaseAction[P, R] через
``__orig_bases__`` и ``get_args()``.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИП: ТОЛЬКО СОБСТВЕННЫЕ ДЕКОРАТОРЫ
═══════════════════════════════════════════════════════════════════════════════

Большинство коллекторов собирают данные ТОЛЬКО из текущего класса
(``vars(cls)``), игнорируя родительские классы в MRO:

- Аспекты не наследуются.
- Чекеры не наследуются.
- Подписки плагинов не наследуются.
- Обработчики ошибок (@on_error) не наследуются.
- Контекстные зависимости (@context_requires) собираются вместе
  с аспектами и обработчиками — не наследуются.
- Зависимости и соединения наследуются через getattr (MRO).
- Роли наследуются через getattr.
- Метаданные @meta наследуются через getattr.

ИСКЛЮЧЕНИЕ: collect_sensitive_fields обходит MRO.

═══════════════════════════════════════════════════════════════════════════════
СБОР КОНТЕКСТНЫХ ЗАВИСИМОСТЕЙ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @context_requires записывает frozenset ключей в атрибут
func._required_context_keys. Коллекторы collect_aspects и
collect_error_handlers читают этот атрибут и включают в AspectMeta
и OnErrorMeta соответственно.

Если _required_context_keys отсутствует — context_keys в метаданных
будет пустым frozenset, и машина не создаёт ContextView для этого
аспекта/обработчика.

═══════════════════════════════════════════════════════════════════════════════
СБОР РОЛЕЙ
═══════════════════════════════════════════════════════════════════════════════

Функция collect_role(cls) читает cls._role_info и создаёт RoleMeta,
содержащий только spec (спецификацию ролей). Поле description
в RoleMeta отсутствует — декоратор @check_roles не принимает
параметр desc.

═══════════════════════════════════════════════════════════════════════════════
СБОР ЧЕКЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Функция collect_checkers(cls) читает _checker_meta с методов и создаёт
CheckerMeta. CheckerMeta содержит только: method_name, checker_class,
field_name, required и extra_params. Поле description отсутствует —
чекеры не принимают параметр desc.

═══════════════════════════════════════════════════════════════════════════════
СБОР ОБРАБОТЧИКОВ ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Функция collect_error_handlers(cls) читает _on_error_meta с методов
текущего класса (vars(cls)) и создаёт OnErrorMeta. Обработчики НЕ
наследуются от родительских классов — каждый Action объявляет свои
обработчики явно. Порядок обработчиков определяется порядком объявления
методов в классе. Контекстные зависимости читаются из
_required_context_keys того же метода.

═══════════════════════════════════════════════════════════════════════════════
СБОР ПОДПИСОК ПЛАГИНОВ
═══════════════════════════════════════════════════════════════════════════════

Функция collect_subscriptions(cls) читает _on_subscriptions с методов
текущего класса (vars(cls)) и собирает SubscriptionInfo. Подписки НЕ
наследуются от родительских плагинов — каждый плагин объявляет свои
обработчики явно.

Каждый SubscriptionInfo содержит:
- event_class — тип события из иерархии BasePluginEvent для isinstance-проверки.
- method_name — имя метода-обработчика.
- action_class — фильтр по типу действия (tuple[type, ...] | None).
- action_name_pattern — regex по строковому имени действия (str | None).
- aspect_name_pattern — regex по имени аспекта (str | None, только для AspectEvent).
- nest_level — фильтр по уровню вложенности (tuple[int, ...] | None).
- domain — фильтр по бизнес-домену (type | None).
- predicate — произвольная функция фильтрации (Callable | None).
- ignore_exceptions — подавление ошибок обработчика (bool).

═══════════════════════════════════════════════════════════════════════════════
СБОР ПОЛЕЙ PARAMS И RESULT
═══════════════════════════════════════════════════════════════════════════════

Функции collect_params_fields(cls) и collect_result_fields(cls) извлекают
generic-параметры P и R из BaseAction[P, R]. Для каждого pydantic-класса
читают model_fields и собирают FieldDescriptionMeta:

- field_name — имя поля.
- field_type — строковое представление аннотации типа.
- description — из FieldInfo.description.
- examples — из FieldInfo.examples.
- constraints — gt, ge, lt, le, min_length, max_length, pattern и др.
- required — True если нет значения по умолчанию.
- default — значение по умолчанию или PydanticUndefined.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

Функции этого модуля вызываются только из ``MetadataBuilder.build()``
в модуле ``builder.py``. Они не являются частью публичного API пакета.
"""

from __future__ import annotations

from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from action_machine.core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    FieldDescriptionMeta,
    MetaInfo,
    OnErrorMeta,
    RoleMeta,
    SensitiveFieldMeta,
)
from action_machine.plugins.subscription_info import SubscriptionInfo


def full_class_name(cls: type) -> str:
    """
    Формирует полное имя класса: module.ClassName.

    Если модуль ``__main__`` или отсутствует, возвращает просто имя класса.

    Аргументы:
        cls: класс, для которого формируется имя.

    Возвращает:
        str — полное имя вида ``"module.ClassName"``.
    """
    module = getattr(cls, "__module__", None)
    if module and module != "__main__":
        return f"{module}.{cls.__qualname__}"
    return cls.__qualname__


# ─────────────────────────────────────────────────────────────────────────────
# Описание и домен (@meta)
# ─────────────────────────────────────────────────────────────────────────────


def collect_meta(cls: type) -> MetaInfo | None:
    """
    Извлекает метаданные описания и домена из ``cls._meta_info``.

    Использует ``getattr(cls, ...)`` — учитывает MRO.

    Возвращает:
        ``MetaInfo`` или ``None``.
    """
    meta_info: dict[str, Any] | None = getattr(cls, "_meta_info", None)
    if meta_info is None:
        return None

    return MetaInfo(
        description=meta_info["description"],
        domain=meta_info.get("domain"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Роли
# ─────────────────────────────────────────────────────────────────────────────


def collect_role(cls: type) -> RoleMeta | None:
    """
    Извлекает ролевые метаданные из ``cls._role_info``.

    Использует ``getattr(cls, ...)`` — учитывает MRO.
    RoleMeta содержит только spec — спецификацию ролей.

    Возвращает:
        ``RoleMeta`` или ``None``.
    """
    role_info: dict[str, Any] | None = getattr(cls, "_role_info", None)
    if role_info is None:
        return None

    return RoleMeta(
        spec=role_info["spec"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Зависимости
# ─────────────────────────────────────────────────────────────────────────────


def collect_dependencies(cls: type) -> list[Any]:
    """
    Извлекает список ``DependencyInfo`` из ``cls._depends_info``.

    Использует ``getattr(cls, ...)`` — учитывает MRO.

    Возвращает:
        ``list[DependencyInfo]``.
    """
    return list(getattr(cls, "_depends_info", []))


# ─────────────────────────────────────────────────────────────────────────────
# Соединения
# ─────────────────────────────────────────────────────────────────────────────


def collect_connections(cls: type) -> list[Any]:
    """
    Извлекает список ``ConnectionInfo`` из ``cls._connection_info``.

    Использует ``getattr(cls, ...)`` — учитывает MRO.

    Возвращает:
        ``list[ConnectionInfo]``.
    """
    return list(getattr(cls, "_connection_info", []))


# ─────────────────────────────────────────────────────────────────────────────
# Аспекты
# ─────────────────────────────────────────────────────────────────────────────


def collect_aspects(cls: type) -> list[AspectMeta]:
    """
    Собирает ``AspectMeta`` из методов, объявленных ТОЛЬКО в текущем классе.

    Обход по ``vars(cls)`` — аспекты родительских классов НЕ наследуются.

    Для каждого метода с ``_new_aspect_meta`` также читает
    ``_required_context_keys`` (записанный декоратором @context_requires).
    Если атрибут отсутствует — context_keys будет пустым frozenset,
    что означает: аспект не запрашивает доступ к контексту и вызывается
    со стандартной сигнатурой (5 параметров).

    Возвращает:
        ``list[AspectMeta]`` — аспекты в порядке объявления.
    """
    aspects: list[AspectMeta] = []

    for attr_name, attr_value in vars(cls).items():
        func = attr_value
        if isinstance(func, property) and func.fget is not None:
            func = func.fget

        meta = getattr(func, "_new_aspect_meta", None)
        if meta is not None:
            context_keys = frozenset(getattr(func, "_required_context_keys", ()))
            aspects.append(AspectMeta(
                method_name=attr_name,
                aspect_type=meta["type"],
                description=meta.get("description", ""),
                method_ref=func,
                context_keys=context_keys,
            ))

    return aspects


# ─────────────────────────────────────────────────────────────────────────────
# Чекеры
# ─────────────────────────────────────────────────────────────────────────────


def collect_checkers(cls: type) -> list[CheckerMeta]:
    """
    Собирает ``CheckerMeta`` из методов, объявленных ТОЛЬКО в текущем классе.

    Обход по ``vars(cls)`` — чекеры родительских классов НЕ наследуются.

    CheckerMeta содержит: method_name, checker_class, field_name, required
    и extra_params. Поле description отсутствует — чекеры работают
    без текстовых описаний.

    Возвращает:
        ``list[CheckerMeta]``.
    """
    checkers: list[CheckerMeta] = []

    for attr_name, attr_value in vars(cls).items():
        func = attr_value
        if isinstance(func, property) and func.fget is not None:
            func = func.fget

        checker_list = getattr(func, "_checker_meta", None)
        if checker_list is not None:
            for checker_dict in checker_list:
                checkers.append(CheckerMeta(
                    method_name=attr_name,
                    checker_class=checker_dict.get("checker_class", type(None)),
                    field_name=checker_dict.get("field_name", ""),
                    required=checker_dict.get("required", False),
                    extra_params={
                        k: v for k, v in checker_dict.items()
                        if k not in (
                            "checker_class", "field_name", "required"
                        )
                    },
                ))

    return checkers


# ─────────────────────────────────────────────────────────────────────────────
# Обработчики ошибок (@on_error)
# ─────────────────────────────────────────────────────────────────────────────


def collect_error_handlers(cls: type) -> list[OnErrorMeta]:
    """
    Собирает ``OnErrorMeta`` из методов, объявленных ТОЛЬКО в текущем классе.

    Обход по ``vars(cls)`` — обработчики ошибок родительских классов
    НЕ наследуются. Каждый Action объявляет свои обработчики явно.

    Для каждого метода с ``_on_error_meta`` также читает
    ``_required_context_keys`` (записанный декоратором @context_requires).
    Если атрибут отсутствует — context_keys будет пустым frozenset,
    что означает: обработчик не запрашивает доступ к контексту
    и вызывается со стандартной сигнатурой (6 параметров).

    Обработчик имеет собственный @context_requires, независимый от аспекта,
    который упал. Машина создаёт отдельный ContextView для каждого
    обработчика на основе его собственных context_keys.

    Порядок обработчиков определяется порядком объявления методов в классе
    (порядок итерации ``vars(cls)`` в Python 3.7+ гарантированно совпадает
    с порядком определения). Это важно, потому что ActionProductMachine
    проходит по обработчикам сверху вниз и вызывает первый подходящий.

    Возвращает:
        ``list[OnErrorMeta]`` — обработчики в порядке объявления.
    """
    handlers: list[OnErrorMeta] = []

    for attr_name, attr_value in vars(cls).items():
        func = attr_value
        if isinstance(func, property) and func.fget is not None:
            func = func.fget

        meta = getattr(func, "_on_error_meta", None)
        if meta is not None:
            context_keys = frozenset(getattr(func, "_required_context_keys", ()))
            handlers.append(OnErrorMeta(
                method_name=attr_name,
                exception_types=meta["exception_types"],
                description=meta["description"],
                method_ref=func,
                context_keys=context_keys,
            ))

    return handlers


# ─────────────────────────────────────────────────────────────────────────────
# Подписки (плагины)
# ─────────────────────────────────────────────────────────────────────────────


def collect_subscriptions(cls: type) -> list[SubscriptionInfo]:
    """
    Собирает ``SubscriptionInfo`` из методов, объявленных ТОЛЬКО в текущем классе.

    Обход по ``vars(cls)`` — подписки родительских плагинов НЕ наследуются.
    Каждый плагин объявляет свои обработчики явно.

    Декоратор @on записывает в метод атрибут ``_on_subscriptions`` —
    список SubscriptionInfo. Каждый SubscriptionInfo содержит полную
    конфигурацию подписки: event_class (тип события из иерархии
    BasePluginEvent), фильтры (action_class, action_name_pattern,
    aspect_name_pattern, nest_level, domain, predicate),
    ignore_exceptions и method_name.

    Один метод может иметь несколько @on (несколько SubscriptionInfo),
    реализуя OR-логику между подписками: обработчик вызывается, если
    хотя бы одна подписка совпала. Внутри одной подписки действует
    AND-логика фильтров.

    Возвращает:
        ``list[SubscriptionInfo]`` — все подписки текущего класса.
    """
    subscriptions: list[SubscriptionInfo] = []

    for _attr_name, attr_value in vars(cls).items():
        func = attr_value
        if isinstance(func, property) and func.fget is not None:
            func = func.fget

        subs_list = getattr(func, "_on_subscriptions", None)
        if subs_list is not None:
            for sub in subs_list:
                if isinstance(sub, SubscriptionInfo):
                    subscriptions.append(sub)

    return subscriptions


# ─────────────────────────────────────────────────────────────────────────────
# Чувствительные поля
# ─────────────────────────────────────────────────────────────────────────────


def collect_sensitive_fields(cls: type) -> list[SensitiveFieldMeta]:
    """
    Сканирует properties класса и собирает ``SensitiveFieldMeta``.

    ОБХОДИТ MRO — чувствительные поля наследуются от родителей.

    Возвращает:
        ``list[SensitiveFieldMeta]``.
    """
    sensitive: list[SensitiveFieldMeta] = []
    seen_names: set[str] = set()

    for klass in cls.__mro__:
        if klass is object:
            continue

        for attr_name, attr_value in vars(klass).items():
            if attr_name in seen_names:
                continue

            getter = None
            if isinstance(attr_value, property) and attr_value.fget is not None:
                getter = attr_value.fget
            elif callable(attr_value):
                getter = attr_value

            if getter is None:
                continue

            config = getattr(getter, "_sensitive_config", None)
            if config is not None:
                sensitive.append(SensitiveFieldMeta(
                    property_name=attr_name,
                    config=dict(config),
                ))
                seen_names.add(attr_name)

    return sensitive


# ─────────────────────────────────────────────────────────────────────────────
# Ограничитель типа зависимостей
# ─────────────────────────────────────────────────────────────────────────────


def collect_depends_bound(cls: type) -> type:
    """
    Извлекает bound-тип из ``DependencyGateHost[T]``.

    Использует ``getattr(cls, ...)`` — учитывает MRO.

    Возвращает:
        ``type`` — bound-тип зависимостей. По умолчанию ``object``.
    """
    return getattr(cls, "_depends_bound", object)


# ─────────────────────────────────────────────────────────────────────────────
# Извлечение generic-параметров BaseAction[P, R]
# ─────────────────────────────────────────────────────────────────────────────


def _extract_generic_args(cls: type, base_class: type) -> tuple[type | None, type | None]:
    """
    Извлекает generic-параметры P и R из BaseAction[P, R] (или другого
    generic-базового класса) в цепочке наследования.

    Обходит ``__orig_bases__`` текущего класса и всех родителей в MRO.
    Ищет запись вида ``base_class[P, R]``, где P и R — конкретные типы
    (не TypeVar).

    Аргументы:
        cls: класс для анализа.
        base_class: generic-базовый класс (например, BaseAction).

    Возвращает:
        Кортеж (P, R). Если не найдены — (None, None).
    """
    for klass in cls.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is base_class:
                args = get_args(base)
                if len(args) >= 2:
                    p_type = args[0] if isinstance(args[0], type) else None
                    r_type = args[1] if isinstance(args[1], type) else None
                    return p_type, r_type
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Извлечение constraints из pydantic FieldInfo.metadata
# ─────────────────────────────────────────────────────────────────────────────


# Имена атрибутов pydantic FieldInfo, содержащих constraints
_CONSTRAINT_ATTRS: tuple[str, ...] = (
    "gt", "ge", "lt", "le",
    "min_length", "max_length",
    "pattern",
    "multiple_of",
    "strict",
)


def _extract_constraints(field_info: FieldInfo) -> dict[str, Any]:
    """
    Извлекает constraints из pydantic FieldInfo.

    Проверяет стандартные атрибуты FieldInfo (gt, ge, lt, le, min_length,
    max_length, pattern, multiple_of, strict). Также обходит
    field_info.metadata — список объектов-аннотаций, содержащих
    pydantic constraint-объекты (Gt, Ge, MinLen и т.д.).

    Аргументы:
        field_info: объект pydantic FieldInfo для одного поля.

    Возвращает:
        dict с ненулевыми constraints. Пустой dict если ограничений нет.
    """
    constraints: dict[str, Any] = {}

    # Прямые атрибуты FieldInfo
    for attr in _CONSTRAINT_ATTRS:
        value = getattr(field_info, attr, None)
        if value is not None:
            constraints[attr] = value

    # Metadata — список pydantic annotated-объектов (Gt, Ge, MinLen и т.д.)
    for meta_item in field_info.metadata or []:
        for attr in _CONSTRAINT_ATTRS:
            value = getattr(meta_item, attr, None)
            if value is not None and attr not in constraints:
                constraints[attr] = value

    return constraints


# ─────────────────────────────────────────────────────────────────────────────
# Сбор описаний полей из pydantic model_fields
# ─────────────────────────────────────────────────────────────────────────────


def _collect_pydantic_fields(model_cls: type) -> list[FieldDescriptionMeta]:
    """
    Собирает ``FieldDescriptionMeta`` из pydantic model_fields класса.

    Для каждого поля извлекает: имя, тип, description, examples,
    constraints, required, default.

    Аргументы:
        model_cls: pydantic-класс (наследник BaseModel) для анализа.

    Возвращает:
        ``list[FieldDescriptionMeta]`` — описания полей.
        Пустой список если класс не является pydantic-моделью
        или не имеет полей.
    """
    if not isinstance(model_cls, type) or not issubclass(model_cls, BaseModel):
        return []

    model_fields = model_cls.model_fields
    if not model_fields:
        return []

    result: list[FieldDescriptionMeta] = []

    for field_name, field_info in model_fields.items():
        # Тип поля — строковое представление аннотации
        annotation = field_info.annotation
        field_type_str = str(annotation) if annotation is not None else "Any"
        if annotation is not None and hasattr(annotation, "__name__"):
            field_type_str = annotation.__name__

        # Description
        description = field_info.description or ""

        # Examples
        examples = None
        if field_info.examples is not None:
            examples = tuple(field_info.examples)

        # Constraints
        constraints = _extract_constraints(field_info)

        # Required / Default
        is_required = field_info.is_required()
        default = field_info.default if not is_required else PydanticUndefined

        result.append(FieldDescriptionMeta(
            field_name=field_name,
            field_type=field_type_str,
            description=description,
            examples=examples,
            constraints=constraints,
            required=is_required,
            default=default,
        ))

    return result


def collect_params_fields(cls: type) -> list[FieldDescriptionMeta]:
    """
    Извлекает описания полей Params (generic-параметр P) из BaseAction[P, R].

    Ищет BaseAction в MRO класса, извлекает первый generic-аргумент P,
    и если P — pydantic-модель, собирает описания её полей.

    Аргументы:
        cls: класс действия для анализа.

    Возвращает:
        ``list[FieldDescriptionMeta]`` — описания полей Params.
        Пустой список если Params не найден или не pydantic-модель.
    """
    from action_machine.core.base_action import BaseAction  # pylint: disable=import-outside-toplevel

    p_type, _ = _extract_generic_args(cls, BaseAction)
    if p_type is None:
        return []

    return _collect_pydantic_fields(p_type)


def collect_result_fields(cls: type) -> list[FieldDescriptionMeta]:
    """
    Извлекает описания полей Result (generic-параметр R) из BaseAction[P, R].

    Ищет BaseAction в MRO класса, извлекает второй generic-аргумент R,
    и если R — pydantic-модель, собирает описания её полей.

    Аргументы:
        cls: класс действия для анализа.

    Возвращает:
        ``list[FieldDescriptionMeta]`` — описания полей Result.
        Пустой список если Result не найден или не pydantic-модель.
    """
    from action_machine.core.base_action import BaseAction  # pylint: disable=import-outside-toplevel

    _, r_type = _extract_generic_args(cls, BaseAction)
    if r_type is None:
        return []

    return _collect_pydantic_fields(r_type)
