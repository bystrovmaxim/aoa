# src/action_machine/metadata/collectors.py
"""
Модуль: collectors — функции извлечения метаданных из временных атрибутов класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит все функции сбора, которые обходят класс и его MRO,
читают временные атрибуты, оставленные декораторами, и возвращают
структурированные данные для ``ClassMetadata``.

Каждая функция принимает класс (``type``) и возвращает собранные данные:
списки, кортежи или отдельные объекты. Функции не модифицируют класс —
только читают атрибуты.

═══════════════════════════════════════════════════════════════════════════════
ВРЕМЕННЫЕ АТРИБУТЫ, ЧИТАЕМЫЕ КОЛЛЕКТОРАМИ
═══════════════════════════════════════════════════════════════════════════════

    @CheckRoles     → cls._role_info            : dict {"spec": ..., "desc": ...}
    @depends        → cls._depends_info         : list[DependencyInfo]
    @connection     → cls._connection_info       : list[ConnectionInfo]
    @regular_aspect → method._new_aspect_meta    : dict {"type": "regular", ...}
    @summary_aspect → method._new_aspect_meta    : dict {"type": "summary", ...}
    чекеры          → method._checker_meta       : list[dict]
    @on             → method._on_subscriptions   : list[SubscriptionInfo]
    @sensitive      → prop.fget._sensitive_config : dict

═══════════════════════════════════════════════════════════════════════════════
ПОРЯДОК ОБХОДА MRO
═══════════════════════════════════════════════════════════════════════════════

Для методов (аспекты, чекеры, подписки, чувствительные поля) обход
выполняется по ``cls.__mro__``, начиная с самого класса. Если дочерний
класс переопределяет метод родителя, используется версия дочернего.
Множество ``seen_names`` предотвращает дублирование.

Для атрибутов уровня класса (роли, зависимости, соединения) используется
``getattr(cls, attr, default)``, который автоматически учитывает MRO.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

Функции этого модуля вызываются только из ``MetadataBuilder.build()``
в модуле ``builder.py``. Они не являются частью публичного API пакета.
"""

from __future__ import annotations

from typing import Any

from action_machine.core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    RoleMeta,
    SensitiveFieldMeta,
)


def full_class_name(cls: type) -> str:
    """
    Формирует полное имя класса: module.ClassName.

    Если модуль ``__main__`` или отсутствует, возвращает просто имя класса.
    Используется для идентификации класса в ``ClassMetadata.class_name``,
    в узлах графа ``GateCoordinator`` и в логировании.

    Аргументы:
        cls: класс, для которого формируется имя.

    Возвращает:
        str — полное имя вида ``"module.ClassName"``.

    Примеры:
        >>> full_class_name(CreateOrderAction)
        'test_full_flow.CreateOrderAction'
        >>> full_class_name(PingAction)
        'test_full_flow.PingAction'
    """
    module = getattr(cls, "__module__", None)
    if module and module != "__main__":
        return f"{module}.{cls.__qualname__}"
    return cls.__qualname__


# ─────────────────────────────────────────────────────────────────────────────
# Роли
# ─────────────────────────────────────────────────────────────────────────────


def collect_role(cls: type) -> RoleMeta | None:
    """
    Извлекает ролевые метаданные из ``cls._role_info``.

    Декоратор ``@CheckRoles`` записывает в ``cls._role_info`` словарь:
        ``{"spec": str | list[str], "desc": str}``

    Если ``_role_info`` отсутствует — возвращает ``None`` (роли не назначены).

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``RoleMeta`` с полями ``spec`` и ``description``, или ``None``.
    """
    role_info: dict[str, Any] | None = getattr(cls, "_role_info", None)
    if role_info is None:
        return None

    return RoleMeta(
        spec=role_info["spec"],
        description=role_info.get("desc", ""),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Зависимости
# ─────────────────────────────────────────────────────────────────────────────


def collect_dependencies(cls: type) -> list[Any]:
    """
    Извлекает список ``DependencyInfo`` из ``cls._depends_info``.

    Декоратор ``@depends`` записывает в ``cls._depends_info`` список объектов
    ``DependencyInfo(cls=..., description=...)``. При первом применении
    к подклассу декоратор копирует родительский список, чтобы не мутировать его.

    Если ``_depends_info`` отсутствует — возвращает пустой список.

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``list[DependencyInfo]`` — список зависимостей в порядке объявления.
    """
    return list(getattr(cls, "_depends_info", []))


# ─────────────────────────────────────────────────────────────────────────────
# Соединения
# ─────────────────────────────────────────────────────────────────────────────


def collect_connections(cls: type) -> list[Any]:
    """
    Извлекает список ``ConnectionInfo`` из ``cls._connection_info``.

    Декоратор ``@connection`` записывает в ``cls._connection_info`` список
    объектов ``ConnectionInfo(cls=..., key=..., description=...)``.

    Если ``_connection_info`` отсутствует — возвращает пустой список.

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``list[ConnectionInfo]`` — список соединений в порядке объявления.
    """
    return list(getattr(cls, "_connection_info", []))


# ─────────────────────────────────────────────────────────────────────────────
# Аспекты
# ─────────────────────────────────────────────────────────────────────────────


def collect_aspects(cls: type) -> list[AspectMeta]:
    """
    Сканирует методы класса и собирает ``AspectMeta`` из атрибута ``_new_aspect_meta``.

    Декораторы ``@regular_aspect`` и ``@summary_aspect`` записывают в функцию:
        ``func._new_aspect_meta = {"type": "regular"|"summary", "description": "..."}``

    Обход выполняется по MRO класса, начиная с самого класса. Порядок аспектов
    определяется порядком объявления в классе (Python 3.7+ гарантирует
    сохранение порядка вставки в ``dict``). Если дочерний класс переопределяет
    метод родителя, используется версия дочернего (множество ``seen_names``).

    Для ``property``-дескрипторов извлекается getter (``fget``), так как
    декоратор может быть применён к getter до оборачивания в ``property``.

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``list[AspectMeta]`` — аспекты в порядке объявления. Каждый элемент
        содержит ``method_name``, ``aspect_type`` (``"regular"``/``"summary"``),
        ``description`` и ``method_ref`` (ссылка на функцию для вызова).
    """
    aspects: list[AspectMeta] = []
    seen_names: set[str] = set()

    for klass in cls.__mro__:
        if klass is object:
            continue

        for attr_name, attr_value in vars(klass).items():
            if attr_name in seen_names:
                continue

            func = attr_value
            if isinstance(func, property) and func.fget is not None:
                func = func.fget

            meta = getattr(func, "_new_aspect_meta", None)
            if meta is not None:
                aspects.append(AspectMeta(
                    method_name=attr_name,
                    aspect_type=meta["type"],
                    description=meta.get("description", ""),
                    method_ref=func,
                ))
                seen_names.add(attr_name)

    return aspects


# ─────────────────────────────────────────────────────────────────────────────
# Чекеры
# ─────────────────────────────────────────────────────────────────────────────


def collect_checkers(cls: type) -> list[CheckerMeta]:
    """
    Сканирует методы класса и собирает ``CheckerMeta`` из атрибута ``_checker_meta``.

    Декораторы чекеров (``@ResultStringChecker``, ``@ResultIntChecker`` и др.)
    записывают в функцию:
        ``func._checker_meta = [{"checker_class": ..., "field_name": ..., ...}, ...]``

    Один метод может иметь несколько чекеров (для разных полей).

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``list[CheckerMeta]`` — чекеры в порядке обнаружения. Каждый элемент
        содержит ``method_name``, ``checker_class``, ``field_name``,
        ``description``, ``required`` и ``extra_params``.
    """
    checkers: list[CheckerMeta] = []
    seen_names: set[str] = set()

    for klass in cls.__mro__:
        if klass is object:
            continue

        for attr_name, attr_value in vars(klass).items():
            if attr_name in seen_names:
                continue

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
                        description=checker_dict.get("description", ""),
                        required=checker_dict.get("required", False),
                        extra_params={
                            k: v for k, v in checker_dict.items()
                            if k not in (
                                "checker_class", "field_name",
                                "description", "required"
                            )
                        },
                    ))
                seen_names.add(attr_name)

    return checkers


# ─────────────────────────────────────────────────────────────────────────────
# Подписки (плагины)
# ─────────────────────────────────────────────────────────────────────────────


def collect_subscriptions(cls: type) -> list[Any]:
    """
    Сканирует методы класса и собирает ``SubscriptionInfo`` из атрибута
    ``_on_subscriptions``.

    Декоратор ``@on`` записывает в функцию:
        ``func._on_subscriptions = [SubscriptionInfo(...), ...]``

    Один метод может иметь несколько подписок (несколько ``@on``).

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``list[SubscriptionInfo]`` — подписки в порядке обнаружения.
    """
    subscriptions: list[Any] = []
    seen_names: set[str] = set()

    for klass in cls.__mro__:
        if klass is object:
            continue

        for attr_name, attr_value in vars(klass).items():
            if attr_name in seen_names:
                continue

            func = attr_value
            if isinstance(func, property) and func.fget is not None:
                func = func.fget

            subs_list = getattr(func, "_on_subscriptions", None)
            if subs_list is not None:
                subscriptions.extend(subs_list)
                seen_names.add(attr_name)

    return subscriptions


# ─────────────────────────────────────────────────────────────────────────────
# Чувствительные поля
# ─────────────────────────────────────────────────────────────────────────────


def collect_sensitive_fields(cls: type) -> list[SensitiveFieldMeta]:
    """
    Сканирует properties класса и собирает ``SensitiveFieldMeta`` из атрибута
    ``_sensitive_config``.

    Декоратор ``@sensitive`` записывает в getter property:
        ``func._sensitive_config = {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}``

    Поддерживаются оба порядка декораторов:
    - ``@property`` → ``@sensitive`` (рекомендуемый)
    - ``@sensitive`` → ``@property``

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``list[SensitiveFieldMeta]`` — чувствительные поля в порядке обнаружения.
        Каждый элемент содержит ``property_name`` и ``config`` (копия словаря
        конфигурации маскирования).
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

    ``DependencyGateHost.__init_subclass__`` записывает в класс:
        ``cls._depends_bound = <тип T>``

    Если ``_depends_bound`` отсутствует — возвращает ``object``
    (разрешены любые зависимости).

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        ``type`` — bound-тип зависимостей. По умолчанию ``object``.
    """
    return getattr(cls, "_depends_bound", object)
