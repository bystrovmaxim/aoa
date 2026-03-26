# src/action_machine/Core/metadata_builder.py
"""
Модуль: MetadataBuilder — сборщик ClassMetadata из временных атрибутов класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

MetadataBuilder — это статический сборщик, который обходит класс (Action или
Plugin), читает временные атрибуты, оставленные декораторами, и конструирует
один иммутабельный экземпляр ClassMetadata.

Декораторы при определении класса записывают «сырые» данные во временные
атрибуты:

    @depends        → cls._depends_info        : list[DependencyInfo]
    @CheckRoles     → cls._role_info            : dict {"spec": ..., "desc": ...}
    @connection     → cls._connection_info      : list[ConnectionInfo]
    @regular_aspect → method._new_aspect_meta   : dict {"type": "regular", ...}
    @summary_aspect → method._new_aspect_meta   : dict {"type": "summary", ...}
    @StringField... → method._checker_meta      : list[dict]
    @on             → method._on_subscriptions  : list[SubscriptionInfo]
    @sensitive      → prop.fget._sensitive_config : dict

MetadataBuilder читает эти атрибуты, валидирует структурные инварианты
(например, ровно один summary-аспект у Action) и упаковывает всё в
ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌───────────────┐
    │  Декораторы   │   записывают временные атрибуты в класс/метод
    └──────┬────────┘
           │
           ▼
    ┌───────────────────┐
    │  MetadataBuilder  │   читает атрибуты, валидирует, собирает
    │  .build(cls)      │
    └──────┬────────────┘
           │
           ▼
    ┌────────────────────┐
    │   ClassMetadata    │   frozen-снимок, передаётся в GateCoordinator
    └────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. ЕДИНСТВЕННАЯ ТОЧКА СБОРКИ: весь код, который «знает» о формате временных
   атрибутов, сосредоточен здесь. Если формат атрибута изменится в декораторе,
   менять нужно только MetadataBuilder — а не десять мест в проекте.

2. ВАЛИДАЦИЯ СТРУКТУРЫ: builder проверяет структурные правила, которые
   невозможно проверить на уровне отдельного декоратора (например, что
   у Action есть ровно один summary-аспект).

3. ИДЕМПОТЕНТНОСТЬ: повторный вызов build(cls) для одного класса возвращает
   эквивалентный результат. Побочных эффектов нет.

4. НЕ МОДИФИЦИРУЕТ КЛАСС: builder только читает атрибуты. Он НЕ удаляет
   временные атрибуты и НЕ записывает ничего обратно в класс.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.Core.metadata_builder import MetadataBuilder

    # Сборка метаданных для класса действия:
    metadata = MetadataBuilder.build(CreateOrderAction)

    # Результат — frozen ClassMetadata:
    print(metadata.class_name)        # "test_full_flow.CreateOrderAction"
    print(metadata.dependencies)      # (DependencyInfo(...), DependencyInfo(...))
    print(metadata.get_summary_aspect())  # AspectMeta(method_name="build_result", ...)

    # Сборка метаданных для плагина:
    plugin_meta = MetadataBuilder.build(CounterPlugin)
    print(plugin_meta.subscriptions)  # (SubscriptionInfo(...),)
"""

from __future__ import annotations

from action_machine.Core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    ClassMetadata,
    RoleMeta,
    SensitiveFieldMeta,
)


class MetadataBuilder:
    """
    Статический сборщик ClassMetadata.

    Не создаёт экземпляров — все методы статические или классовые.
    Единственная публичная точка входа: MetadataBuilder.build(cls).

    Внутренние методы (_collect_*) разделены по типам метаданных для
    читаемости и упрощения тестирования.
    """

    # ─────────────────────────────────────────────────────────────────────
    # Публичный API
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def build(cls: type) -> ClassMetadata:
        """
        Собирает ClassMetadata из временных атрибутов класса.

        Аргументы:
            cls: класс (Action, Plugin или любой другой), метаданные
                 которого нужно собрать.

        Возвращает:
            ClassMetadata — иммутабельный снимок всех метаданных.

        Исключения:
            TypeError: если cls не является классом (type).
            ValueError: если нарушены структурные инварианты
                        (например, больше одного summary-аспекта).

        Пример:
            >>> metadata = MetadataBuilder.build(CreateOrderAction)
            >>> metadata.class_name
            'test_full_flow.CreateOrderAction'
        """
        if not isinstance(cls, type):
            raise TypeError(
                f"MetadataBuilder.build() ожидает класс (type), "
                f"получен {type(cls).__name__}: {cls!r}"
            )

        # Полное имя класса для идентификации
        class_name = _full_class_name(cls)

        # ── Сбор отдельных секций ──────────────────────────────────────
        role = _collect_role(cls)
        dependencies = _collect_dependencies(cls)
        connections = _collect_connections(cls)
        aspects = _collect_aspects(cls)
        checkers = _collect_checkers(cls)
        subscriptions = _collect_subscriptions(cls)
        sensitive_fields = _collect_sensitive_fields(cls)
        depends_bound = _collect_depends_bound(cls)

        # ── Структурная валидация ──────────────────────────────────────
        _validate_aspects(cls, aspects)
        _validate_checkers_belong_to_aspects(cls, checkers, aspects)

        # ── Сборка финального объекта ──────────────────────────────────
        return ClassMetadata(
            class_ref=cls,
            class_name=class_name,
            role=role,
            dependencies=tuple(dependencies),
            connections=tuple(connections),
            aspects=tuple(aspects),
            checkers=tuple(checkers),
            subscriptions=tuple(subscriptions),
            sensitive_fields=tuple(sensitive_fields),
            depends_bound=depends_bound,
        )


# ═════════════════════════════════════════════════════════════════════════════
# Внутренние функции сбора (private)
# ═════════════════════════════════════════════════════════════════════════════


def _full_class_name(cls: type) -> str:
    """
    Формирует полное имя класса: module.ClassName.

    Если модуль "__main__" или отсутствует, возвращает просто имя класса.

    Примеры:
        _full_class_name(CreateOrderAction) → "test_full_flow.CreateOrderAction"
        _full_class_name(PingAction)        → "test_full_flow.PingAction"
    """
    module = getattr(cls, "__module__", None)
    if module and module != "__main__":
        return f"{module}.{cls.__qualname__}"
    return cls.__qualname__


# ─────────────────────────────────────────────────────────────────────────────
# Роли
# ─────────────────────────────────────────────────────────────────────────────


def _collect_role(cls: type) -> RoleMeta | None:
    """
    Извлекает ролевые метаданные из cls._role_info.

    Декоратор @CheckRoles записывает в cls._role_info словарь:
        {"spec": str | list[str], "desc": str}

    Если _role_info отсутствует — возвращает None (роли не назначены).

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        RoleMeta или None.
    """
    role_info: dict | None = getattr(cls, "_role_info", None)
    if role_info is None:
        return None

    return RoleMeta(
        spec=role_info["spec"],
        description=role_info.get("desc", ""),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Зависимости
# ─────────────────────────────────────────────────────────────────────────────


def _collect_dependencies(cls: type) -> list:
    """
    Извлекает список DependencyInfo из cls._depends_info.

    Декоратор @depends записывает в cls._depends_info список объектов
    DependencyInfo(cls=..., description=...).

    Если _depends_info отсутствует — возвращает пустой список.

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        list[DependencyInfo] — список зависимостей в порядке объявления.
    """
    return list(getattr(cls, "_depends_info", []))


# ─────────────────────────────────────────────────────────────────────────────
# Соединения
# ─────────────────────────────────────────────────────────────────────────────


def _collect_connections(cls: type) -> list:
    """
    Извлекает список ConnectionInfo из cls._connection_info.

    Декоратор @connection записывает в cls._connection_info список объектов
    ConnectionInfo(cls=..., key=..., description=...).

    Если _connection_info отсутствует — возвращает пустой список.

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        list[ConnectionInfo] — список соединений в порядке объявления.
    """
    return list(getattr(cls, "_connection_info", []))


# ─────────────────────────────────────────────────────────────────────────────
# Аспекты
# ─────────────────────────────────────────────────────────────────────────────


def _collect_aspects(cls: type) -> list[AspectMeta]:
    """
    Сканирует методы класса и собирает AspectMeta из атрибута _new_aspect_meta.

    Декораторы @regular_aspect и @summary_aspect записывают в функцию:
        func._new_aspect_meta = {"type": "regular"|"summary", "description": "..."}

    Метод обходит MRO класса (method resolution order) начиная с самого класса,
    чтобы сохранить порядок объявления и учесть наследование.

    Порядок аспектов определяется порядком объявления в классе. Для Python 3.7+
    dict сохраняет порядок вставки, поэтому vars(cls) возвращает атрибуты
    в порядке объявления.

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        list[AspectMeta] — аспекты в порядке объявления.
    """
    aspects: list[AspectMeta] = []
    seen_names: set[str] = set()

    # Обходим MRO, но начинаем с самого класса. Это позволяет
    # дочернему классу переопределять аспекты родителя.
    for klass in cls.__mro__:
        # Пропускаем object и стандартные классы
        if klass is object:
            continue

        for attr_name, attr_value in vars(klass).items():
            # Пропускаем уже найденные (переопределённые в дочернем классе)
            if attr_name in seen_names:
                continue

            # Разворачиваем property → getter
            func = attr_value
            if isinstance(func, property) and func.fget is not None:
                func = func.fget

            # Проверяем наличие метаданных аспекта
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


def _collect_checkers(cls: type) -> list[CheckerMeta]:
    """
    Сканирует методы класса и собирает CheckerMeta из атрибута _checker_meta.

    Декораторы чекеров (например, @StringFieldChecker) записывают в функцию:
        func._checker_meta = [
            {"checker_class": StringFieldChecker, "field_name": "txn_id",
             "description": "...", "required": True, ...},
            ...  # может быть несколько чекеров на одном методе
        ]

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        list[CheckerMeta] — чекеры в порядке обнаружения.
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


def _collect_subscriptions(cls: type) -> list:
    """
    Сканирует методы класса и собирает SubscriptionInfo из атрибута
    _on_subscriptions.

    Декоратор @on записывает в функцию:
        func._on_subscriptions = [SubscriptionInfo(...), ...]

    Один метод может иметь несколько подписок (несколько @on).

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        list[SubscriptionInfo] — подписки в порядке обнаружения.
    """
    subscriptions: list = []
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


def _collect_sensitive_fields(cls: type) -> list[SensitiveFieldMeta]:
    """
    Сканирует properties класса и собирает SensitiveFieldMeta из атрибута
    _sensitive_config.

    Декоратор @sensitive записывает в getter property:
        func._sensitive_config = {
            "enabled": True,
            "max_chars": 3,
            "char": "*",
            "max_percent": 50
        }

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        list[SensitiveFieldMeta] — чувствительные поля в порядке обнаружения.
    """
    sensitive: list[SensitiveFieldMeta] = []
    seen_names: set[str] = set()

    for klass in cls.__mro__:
        if klass is object:
            continue

        for attr_name, attr_value in vars(klass).items():
            if attr_name in seen_names:
                continue

            # @sensitive работает только с property
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
                    config=dict(config),  # копия для безопасности
                ))
                seen_names.add(attr_name)

    return sensitive


# ─────────────────────────────────────────────────────────────────────────────
# Ограничитель типа зависимостей
# ─────────────────────────────────────────────────────────────────────────────


def _collect_depends_bound(cls: type) -> type:
    """
    Извлекает bound-тип из DependencyGateHost[T].

    DependencyGateHost.__init_subclass__ записывает в класс:
        cls._depends_bound = <тип T>

    Если _depends_bound отсутствует — возвращает object (разрешены любые
    зависимости).

    Аргументы:
        cls: класс для анализа.

    Возвращает:
        type — bound-тип зависимостей.
    """
    return getattr(cls, "_depends_bound", object)


# ═════════════════════════════════════════════════════════════════════════════
# Валидация структуры
# ═════════════════════════════════════════════════════════════════════════════


def _validate_aspects(cls: type, aspects: list[AspectMeta]) -> None:
    """
    Проверяет структурные инварианты аспектов.

    Правила:
    1. Не более одного summary-аспекта.
    2. Если есть regular-аспекты, должен быть ровно один summary-аспект
       (действие без summary не может вернуть результат).
    3. Summary-аспект должен быть объявлен последним.

    Исключение из правила 2: классы без аспектов вообще (например, Plugin)
    — это нормально, правило применяется только если есть хотя бы один аспект.

    Аргументы:
        cls: класс (для сообщений об ошибках).
        aspects: собранные аспекты.

    Исключения:
        ValueError: при нарушении инвариантов.
    """
    if not aspects:
        return  # Нет аспектов — нечего проверять (Plugin, утилитарный класс)

    summaries = [a for a in aspects if a.aspect_type == "summary"]
    regulars = [a for a in aspects if a.aspect_type == "regular"]

    # Правило 1: не более одного summary
    if len(summaries) > 1:
        names = ", ".join(s.method_name for s in summaries)
        raise ValueError(
            f"Класс {cls.__name__} содержит {len(summaries)} summary-аспектов "
            f"({names}), допускается не более одного."
        )

    # Правило 2: если есть regular, должен быть summary
    if regulars and not summaries:
        raise ValueError(
            f"Класс {cls.__name__} содержит {len(regulars)} regular-аспект(ов), "
            f"но не имеет summary-аспекта. Действие должно завершаться "
            f"summary-аспектом, возвращающим Result."
        )

    # Правило 3: summary должен быть последним
    if summaries and aspects[-1].aspect_type != "summary":
        raise ValueError(
            f"Класс {cls.__name__}: summary-аспект '{summaries[0].method_name}' "
            f"должен быть объявлен последним методом среди аспектов. "
            f"Сейчас последний аспект — '{aspects[-1].method_name}' "
            f"(тип: {aspects[-1].aspect_type})."
        )


def _validate_checkers_belong_to_aspects(
    cls: type,
    checkers: list[CheckerMeta],
    aspects: list[AspectMeta],
) -> None:
    """
    Проверяет, что каждый чекер привязан к существующему аспекту.

    Чекер декорирует метод, который также должен быть аспектом. Если
    метод с чекером не является аспектом — это ошибка конфигурации
    (чекер не будет вызван).

    Аргументы:
        cls: класс (для сообщений об ошибках).
        checkers: собранные чекеры.
        aspects: собранные аспекты.

    Исключения:
        ValueError: если чекер привязан к несуществующему аспекту.
    """
    aspect_names = {a.method_name for a in aspects}

    for checker in checkers:
        if checker.method_name not in aspect_names:
            raise ValueError(
                f"Класс {cls.__name__}: чекер '{checker.checker_class.__name__}' "
                f"для поля '{checker.field_name}' привязан к методу "
                f"'{checker.method_name}', который не является аспектом. "
                f"Чекеры можно применять только к методам с @regular_aspect "
                f"или @summary_aspect."
            )
