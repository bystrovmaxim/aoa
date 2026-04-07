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

Включает сбор метаданных сущностей (@entity): описание и домен
из _entity_info, простые поля из model_fields, связи из Annotated-
аннотаций (контейнеры связей + Inverse/NoInverse + Rel), поля Lifecycle
(специализированные классы с _template).

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИП: ТОЛЬКО СОБСТВЕННЫЕ ДЕКОРАТОРЫ
═══════════════════════════════════════════════════════════════════════════════

Большинство коллекторов собирают данные ТОЛЬКО из текущего класса
(``vars(cls)``), игнорируя родительские классы в MRO:

- Аспекты не наследуются.
- Чекеры не наследуются.
- Подписки плагинов не наследуются.
- Обработчики ошибок (@on_error) не наследуются.
- Компенсаторы (@compensate) не наследуются.
- Контекстные зависимости (@context_requires) собираются вместе
  с аспектами, обработчиками и компенсаторами — не наследуются.
- Зависимости и соединения наследуются через getattr (MRO).
- Роли наследуются через getattr.
- Метаданные @meta наследуются через getattr.
- Метаданные @entity наследуются через getattr.

ИСКЛЮЧЕНИЕ: collect_sensitive_fields обходит MRO.

═══════════════════════════════════════════════════════════════════════════════
СБОР КОНТЕКСТНЫХ ЗАВИСИМОСТЕЙ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @context_requires записывает frozenset ключей в атрибут
func._required_context_keys. Коллекторы collect_aspects,
collect_error_handlers и collect_compensators читают этот атрибут
и включают в AspectMeta, OnErrorMeta и CompensatorMeta соответственно.

Если _required_context_keys отсутствует — context_keys в метаданных
будет пустым frozenset, и машина не создаёт ContextView для этого
аспекта/обработчика/компенсатора.

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
СБОР КОМПЕНСАТОРОВ
═══════════════════════════════════════════════════════════════════════════════

Функция collect_compensators(cls) читает _compensate_meta с методов
текущего класса (vars(cls)) и создаёт CompensatorMeta. Компенсаторы НЕ
наследуются от родительских классов.

Обоснование отсутствия наследования: компенсатор жёстко привязан
к конкретному regular-аспекту конкретного класса по строковому имени.
При наследовании аспекты могут переопределяться, добавляться, удаляться —
унаследованный компенсатор может ссылаться на несуществующий или
изменённый аспект. Явное переопределение безопаснее неявного наследования.

Контекстные зависимости читаются из _required_context_keys того же метода.
Порядок компенсаторов определяется порядком объявления методов в классе.

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
СБОР МЕТАДАННЫХ СУЩНОСТЕЙ (@entity)
═══════════════════════════════════════════════════════════════════════════════

Функция collect_entity_info(cls) читает _entity_info (от @entity)
и создаёт EntityInfo. Аналог collect_meta() для Action.

Функция collect_entity_fields(cls) обходит model_fields и собирает
EntityFieldInfo для простых полей (не связей, не Lifecycle).

Функция collect_entity_relations(cls) обходит model_fields и собирает
EntityRelationInfo для полей с контейнерами связей (CompositeOne,
AssociationMany и т.д.) в Annotated-аннотациях.

Функция collect_entity_lifecycles(cls) обходит model_fields и собирает
EntityLifecycleInfo для полей, аннотированных подклассами Lifecycle.
Специализированный класс (OrderLifecycle) содержит _template с графом
состояний, который координатор проверяет при старте (8 правил).

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

Функции этого модуля вызываются только из ``MetadataBuilder.build()``
в модуле ``builder.py``. Они не являются частью публичного API пакета.
"""

from __future__ import annotations

import inspect
from typing import Annotated, Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from action_machine.core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    CompensatorMeta,
    EntityFieldInfo,
    EntityInfo,
    EntityLifecycleInfo,
    EntityRelationInfo,
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
# Компенсаторы (@compensate)
# ─────────────────────────────────────────────────────────────────────────────


def collect_compensators(cls: type) -> list[CompensatorMeta]:
    """
    Собирает ``CompensatorMeta`` из методов, объявленных ТОЛЬКО в текущем классе.

    Обход по ``vars(cls)`` — компенсаторы родительских классов НЕ наследуются.
    Каждый Action объявляет свои компенсаторы явно.

    Обоснование отсутствия наследования: компенсатор жёстко привязан
    к конкретному regular-аспекту конкретного класса по строковому имени
    (target_aspect_name). При наследовании аспекты могут переопределяться,
    добавляться, удаляться — унаследованный компенсатор может ссылаться
    на несуществующий или изменённый аспект. Явное переопределение
    безопаснее неявного наследования.

    Для каждого метода с ``_compensate_meta`` также читает
    ``_required_context_keys`` (записанный декоратором @context_requires).
    Если атрибут отсутствует — context_keys будет пустым frozenset,
    что означает: компенсатор не запрашивает доступ к контексту
    и вызывается со стандартной сигнатурой (7 параметров).
    Непустой frozenset означает: машина создаст ContextView
    и передаст как 8-й аргумент (ctx).

    Порядок компенсаторов определяется порядком объявления методов в классе
    (порядок итерации ``vars(cls)`` в Python 3.7+ гарантированно совпадает
    с порядком определения).

    Декоратор @compensate записывает на метод атрибут ``_compensate_meta`` —
    dict с ключами:
        - "target_aspect_name" — строковое имя regular-аспекта.
        - "description" — человекочитаемое описание компенсатора.

    Валидация привязки к существующему аспекту и его типа ("regular")
    выполняется НЕ здесь, а в validate_compensators() в validators.py —
    на этапе сбора аспекты уже собраны и доступны для проверки.

    Аргументы:
        cls: класс Action для анализа.

    Возвращает:
        ``list[CompensatorMeta]`` — компенсаторы в порядке объявления.
    """
    compensators: list[CompensatorMeta] = []
    for attr_name, attr_value in vars(cls).items():
        func = attr_value
        if isinstance(func, property) and func.fget is not None:
            func = func.fget
        meta = getattr(func, "_compensate_meta", None)
        if meta is not None:
            context_keys = frozenset(getattr(func, "_required_context_keys", ()))
            compensators.append(CompensatorMeta(
                method_name=attr_name,
                target_aspect_name=meta["target_aspect_name"],
                description=meta["description"],
                method_ref=func,
                context_keys=context_keys,
            ))
    return compensators


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


# ─────────────────────────────────────────────────────────────────────────────
# Entity: описание и домен (@entity)
# ─────────────────────────────────────────────────────────────────────────────


def collect_entity_info(cls: type) -> EntityInfo | None:
    """
    Извлекает метаданные сущности из ``cls._entity_info``.

    Декоратор @entity записывает _entity_info = {"description": ..., "domain": ...}
    на класс. Аналог collect_meta() для Action [1].

    Использует ``getattr(cls, ...)`` — учитывает MRO.

    Возвращает:
        ``EntityInfo`` или ``None``.
    """
    entity_info: dict[str, Any] | None = getattr(cls, "_entity_info", None)
    if entity_info is None:
        return None
    return EntityInfo(
        description=entity_info["description"],
        domain=entity_info.get("domain"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entity: вспомогательные функции определения типов полей
# ─────────────────────────────────────────────────────────────────────────────


def _is_lifecycle_subclass(annotation: Any) -> bool:
    """
    Проверяет, является ли аннотация подклассом Lifecycle.

    Обрабатывает:
    - Прямой тип: OrderLifecycle
    - Optional: OrderLifecycle | None (Union[OrderLifecycle, None])
    - Annotated: Annotated[OrderLifecycle | None, ...]

    Аргументы:
        annotation: аннотация типа поля из model_fields.

    Возвращает:
        True если аннотация содержит подкласс Lifecycle.
    """
    import types
    import typing

    from action_machine.domain.lifecycle import Lifecycle  # pylint: disable=import-outside-toplevel

    # Разворачиваем Annotated
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _is_lifecycle_subclass(base)

    # Прямой тип
    if isinstance(annotation, type) and issubclass(annotation, Lifecycle):
        return True

    # Union (X | None)
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            if _is_lifecycle_subclass(arg):
                return True
        return False

    return False


def _extract_lifecycle_class(annotation: Any) -> type | None:
    """
    Извлекает класс Lifecycle из аннотации.

    Обрабатывает:
    - Прямой тип: OrderLifecycle
    - Optional: OrderLifecycle | None
    - Annotated: Annotated[OrderLifecycle | None, ...]

    Аргументы:
        annotation: аннотация типа поля.

    Возвращает:
        Класс-наследник Lifecycle или None.
    """
    import types
    import typing

    from action_machine.domain.lifecycle import Lifecycle  # pylint: disable=import-outside-toplevel

    # Разворачиваем Annotated
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _extract_lifecycle_class(base)

    # Прямой тип
    if isinstance(annotation, type) and issubclass(annotation, Lifecycle):
        return annotation

    # Union (X | None)
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            result = _extract_lifecycle_class(arg)
            if result is not None:
                return result

    return None


def _is_relation_container(annotation: Any) -> bool:
    """
    Проверяет, является ли аннотация контейнером связи.

    Обрабатывает:
    - Generic: AssociationOne[CustomerEntity]
    - Optional: AssociationOne[CustomerEntity] | None
    - Annotated: Annotated[AssociationOne[CustomerEntity] | None, Inverse(...)]
    - Комбинации: Annotated[X | None, ...]

    Аргументы:
        annotation: аннотация типа поля.

    Возвращает:
        True если аннотация — контейнер связи.
    """
    import types
    import typing

    from action_machine.domain.relation_containers import (  # pylint: disable=import-outside-toplevel
        BaseRelationMany,
        BaseRelationOne,
    )

    # Разворачиваем Annotated
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _is_relation_container(base)

    # Union (X | None)
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            if _is_relation_container(arg):
                return True
        return False

    # Generic origin (AssociationOne[T])
    if origin is not None and inspect.isclass(origin):
        if issubclass(origin, (BaseRelationOne, BaseRelationMany)):
            return True

    # Прямой тип
    if isinstance(annotation, type) and issubclass(
        annotation, (BaseRelationOne, BaseRelationMany)
    ):
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Entity: простые поля из model_fields
# ─────────────────────────────────────────────────────────────────────────────


def collect_entity_fields(cls: type) -> list[EntityFieldInfo]:
    """
    Собирает метаданные простых полей сущности из model_fields.

    Простое поле — поле, которое НЕ является контейнером связи
    и НЕ является подклассом Lifecycle.

    Аналог _collect_pydantic_fields() для Params/Result, но
    с фильтрацией связей и Lifecycle.

    Аргументы:
        cls: класс сущности с @entity.

    Возвращает:
        list[EntityFieldInfo] — простые поля. Пустой список если
        класс не имеет model_fields.
    """
    model_fields = getattr(cls, "model_fields", None)
    if not model_fields:
        return []

    try:
        from typing_extensions import get_type_hints  # pylint: disable=import-outside-toplevel
        hints = get_type_hints(cls, include_extras=True)
    except Exception:
        hints = {}

    fields: list[EntityFieldInfo] = []

    for field_name, field_info in model_fields.items():
        annotation = hints.get(field_name, field_info.annotation)

        # Пропускаем связи
        if _is_relation_container(annotation):
            continue

        # Пропускаем Lifecycle
        if _is_lifecycle_subclass(field_info.annotation):
            continue

        # Тип поля
        raw_annotation = field_info.annotation
        field_type_str = str(raw_annotation) if raw_annotation is not None else "Any"
        if raw_annotation is not None and hasattr(raw_annotation, "__name__"):
            field_type_str = raw_annotation.__name__

        # Description
        description = field_info.description or ""

        # Constraints
        constraints = _extract_constraints(field_info)

        # Required / Default
        is_required = field_info.is_required()
        default = field_info.default if not is_required else PydanticUndefined

        # Deprecated
        deprecated = bool(getattr(field_info, "deprecated", False))

        fields.append(EntityFieldInfo(
            field_name=field_name,
            field_type=field_type_str,
            description=description,
            required=is_required,
            default=default,
            constraints=constraints,
            deprecated=deprecated,
        ))

    return fields


# ─────────────────────────────────────────────────────────────────────────────
# Entity: связи из model_fields (Annotated-аннотации)
# ─────────────────────────────────────────────────────────────────────────────


def _extract_relation_info(
    field_name: str,
    annotation: Any,
    field_info: FieldInfo,
) -> EntityRelationInfo | None:
    """
    Извлекает метаданные связи из аннотации поля.

    Разбирает Annotated[AssociationOne[CustomerEntity] | None, Inverse(...), ...],
    извлекает контейнер, целевую сущность, Inverse/NoInverse, Rel.

    Обрабатывает:
    - Annotated[X, ...] — извлекает base_type и metadata.
    - Union (X | None) — разворачивает, берёт первый не-None аргумент.
    - Generic (AssociationOne[T]) — извлекает origin и args.

    Аргументы:
        field_name: имя поля.
        annotation: полная аннотация типа.
        field_info: pydantic FieldInfo.

    Возвращает:
        EntityRelationInfo или None.
    """
    import types
    import typing

    from action_machine.domain.relation_containers import (  # pylint: disable=import-outside-toplevel
        BaseRelationMany,
        BaseRelationOne,
    )
    from action_machine.domain.relation_markers import (  # pylint: disable=import-outside-toplevel
        Inverse,
        NoInverse,
        Rel,
    )

    # Разбираем Annotated[T, ...]
    base_type = annotation
    annotated_metadata: tuple[Any, ...] = ()

    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        base_type = args[0]
        annotated_metadata = tuple(args[1:])

    # Разворачиваем Union (X | None) — берём первый не-None аргумент
    unwrapped = base_type
    origin = get_origin(base_type)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(base_type):
            if arg is not type(None):
                unwrapped = arg
                break
    base_type = unwrapped

    # Извлекаем origin контейнера
    origin = get_origin(base_type)
    container_class = None

    if origin is not None and inspect.isclass(origin) and issubclass(
        origin, (BaseRelationOne, BaseRelationMany)
    ):
        container_class = origin
    elif isinstance(base_type, type) and issubclass(
        base_type, (BaseRelationOne, BaseRelationMany)
    ):
        container_class = base_type

    if container_class is None:
        return None

    # Целевая сущность из generic-аргумента
    target_entity = None
    container_args = get_args(base_type)
    if container_args and isinstance(container_args[0], type):
        target_entity = container_args[0]

    # Тип владения и кардинальность
    relation_type = container_class.relation_type.value
    cardinality = "one" if issubclass(container_class, BaseRelationOne) else "many"

    # Inverse / NoInverse из Annotated метаданных
    has_inverse = False
    inverse_entity = None
    inverse_field = None
    for item in annotated_metadata:
        if isinstance(item, Inverse):
            has_inverse = True
            inverse_entity = item.target_entity
            inverse_field = item.field_name
            break
        if isinstance(item, NoInverse):
            break

    # Описание из Rel (default значение поля)
    description = ""
    default_val = field_info.default
    if isinstance(default_val, Rel):
        description = default_val.description
    elif field_info.description:
        description = field_info.description

    # Deprecated
    deprecated = bool(getattr(field_info, "deprecated", False))

    return EntityRelationInfo(
        field_name=field_name,
        container_class=container_class,
        relation_type=relation_type,
        target_entity=target_entity,
        cardinality=cardinality,
        description=description,
        has_inverse=has_inverse,
        inverse_entity=inverse_entity,
        inverse_field=inverse_field,
        deprecated=deprecated,
    )


def collect_entity_relations(cls: type) -> list[EntityRelationInfo]:
    """
    Собирает метаданные связей сущности из model_fields.

    Связь — поле, аннотированное контейнером связи (CompositeOne,
    AssociationMany и т.д.) с Inverse/NoInverse в Annotated.

    Аналог collect_aspects() по паттерну: обходит model_fields,
    фильтрует по типу аннотации, извлекает метаданные.

    Аргументы:
        cls: класс сущности с @entity.

    Возвращает:
        list[EntityRelationInfo] — связи. Пустой список если нет связей.
    """
    model_fields = getattr(cls, "model_fields", None)
    if not model_fields:
        return []

    try:
        from typing_extensions import get_type_hints  # pylint: disable=import-outside-toplevel
        hints = get_type_hints(cls, include_extras=True)
    except Exception:
        hints = {}

    relations: list[EntityRelationInfo] = []

    for field_name, field_info in model_fields.items():
        annotation = hints.get(field_name, field_info.annotation)

        if not _is_relation_container(annotation):
            continue

        rel_info = _extract_relation_info(field_name, annotation, field_info)
        if rel_info is not None:
            relations.append(rel_info)

    return relations


# ─────────────────────────────────────────────────────────────────────────────
# Entity: поля Lifecycle из model_fields
# ─────────────────────────────────────────────────────────────────────────────


def collect_entity_lifecycles(cls: type) -> list[EntityLifecycleInfo]:
    """
    Собирает метаданные полей Lifecycle сущности из model_fields.

    Lifecycle — обычное pydantic-поле (OrderLifecycle | None).
    Каждый экземпляр сущности хранит своё текущее состояние
    в lifecycle.current_state. Специализированный класс (OrderLifecycle)
    содержит _template с графом состояний, который координатор
    проверяет при старте (8 правил).

    Доступ к текущему состоянию экземпляра:
        order.lifecycle                         → OrderLifecycle или None
        order.lifecycle.current_state           → "new"
        order.lifecycle.can_transition("confirmed")  → True
        order.lifecycle.available_transitions   → {"confirmed", "cancelled"}
        order.lifecycle.is_initial              → True
        order.lifecycle.is_final                → False

    Переход состояния (frozen-сущность):
        new_lc = order.lifecycle.transition("confirmed")
        confirmed_order = order.model_copy(update={"lifecycle": new_lc})

    Аргументы:
        cls: класс сущности с @entity.

    Возвращает:
        list[EntityLifecycleInfo] — поля Lifecycle. Пустой список
        если нет полей Lifecycle.
    """
    model_fields = getattr(cls, "model_fields", None)
    if not model_fields:
        return []

    lifecycles: list[EntityLifecycleInfo] = []

    for field_name, field_info in model_fields.items():
        annotation = field_info.annotation

        if not _is_lifecycle_subclass(annotation):
            continue

        lifecycle_class = _extract_lifecycle_class(annotation)
        if lifecycle_class is None:
            continue

        # Извлекаем _template из класса
        template = None
        if hasattr(lifecycle_class, "_get_template"):
            template = lifecycle_class._get_template()

        if template is None:
            continue

        states = template.get_states()
        initial_keys = template.get_initial_keys()
        final_keys = template.get_final_keys()

        lifecycles.append(EntityLifecycleInfo(
            field_name=field_name,
            lifecycle_class=lifecycle_class,
            template_ref=template,
            state_count=len(states),
            initial_count=len(initial_keys),
            final_count=len(final_keys),
        ))

    return lifecycles
