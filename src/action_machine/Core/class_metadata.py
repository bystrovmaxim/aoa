# src/action_machine/core/class_metadata.py
"""
Модуль: ClassMetadata — иммутабельный снимок метаданных класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ClassMetadata — это замороженный (frozen) объект, который хранит ВСЕ метаданные,
собранные декораторами с одного класса (Action, Plugin, ResourceManager).
После создания ClassMetadata нельзя изменить — это гарантия, что ни один
компонент системы не сможет случайно мутировать описание класса во время
выполнения.

Каждый декоратор при определении класса записывает временные атрибуты
(_depends_info, _role_info, _connection_info, _new_aspect_meta, _on_subscriptions,
_sensitive_config, _checker_meta, _meta_info). MetadataBuilder собирает эти
атрибуты и конструирует один экземпляр ClassMetadata.

Дополнительно MetadataBuilder извлекает generic-параметры P и R из
BaseAction[P, R] и собирает описания полей Params и Result из pydantic
model_fields.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌───────────────┐      ┌───────────────────┐      ┌────────────────────┐
    │  Декораторы   │ ──▶  │  MetadataBuilder  │ ──▶  │   ClassMetadata    │
    │  (@depends,   │      │  (собирает temp   │      │   (frozen снимок)  │
    │   @CheckRoles │      │   атрибуты и      │      │                    │
    │   @meta,      │      │   pydantic fields) │      └────────────────────┘
    │   Field(...)) │      └───────────────────┘
    └───────────────┘

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ МЕТАДАННЫХ
═══════════════════════════════════════════════════════════════════════════════

- MetaInfo — описание и доменная принадлежность (@meta).
- RoleMeta — спецификация ролей (@CheckRoles). Содержит только spec.
- AspectMeta — аспекты конвейера (@regular_aspect, @summary_aspect).
- CheckerMeta — чекеры полей результатов аспектов. Содержит класс чекера,
  имя поля, обязательность и дополнительные параметры (без описания).
- SensitiveFieldMeta — чувствительные поля (@sensitive).
- FieldDescriptionMeta — описание поля Params или Result (pydantic Field).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    metadata = gate_coordinator.get(CreateOrderAction)

    # Описание и домен:
    metadata.meta.description          # → "Создание нового заказа"
    metadata.meta.domain.name          # → "orders"

    # Роли:
    metadata.role.spec                 # → "manager"

    # Поля параметров:
    for f in metadata.params_fields:
        print(f"{f.field_name}: {f.description}")

    # Чекеры:
    for c in metadata.checkers:
        print(f"{c.field_name}: required={c.required}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные frozen-датаклассы для хранения собранных метаданных
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MetaInfo:
    """
    Метаданные класса, собранные из атрибута _meta_info,
    который устанавливает декоратор @meta.

    Поля:
        description : str
            Текстовое описание класса. Непустая строка.
        domain : type[BaseDomain] | None
            Класс бизнес-домена. None если не указан.
    """
    description: str
    domain: Any = None


@dataclass(frozen=True)
class AspectMeta:
    """
    Метаданные одного аспекта (regular или summary).

    Поля:
        method_name : str — имя метода.
        aspect_type : str — "regular" или "summary".
        description : str — описание шага.
        method_ref  : Any — ссылка на функцию.
    """
    method_name: str
    aspect_type: str
    description: str
    method_ref: Any


@dataclass(frozen=True)
class CheckerMeta:
    """
    Метаданные одного чекера.

    Поля:
        method_name    : str — имя метода-аспекта, к которому привязан чекер.
        checker_class  : type — класс чекера (ResultStringChecker и т.д.).
        field_name     : str — имя проверяемого поля в словаре результата аспекта.
        required       : bool — обязательность поля.
        extra_params   : dict[str, Any] — дополнительные параметры чекера
                         (min_length, max_length, min_value, max_value и т.д.).
    """
    method_name: str
    checker_class: type
    field_name: str
    required: bool
    extra_params: dict[str, Any]


@dataclass(frozen=True)
class SensitiveFieldMeta:
    """
    Метаданные одного чувствительного поля (@sensitive на property).

    Поля:
        property_name : str — имя свойства.
        config        : dict[str, Any] — конфигурация маскирования.
    """
    property_name: str
    config: dict[str, Any]


@dataclass(frozen=True)
class RoleMeta:
    """
    Метаданные ролей класса (@CheckRoles).

    Содержит только спецификацию ролей — строку, список строк
    или специальное значение (ROLE_NONE, ROLE_ANY).

    Поля:
        spec : str | list[str] — спецификация ролей.
    """
    spec: Any


@dataclass(frozen=True)
class FieldDescriptionMeta:
    """
    Метаданные одного поля Params или Result, собранные из pydantic
    model_fields.

    Содержит описание поля, его тип, ограничения (constraints),
    примеры и информацию об обязательности. Используется адаптерами
    для генерации OpenAPI schema, JSON Schema, документации MCP tools.

    Поля:
        field_name : str
            Имя поля (например, "user_id", "amount").

        field_type : str
            Строковое представление типа поля (например, "str", "float",
            "str | None"). Строка, а не type, потому что аннотации могут
            содержать Union, Optional и другие формы, не являющиеся type.

        description : str
            Текстовое описание поля из Field(description="...").
            Непустая строка — обязательность контролируется
            DescribedFieldsGateHost.

        examples : tuple[Any, ...] | None
            Примеры значений из Field(examples=[...]). None если
            примеры не указаны.

        constraints : dict[str, Any]
            Ограничения из pydantic Field: gt, ge, lt, le, min_length,
            max_length, pattern и другие. Пустой dict если ограничений нет.

        required : bool
            True если поле не имеет значения по умолчанию
            (обязательно при создании экземпляра).

        default : Any
            Значение по умолчанию. PydanticUndefined если поле обязательно.
    """
    field_name: str
    field_type: str
    description: str
    examples: tuple[Any, ...] | None
    constraints: dict[str, Any]
    required: bool
    default: Any


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
        class_ref : type — ссылка на класс.
        class_name : str — полное имя класса (module.ClassName).
        meta : MetaInfo | None — описание и домен (@meta).
        role : RoleMeta | None — спецификация ролей (@CheckRoles).
        dependencies : tuple[Any, ...] — зависимости (@depends).
        connections : tuple[Any, ...] — соединения (@connection).
        aspects : tuple[AspectMeta, ...] — аспекты конвейера.
        checkers : tuple[CheckerMeta, ...] — чекеры полей аспектов.
        subscriptions : tuple[Any, ...] — подписки плагинов (@on).
        sensitive_fields : tuple[SensitiveFieldMeta, ...] — чувствительные поля.
        depends_bound : type — ограничитель типа зависимостей.
        params_fields : tuple[FieldDescriptionMeta, ...] — описания полей Params.
        result_fields : tuple[FieldDescriptionMeta, ...] — описания полей Result.
    """

    # ── Идентификация ──────────────────────────────────────────────────────
    class_ref: type
    class_name: str

    # ── Описание и домен ───────────────────────────────────────────────────
    meta: MetaInfo | None = None

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

    # ── Описания полей Params ──────────────────────────────────────────────
    params_fields: tuple[FieldDescriptionMeta, ...] = field(default_factory=tuple)

    # ── Описания полей Result ──────────────────────────────────────────────
    result_fields: tuple[FieldDescriptionMeta, ...] = field(default_factory=tuple)

    # ── Удобные методы доступа ─────────────────────────────────────────────

    def has_meta(self) -> bool:
        """Есть ли описание (@meta) у класса."""
        return self.meta is not None

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
        """Есть ли подписки на события (@on)."""
        return len(self.subscriptions) > 0

    def has_sensitive_fields(self) -> bool:
        """Есть ли поля, помеченные @sensitive."""
        return len(self.sensitive_fields) > 0

    def has_params_fields(self) -> bool:
        """Есть ли описания полей Params."""
        return len(self.params_fields) > 0

    def has_result_fields(self) -> bool:
        """Есть ли описания полей Result."""
        return len(self.result_fields) > 0

    def get_regular_aspects(self) -> tuple[AspectMeta, ...]:
        """Возвращает только regular-аспекты, в порядке объявления."""
        return tuple(a for a in self.aspects if a.aspect_type == "regular")

    def get_summary_aspect(self) -> AspectMeta | None:
        """Возвращает summary-аспект или None."""
        summaries = [a for a in self.aspects if a.aspect_type == "summary"]
        return summaries[0] if summaries else None

    def get_checkers_for_aspect(self, method_name: str) -> tuple[CheckerMeta, ...]:
        """Возвращает чекеры, привязанные к конкретному аспекту."""
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
        if self.has_meta() and self.meta is not None:
            domain_str = self.meta.domain.name if self.meta.domain else "None"
            parts.append(f"  meta='{self.meta.description}' domain={domain_str}")
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
        if self.has_params_fields():
            pf_names = ", ".join(f.field_name for f in self.params_fields)
            parts.append(f"  params_fields=[{pf_names}]")
        if self.has_result_fields():
            rf_names = ", ".join(f.field_name for f in self.result_fields)
            parts.append(f"  result_fields=[{rf_names}]")
        parts.append(")")
        return "\n".join(parts)
