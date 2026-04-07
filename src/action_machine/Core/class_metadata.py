# src/action_machine/core/class_metadata.py
"""
Модуль: ClassMetadata — иммутабельный снимок метаданных класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ClassMetadata — frozen объект, хранящий ВСЕ метаданные, собранные
декораторами с одного класса (Action, Plugin, ResourceManager, Entity).
После создания ClassMetadata нельзя изменить.

Каждый декоратор при определении класса записывает временные атрибуты.
MetadataBuilder собирает эти атрибуты и конструирует один экземпляр
ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ МЕТАДАННЫХ
═══════════════════════════════════════════════════════════════════════════════

Action / Plugin / ResourceManager:
- MetaInfo — описание и доменная принадлежность (@meta).
- RoleMeta — спецификация ролей (@check_roles).
- AspectMeta — аспекты конвейера (@regular_aspect, @summary_aspect).
- CheckerMeta — чекеры полей результатов аспектов.
- OnErrorMeta — обработчики ошибок (@on_error).
- CompensatorMeta — компенсаторы для regular-аспектов (@compensate).
- SensitiveFieldMeta — чувствительные поля (@sensitive).
- FieldDescriptionMeta — описание поля Params или Result.

Entity (@entity):
- EntityInfo — описание и доменная принадлежность сущности (@entity).
- EntityFieldInfo — метаданные простого поля сущности.
- EntityRelationInfo — метаданные связи между сущностями.
- EntityLifecycleInfo — метаданные поля Lifecycle сущности.

═══════════════════════════════════════════════════════════════════════════════
ENTITY-МЕТАДАННЫЕ
═══════════════════════════════════════════════════════════════════════════════

Сущности доменной модели (@entity) регистрируются через тот же
MetadataBuilder.build() и GateCoordinator.get(), что и Action.
Декоратор @entity записывает _entity_info на класс, коллекторы
читают model_fields и атрибуты класса (Lifecycle), MetadataBuilder
конструирует ClassMetadata с заполненными entity-полями.

EntityInfo — аналог MetaInfo для сущностей. Содержит description
и domain из @entity(description="...", domain=...).

EntityFieldInfo — метаданные одного простого поля сущности (не связи,
не Lifecycle). Содержит имя, тип, описание, обязательность, constraints.

EntityRelationInfo — метаданные одной связи между сущностями.
Содержит контейнер, тип владения, целевую сущность, Inverse/NoInverse.

EntityLifecycleInfo — метаданные одного поля Lifecycle. Содержит имя
поля, ссылку на _template специализированного класса, количество
состояний.

═══════════════════════════════════════════════════════════════════════════════
КОНТЕКСТНЫЕ ЗАВИСИМОСТИ АСПЕКТОВ, ОБРАБОТЧИКОВ И КОМПЕНСАТОРОВ
═══════════════════════════════════════════════════════════════════════════════

Поле context_keys в AspectMeta, OnErrorMeta и CompensatorMeta содержит
frozenset строковых ключей (dot-path), объявленных через @context_requires.

═══════════════════════════════════════════════════════════════════════════════
КОМПЕНСАЦИЯ (SAGA)
═══════════════════════════════════════════════════════════════════════════════

CompensatorMeta описывает метод-компенсатор, объявленный декоратором
@compensate(target_aspect_name, description). Компенсатор привязан к одному
regular-аспекту по строковому имени (target_aspect_name).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Action:
    metadata = gate_coordinator.get(CreateOrderAction)
    metadata.meta.description          # → "Создание нового заказа"
    metadata.aspects[0].context_keys   # → frozenset({"user.user_id"})

    # Entity:
    metadata = gate_coordinator.get(OrderEntity)
    metadata.entity_info.description   # → "Заказ клиента"
    metadata.entity_fields[0].field_name  # → "id"
    metadata.entity_lifecycles[0].field_name  # → "lifecycle"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Action / Plugin / ResourceManager метаданные
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MetaInfo:
    """
    Метаданные класса из @meta(description="...", domain=...).

    Поля:
        description : str — текстовое описание.
        domain : type[BaseDomain] | None — класс бизнес-домена.
    """

    description: str
    domain: Any = None


@dataclass(frozen=True)
class AspectMeta:
    """
    Метаданные одного аспекта (regular или summary).

    Поля:
        method_name  : str — имя метода.
        aspect_type  : str — "regular" или "summary".
        description  : str — описание шага.
        method_ref   : Any — ссылка на функцию.
        context_keys : frozenset[str] — ключи контекста из @context_requires.
    """

    method_name: str
    aspect_type: str
    description: str
    method_ref: Any
    context_keys: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CheckerMeta:
    """
    Метаданные одного чекера.

    Поля:
        method_name   : str — имя метода-аспекта.
        checker_class : type — класс чекера.
        field_name    : str — имя проверяемого поля.
        required      : bool — обязательность.
        extra_params  : dict[str, Any] — дополнительные параметры.
    """

    method_name: str
    checker_class: type
    field_name: str
    required: bool
    extra_params: dict[str, Any]


@dataclass(frozen=True)
class OnErrorMeta:
    """
    Метаданные одного обработчика ошибок (@on_error).

    Поля:
        method_name     : str — имя метода.
        exception_types : tuple[type[Exception], ...] — перехватываемые типы.
        description     : str — описание обработчика.
        method_ref      : Any — ссылка на функцию.
        context_keys    : frozenset[str] — ключи контекста.
    """

    method_name: str
    exception_types: tuple[type[Exception], ...]
    description: str
    method_ref: Any
    context_keys: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CompensatorMeta:
    """
    Метаданные одного компенсатора (@compensate).

    Поля:
        method_name        : str — имя метода-компенсатора.
        target_aspect_name : str — имя regular-аспекта.
        description        : str — описание действия компенсатора.
        method_ref         : Any — ссылка на функцию.
        context_keys       : frozenset[str] — ключи контекста.
    """

    method_name: str
    target_aspect_name: str
    description: str
    method_ref: Any
    context_keys: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SensitiveFieldMeta:
    """
    Метаданные одного чувствительного поля (@sensitive).

    Поля:
        property_name : str — имя свойства.
        config        : dict[str, Any] — конфигурация маскирования.
    """

    property_name: str
    config: dict[str, Any]


@dataclass(frozen=True)
class RoleMeta:
    """
    Метаданные ролей класса (@check_roles).

    Поля:
        spec : Any — спецификация ролей (строка, список, ROLE_NONE, ROLE_ANY).
    """

    spec: Any


@dataclass(frozen=True)
class FieldDescriptionMeta:
    """
    Метаданные одного поля Params или Result из pydantic model_fields.

    Поля:
        field_name  : str — имя поля.
        field_type  : str — строковое представление типа.
        description : str — описание из Field(description="...").
        examples    : tuple[Any, ...] | None — примеры значений.
        constraints : dict[str, Any] — ограничения (ge, le, min_length...).
        required    : bool — обязательность.
        default     : Any — значение по умолчанию.
    """

    field_name: str
    field_type: str
    description: str
    examples: tuple[Any, ...] | None
    constraints: dict[str, Any]
    required: bool
    default: Any


# ─────────────────────────────────────────────────────────────────────────────
# Entity метаданные (@entity)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EntityInfo:
    """
    Метаданные сущности из @entity(description="...", domain=...).

    Аналог MetaInfo для Action. Содержит описание и домен сущности.
    Записывается декоратором @entity в cls._entity_info, читается
    коллектором collect_entity_info().

    Поля:
        description : str — текстовое описание сущности.
        domain : type[BaseDomain] | None — класс бизнес-домена.
    """

    description: str
    domain: Any = None


@dataclass(frozen=True)
class EntityFieldInfo:
    """
    Метаданные одного простого поля сущности (не связи, не Lifecycle).

    Собирается из pydantic model_fields класса сущности. Аналог
    FieldDescriptionMeta для Params/Result.

    Поля:
        field_name  : str — имя поля ("id", "amount", "status").
        field_type  : str — строковое представление типа ("str", "float").
        description : str — описание из Field(description="...").
        required    : bool — True если нет default.
        default     : Any — значение по умолчанию.
        constraints : dict[str, Any] — ограничения (ge, le, min_length...).
        deprecated  : bool — True если помечено deprecated.
    """

    field_name: str
    field_type: str
    description: str
    required: bool
    default: Any
    constraints: dict[str, Any] = field(default_factory=dict)
    deprecated: bool = False


@dataclass(frozen=True)
class EntityRelationInfo:
    """
    Метаданные одной связи между сущностями.

    Собирается из Annotated-аннотаций полей сущности. Коллектор
    анализирует аннотацию, извлекает контейнер связи (CompositeOne,
    AssociationMany...), маркер Inverse/NoInverse и описание из Rel.

    Поля:
        field_name      : str — имя поля связи ("customer", "items").
        container_class : type — класс контейнера (AssociationOne и т.д.).
        relation_type   : str — тип владения ("composition", "aggregation", "association").
        target_entity   : type — класс целевой сущности.
        cardinality     : str — "one" или "many".
        description     : str — описание из Rel(description="...").
        has_inverse     : bool — True если Inverse, False если NoInverse.
        inverse_entity  : type | None — класс обратной стороны.
        inverse_field   : str | None — имя поля обратной стороны.
        deprecated      : bool — True если deprecated.
    """

    field_name: str
    container_class: type
    relation_type: str
    target_entity: type
    cardinality: str
    description: str
    has_inverse: bool
    inverse_entity: type | None = None
    inverse_field: str | None = None
    deprecated: bool = False


@dataclass(frozen=True)
class EntityLifecycleInfo:
    """
    Метаданные одного поля Lifecycle сущности.

    Lifecycle — обычное pydantic-поле сущности (OrderLifecycle | None).
    Каждый экземпляр хранит своё текущее состояние в lifecycle.current_state.
    Специализированный класс (OrderLifecycle) содержит _template с графом
    состояний, который координатор проверяет при старте (8 правил).

    Доступ к текущему состоянию:
        order.lifecycle                    # → OrderLifecycle или None
        order.lifecycle.current_state      # → "new"
        order.lifecycle.can_transition("confirmed")  # → True
        order.lifecycle.available_transitions        # → {"confirmed", "cancelled"}
        order.lifecycle.is_initial         # → True
        order.lifecycle.is_final           # → False

    Переход состояния (frozen-сущность):
        new_lc = order.lifecycle.transition("confirmed")
        confirmed_order = order.model_copy(update={"lifecycle": new_lc})

    Поля:
        field_name      : str — имя pydantic-поля ("lifecycle", "payment").
        lifecycle_class : type — специализированный класс (OrderLifecycle).
        template_ref    : Lifecycle — объект _template с графом состояний.
        state_count     : int — количество состояний в графе.
        initial_count   : int — количество начальных состояний.
        final_count     : int — количество финальных состояний.
    """

    field_name: str
    lifecycle_class: type
    template_ref: Any  # Lifecycle (не импортируем для избежания циклов)
    state_count: int
    initial_count: int
    final_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Основной класс ClassMetadata
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ClassMetadata:
    """
    Иммутабельный снимок всех метаданных, собранных декораторами с одного класса.

    Используется для Action, Plugin, ResourceManager и Entity.
    После создания ни одно поле изменить нельзя. Все коллекции — tuple.

    Поля Action / Plugin / ResourceManager:
        class_ref, class_name, meta, role, dependencies, connections,
        aspects, checkers, error_handlers, compensators, subscriptions,
        sensitive_fields, depends_bound, params_fields, result_fields.

    Поля Entity (@entity):
        entity_info       — описание и домен из @entity.
        entity_fields     — простые поля сущности.
        entity_relations  — связи между сущностями.
        entity_lifecycles — поля Lifecycle.
    """

    # ── Идентификация ──────────────────────────────────────────────────────
    class_ref: type
    class_name: str

    # ── Описание и домен (Action) ─────────────────────────────────────────
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

    # ── Обработчики ошибок ─────────────────────────────────────────────────
    error_handlers: tuple[OnErrorMeta, ...] = field(default_factory=tuple)

    # ── Компенсаторы ───────────────────────────────────────────────────────
    compensators: tuple[CompensatorMeta, ...] = field(default_factory=tuple)

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

    # ── Entity: описание и домен (@entity) ─────────────────────────────────
    entity_info: EntityInfo | None = None

    # ── Entity: простые поля ───────────────────────────────────────────────
    entity_fields: tuple[EntityFieldInfo, ...] = field(default_factory=tuple)

    # ── Entity: связи между сущностями ─────────────────────────────────────
    entity_relations: tuple[EntityRelationInfo, ...] = field(default_factory=tuple)

    # ── Entity: поля Lifecycle ─────────────────────────────────────────────
    entity_lifecycles: tuple[EntityLifecycleInfo, ...] = field(default_factory=tuple)

    # ── Удобные методы: Action / Plugin / ResourceManager ──────────────────

    def has_meta(self) -> bool:
        """Есть ли описание (@meta)."""
        return self.meta is not None

    def has_role(self) -> bool:
        """Назначены ли ролевые ограничения."""
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

    def has_error_handlers(self) -> bool:
        """Объявлены ли обработчики ошибок (@on_error)."""
        return len(self.error_handlers) > 0

    def has_compensators(self) -> bool:
        """Объявлены ли компенсаторы (@compensate)."""
        return len(self.compensators) > 0

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
        """Возвращает только regular-аспекты."""
        return tuple(a for a in self.aspects if a.aspect_type == "regular")

    def get_summary_aspect(self) -> AspectMeta | None:
        """Возвращает summary-аспект или None."""
        summaries = [a for a in self.aspects if a.aspect_type == "summary"]
        return summaries[0] if summaries else None

    def get_checkers_for_aspect(self, method_name: str) -> tuple[CheckerMeta, ...]:
        """Возвращает чекеры, привязанные к аспекту."""
        return tuple(c for c in self.checkers if c.method_name == method_name)

    def get_compensator_for_aspect(self, aspect_name: str) -> CompensatorMeta | None:
        """Возвращает компенсатор для аспекта или None."""
        for comp in self.compensators:
            if comp.target_aspect_name == aspect_name:
                return comp
        return None

    def get_error_handler_for(self, error: Exception) -> OnErrorMeta | None:
        """Находит первый подходящий обработчик ошибок."""
        for handler in self.error_handlers:
            if isinstance(error, handler.exception_types):
                return handler
        return None

    def get_dependency_classes(self) -> tuple[type, ...]:
        """Кортеж классов зависимостей."""
        return tuple(d.cls for d in self.dependencies)

    def get_connection_keys(self) -> tuple[str, ...]:
        """Кортеж ключей соединений."""
        return tuple(c.key for c in self.connections)

    # ── Удобные методы: Entity ─────────────────────────────────────────────

    def is_entity(self) -> bool:
        """True если класс — сущность доменной модели (@entity)."""
        return self.entity_info is not None

    def has_entity_fields(self) -> bool:
        """Есть ли простые поля у сущности."""
        return len(self.entity_fields) > 0

    def has_entity_relations(self) -> bool:
        """Есть ли связи с другими сущностями."""
        return len(self.entity_relations) > 0

    def has_entity_lifecycles(self) -> bool:
        """Есть ли поля Lifecycle."""
        return len(self.entity_lifecycles) > 0

    def get_entity_field(self, name: str) -> EntityFieldInfo | None:
        """Возвращает метаданные поля сущности по имени или None."""
        for f in self.entity_fields:
            if f.field_name == name:
                return f
        return None

    def get_entity_relation(self, name: str) -> EntityRelationInfo | None:
        """Возвращает метаданные связи по имени или None."""
        for r in self.entity_relations:
            if r.field_name == name:
                return r
        return None

    def get_entity_lifecycle(self, name: str) -> EntityLifecycleInfo | None:
        """Возвращает метаданные Lifecycle по имени или None."""
        for lc in self.entity_lifecycles:
            if lc.field_name == name:
                return lc
        return None

    def get_entity_field_names(self) -> tuple[str, ...]:
        """Имена всех простых полей сущности."""
        return tuple(f.field_name for f in self.entity_fields)

    def get_entity_relation_names(self) -> tuple[str, ...]:
        """Имена всех связей сущности."""
        return tuple(r.field_name for r in self.entity_relations)

    def get_entity_lifecycle_names(self) -> tuple[str, ...]:
        """Имена всех полей Lifecycle сущности."""
        return tuple(lc.field_name for lc in self.entity_lifecycles)

    # ── Строковое представление ────────────────────────────────────────────

    def __repr__(self) -> str:
        """Компактное строковое представление для отладки."""
        parts = [f"ClassMetadata({self.class_name}"]

        if self.has_meta() and self.meta is not None:
            domain_str = self.meta.domain.name if self.meta.domain else "None"
            parts.append(f"  meta='{self.meta.description}' domain={domain_str}")

        if self.is_entity() and self.entity_info is not None:
            domain_str = self.entity_info.domain.name if self.entity_info.domain else "None"
            parts.append(f"  entity='{self.entity_info.description}' domain={domain_str}")

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

        if self.has_error_handlers():
            handler_info = ", ".join(
                f"{h.method_name}({','.join(t.__name__ for t in h.exception_types)})"
                for h in self.error_handlers
            )
            parts.append(f"  error_handlers=[{handler_info}]")

        if self.has_compensators():
            comp_info = ", ".join(
                f"{c.method_name}→{c.target_aspect_name}"
                for c in self.compensators
            )
            parts.append(f"  compensators=[{comp_info}]")

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

        if self.has_entity_fields():
            ef_names = ", ".join(f.field_name for f in self.entity_fields)
            parts.append(f"  entity_fields=[{ef_names}]")

        if self.has_entity_relations():
            er_info = ", ".join(
                f"{r.field_name}:{r.relation_type}:{r.cardinality}"
                for r in self.entity_relations
            )
            parts.append(f"  entity_relations=[{er_info}]")

        if self.has_entity_lifecycles():
            el_info = ", ".join(
                f"{lc.field_name}({lc.state_count} states)"
                for lc in self.entity_lifecycles
            )
            parts.append(f"  entity_lifecycles=[{el_info}]")

        parts.append(")")
        return "\n".join(parts)
