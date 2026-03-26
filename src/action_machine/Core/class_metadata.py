# src/action_machine/core/class_metadata.py
"""
Модуль: ClassMetadata — иммутабельный снимок метаданных класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ClassMetadata — это замороженный (frozen) объект, который хранит ВСЕ метаданные,
собранные декораторами с одного класса (Action или Plugin). После создания
ClassMetadata нельзя изменить — это гарантия, что ни один компонент системы
не сможет случайно мутировать описание класса во время выполнения.

Каждый декоратор при определении класса записывает временные атрибуты
(_depends_info, _role_info, _connection_info, _new_aspect_meta, _on_subscriptions,
_sensitive_config, _checker_meta). MetadataBuilder собирает эти атрибуты
и конструирует один экземпляр ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌───────────────┐      ┌───────────────────┐      ┌────────────────────┐
    │  Декораторы   │ ──▶  │  MetadataBuilder  │ ──▶  │   ClassMetadata    │
    │  (@depends,   │      │  (собирает temp   │      │   (frozen снимок)  │
    │   @CheckRoles │      │   атрибуты)       │      │                    │
    │   и т.д.)     │      └───────────────────┘      └────────────────────┘
    └───────────────┘                                          │
                                                              ▼
                                                   ┌────────────────────┐
                                                   │  GateCoordinator   │
                                                   │  (кеширует и       │
                                                   │   предоставляет    │
                                                   │   доступ)          │
                                                   └────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. ИММУТАБЕЛЬНОСТЬ: после создания ни одно поле изменить нельзя.
   Все коллекции хранятся как tuple (не list), все гейты заморожены.

2. ПОЛНОТА: ClassMetadata содержит ВСЮ информацию, необходимую для выполнения
   действия — роли, зависимости, соединения, аспекты, чекеры, подписки,
   чувствительные поля.

3. ЕДИНАЯ ТОЧКА ДОСТУПА: вместо обращения к cls._depends_info, cls._role_info
   и прочим «сырым» атрибутам, любой потребитель берёт ClassMetadata из
   GateCoordinator и работает только с ним.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Получение метаданных класса через координатор:
    metadata = gate_coordinator.get(CreateOrderAction)

    # Доступ к зависимостям:
    for dep in metadata.dependencies:
        print(f"  {dep.cls.__name__}: {dep.description}")

    # Доступ к ролям:
    if metadata.has_role():
        print(f"Роли: {metadata.role.spec}")

    # Доступ к аспектам:
    for aspect in metadata.aspects:
        print(f"  [{aspect.aspect_type}] {aspect.method_name}: {aspect.description}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные frozen-датаклассы для хранения собранных метаданных
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AspectMeta:
    """
    Метаданные одного аспекта (regular или summary), собранные из
    атрибута _new_aspect_meta, который устанавливает декоратор
    @regular_aspect или @summary_aspect.

    Поля:
        method_name : str
            Имя метода, на котором стоит декоратор (например, "process_payment").
        aspect_type : str
            Тип аспекта: "regular" или "summary".
        description : str
            Человекочитаемое описание шага (передаётся в декоратор).
        method_ref  : Any
            Ссылка на сам метод (функцию). Используется для вызова
            в ActionProductMachine при выполнении пайплайна.
    """
    method_name: str
    aspect_type: str
    description: str
    method_ref: Any


@dataclass(frozen=True)
class CheckerMeta:
    """
    Метаданные одного чекера, собранные из атрибута _checker_meta,
    который устанавливает декоратор чекера (например, @ResultStringChecker).

    Поля:
        method_name    : str
            Имя метода, на котором стоит чекер.
        checker_class  : type
            Класс чекера (например, ResultStringChecker).
        field_name     : str
            Имя поля, которое проверяет чекер.
        description    : str
            Описание проверки.
        required       : bool
            Обязательность поля.
        extra_params   : dict[str, Any]
            Дополнительные параметры чекера (min_length, max_length и т.д.).
    """
    method_name: str
    checker_class: type
    field_name: str
    description: str
    required: bool
    extra_params: dict[str, Any]


@dataclass(frozen=True)
class SensitiveFieldMeta:
    """
    Метаданные одного чувствительного поля, собранные из атрибута
    _sensitive_config, который устанавливает декоратор @sensitive.

    Поля:
        property_name : str
            Имя свойства (property), помеченного @sensitive.
        config        : dict[str, Any]
            Конфигурация маскирования:
            - enabled (bool): включено ли маскирование.
            - max_chars (int): максимум видимых символов.
            - char (str): символ замены.
            - max_percent (int): максимальный процент видимых символов.
    """
    property_name: str
    config: dict[str, Any]


@dataclass(frozen=True)
class RoleMeta:
    """
    Метаданные ролей класса, собранные из атрибута _role_info,
    который устанавливает декоратор @CheckRoles.

    Поля:
        spec : str | list[str]
            Спецификация ролей:
            - строка "__NONE__" — доступ без аутентификации.
            - строка "__ANY__" — любая аутентифицированная роль.
            - строка "admin" — конкретная роль.
            - список ["admin", "manager"] — одна из перечисленных ролей.
        description : str
            Описание назначения ролевого ограничения.
    """
    spec: Any  # str | list[str]
    description: str


# ─────────────────────────────────────────────────────────────────────────────
# Основной класс ClassMetadata
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ClassMetadata:
    """
    Иммутабельный снимок всех метаданных, собранных декораторами с одного класса.

    После создания ни одно поле изменить нельзя. Все коллекции — tuple,
    все вложенные объекты — frozen dataclass.

    Поля:
        class_ref : type
            Ссылка на сам класс (например, CreateOrderAction).

        class_name : str
            Полное имя класса (module.ClassName), используется для логирования
            и идентификации в координаторе.

        role : RoleMeta | None
            Метаданные ролей (от @CheckRoles). None если декоратор не применялся.

        dependencies : tuple[Any, ...]
            Кортеж зависимостей (от @depends). Пустой tuple если нет зависимостей.

        connections : tuple[Any, ...]
            Кортеж соединений (от @connection). Пустой tuple если нет соединений.

        aspects : tuple[AspectMeta, ...]
            Кортеж аспектов (от @regular_aspect и @summary_aspect), в порядке
            объявления в классе. Последний элемент — summary (если есть).

        checkers : tuple[CheckerMeta, ...]
            Кортеж чекеров (от @ResultStringChecker и других). Привязаны
            к конкретным аспектам (по method_name).

        subscriptions : tuple[Any, ...]
            Кортеж подписок (от @on). Актуально только для Plugin-классов.

        sensitive_fields : tuple[SensitiveFieldMeta, ...]
            Кортеж чувствительных полей (от @sensitive). Актуально для любых
            классов, использующих маскирование в логах.

        depends_bound : type
            Тип-ограничитель из DependencyGateHost[T]. По умолчанию object.
            Используется для документирования и возможной рантайм-валидации.
    """

    # ── Идентификация ──────────────────────────────────────────────────────
    class_ref: type
    class_name: str

    # ── Роли ───────────────────────────────────────────────────────────────
    role: RoleMeta | None = None

    # ── Зависимости ────────────────────────────────────────────────────────
    dependencies: tuple[Any, ...] = field(default_factory=tuple)

    # ── Соединения ─────────────────────────────────────────────────────────
    connections: tuple[Any, ...] = field(default_factory=tuple)

    # ── Аспекты (пайплайн) ─────────────────────────────────────────────────
    aspects: tuple[AspectMeta, ...] = field(default_factory=tuple)

    # ── Чекеры ─────────────────────────────────────────────────────────────
    checkers: tuple[CheckerMeta, ...] = field(default_factory=tuple)

    # ── Подписки (плагины) ─────────────────────────────────────────────────
    subscriptions: tuple[Any, ...] = field(default_factory=tuple)

    # ── Чувствительные поля ────────────────────────────────────────────────
    sensitive_fields: tuple[SensitiveFieldMeta, ...] = field(default_factory=tuple)

    # ── Ограничитель типа зависимостей ─────────────────────────────────────
    depends_bound: type = object

    # ── Удобные методы доступа ─────────────────────────────────────────────

    def has_role(self) -> bool:
        """Назначены ли ролевые ограничения для класса."""
        return self.role is not None

    def has_dependencies(self) -> bool:
        """Объявлены ли зависимости (@depends)."""
        return len(self.dependencies) > 0

    def has_connections(self) -> bool:
        """Объявлены ли соединения (@connection)."""
        return len(self.connections) > 0

    def has_aspects(self) -> bool:
        """Есть ли аспекты (regular или summary)."""
        return len(self.aspects) > 0

    def has_checkers(self) -> bool:
        """Привязаны ли чекеры к аспектам."""
        return len(self.checkers) > 0

    def has_subscriptions(self) -> bool:
        """Есть ли подписки на события (@on). Актуально для плагинов."""
        return len(self.subscriptions) > 0

    def has_sensitive_fields(self) -> bool:
        """Есть ли поля, помеченные @sensitive."""
        return len(self.sensitive_fields) > 0

    def get_regular_aspects(self) -> tuple[AspectMeta, ...]:
        """Возвращает только regular-аспекты, в порядке объявления."""
        return tuple(a for a in self.aspects if a.aspect_type == "regular")

    def get_summary_aspect(self) -> AspectMeta | None:
        """
        Возвращает summary-аспект или None.
        У действия может быть только один summary-аспект.
        """
        summaries = [a for a in self.aspects if a.aspect_type == "summary"]
        return summaries[0] if summaries else None

    def get_checkers_for_aspect(self, method_name: str) -> tuple[CheckerMeta, ...]:
        """
        Возвращает чекеры, привязанные к конкретному аспекту (по имени метода).

        Аргументы:
            method_name: имя метода аспекта (например, "process_payment").

        Возвращает:
            Кортеж CheckerMeta для указанного метода.
        """
        return tuple(c for c in self.checkers if c.method_name == method_name)

    def get_dependency_classes(self) -> tuple[type, ...]:
        """Возвращает кортеж классов всех зависимостей."""
        return tuple(d.cls for d in self.dependencies)

    def get_connection_keys(self) -> tuple[str, ...]:
        """Возвращает кортеж ключей всех соединений."""
        return tuple(c.key for c in self.connections)

    def __repr__(self) -> str:
        """Компактное строковое представление для отладки."""
        parts = [f"ClassMetadata({self.class_name}"]
        if self.has_role() and self.role is not None:
            parts.append(f"  role={self.role.spec!r}")
        if self.has_dependencies():
            dep_names = ", ".join(d.cls.__name__ for d in self.dependencies)
            parts.append(f"  deps=[{dep_names}]")
        if self.has_connections():
            conn_keys = ", ".join(c.key for c in self.connections)
            parts.append(f"  conns=[{conn_keys}]")
        if self.has_aspects():
            aspect_info = ", ".join(
                f"{a.aspect_type}:{a.method_name}" for a in self.aspects
            )
            parts.append(f"  aspects=[{aspect_info}]")
        if self.has_checkers():
            parts.append(f"  checkers={len(self.checkers)}")
        if self.has_subscriptions():
            parts.append(f"  subscriptions={len(self.subscriptions)}")
        if self.has_sensitive_fields():
            sf_names = ", ".join(sf.property_name for sf in self.sensitive_fields)
            parts.append(f"  sensitive=[{sf_names}]")
        parts.append(")")
        return "\n".join(parts)
