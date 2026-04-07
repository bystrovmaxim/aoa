# tests/domain/test_coordinator.py
"""
Тесты регистрации сущностей доменной модели в GateCoordinator.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что сущности (@entity) регистрируются через тот же
GateCoordinator.get(), что и Action/Plugin/ResourceManager.
MetadataBuilder.build() собирает entity-коллекторы, ClassMetadata
содержит entity-поля, граф заполняется узлами entity/entity_field/
entity_relation/entity_lifecycle.

═══════════════════════════════════════════════════════════════════════════════
ТЕСТОВЫЕ СУЩНОСТИ
═══════════════════════════════════════════════════════════════════════════════

- TestEntity — простая сущность без связей и Lifecycle.
- LifecycleEntity — сущность с DraftLifecycle.
- RelatedEntity — сущность со связями (AssociationOne, AggregateMany).
- ComplexEntity — сущность со всем функционалом.

Все сущности определены в tests/domain_model/entities.py.
"""

from action_machine.core.gate_coordinator import GateCoordinator

from ..domain_model.entities import (
    ComplexEntity,
    DraftLifecycle,
    LifecycleEntity,
    RelatedEntity,
    SampleEntity,
)


class TestEntityRegistration:
    """Тесты регистрации сущностей в GateCoordinator."""

    def test_register_simple_entity(self):
        """Регистрация простой сущности через get()."""
        coordinator = GateCoordinator()
        meta = coordinator.get(SampleEntity)

        assert meta.is_entity()
        assert meta.entity_info is not None
        assert meta.entity_info.description == "Простая тестовая сущность"
        assert meta.entity_info.domain.name == "test"

    def test_entity_fields(self):
        """Простые поля сущности собираются из model_fields."""
        coordinator = GateCoordinator()
        meta = coordinator.get(SampleEntity)

        field_names = meta.get_entity_field_names()
        assert "id" in field_names
        assert "name" in field_names
        assert "value" in field_names

    def test_entity_field_details(self):
        """Детали поля: тип, описание, обязательность, constraints."""
        coordinator = GateCoordinator()
        meta = coordinator.get(SampleEntity)

        value_field = meta.get_entity_field("value")
        assert value_field is not None
        assert value_field.field_name == "value"
        assert value_field.description == "Значение"
        assert value_field.required is True
        assert "ge" in value_field.constraints
        assert value_field.constraints["ge"] == 0

    def test_metadata_caching(self):
        """Повторный вызов get() возвращает тот же объект."""
        coordinator = GateCoordinator()
        meta1 = coordinator.get(SampleEntity)
        meta2 = coordinator.get(SampleEntity)

        assert meta1 is meta2

    def test_entity_not_action(self):
        """Entity не имеет аспектов, ролей, зависимостей."""
        coordinator = GateCoordinator()
        meta = coordinator.get(SampleEntity)

        assert not meta.has_aspects()
        assert not meta.has_role()
        assert not meta.has_dependencies()
        assert meta.meta is None  # @entity, не @meta


class TestEntityLifecycle:
    """Тесты Lifecycle в сущностях."""

    def test_entity_with_lifecycle(self):
        """Сущность с DraftLifecycle — lifecycle собирается."""
        coordinator = GateCoordinator()
        meta = coordinator.get(LifecycleEntity)

        assert meta.has_entity_lifecycles()
        assert len(meta.entity_lifecycles) == 1

        lc_info = meta.entity_lifecycles[0]
        assert lc_info.field_name == "lifecycle"
        assert lc_info.lifecycle_class is DraftLifecycle
        assert lc_info.state_count == 3
        assert lc_info.initial_count == 1
        assert lc_info.final_count == 1

    def test_entity_without_lifecycle(self):
        """Сущность без Lifecycle — lifecycle пуст."""
        coordinator = GateCoordinator()
        meta = coordinator.get(SampleEntity)

        assert not meta.has_entity_lifecycles()
        assert len(meta.entity_lifecycles) == 0


class TestEntityRelations:
    """Тесты связей в сущностях."""

    def test_entity_with_relations(self):
        """Связи собираются из Annotated-аннотаций."""
        coordinator = GateCoordinator()
        meta = coordinator.get(RelatedEntity)

        assert meta.has_entity_relations()
        relation_names = meta.get_entity_relation_names()
        assert "parent" in relation_names
        assert "children" in relation_names

    def test_relation_details(self):
        """Детали связи: тип, кардинальность, описание."""
        coordinator = GateCoordinator()
        meta = coordinator.get(RelatedEntity)

        parent_rel = meta.get_entity_relation("parent")
        assert parent_rel is not None
        assert parent_rel.relation_type == "association"
        assert parent_rel.cardinality == "one"
        assert parent_rel.description == "Родительская сущность"
        assert parent_rel.has_inverse is False

        children_rel = meta.get_entity_relation("children")
        assert children_rel is not None
        assert children_rel.relation_type == "aggregation"
        assert children_rel.cardinality == "many"

    def test_entity_without_relations(self):
        """Сущность без связей — relations пуст."""
        coordinator = GateCoordinator()
        meta = coordinator.get(SampleEntity)

        assert not meta.has_entity_relations()


class TestComplexEntity:
    """Тесты комплексной сущности со всем функционалом."""

    def test_complex_entity_all_components(self):
        """ComplexEntity содержит поля, связи и Lifecycle."""
        coordinator = GateCoordinator()
        meta = coordinator.get(ComplexEntity)

        assert meta.is_entity()
        assert meta.has_entity_fields()
        assert meta.has_entity_relations()
        assert meta.has_entity_lifecycles()

    def test_complex_entity_fields(self):
        """Простые поля ComplexEntity (не связи, не Lifecycle)."""
        coordinator = GateCoordinator()
        meta = coordinator.get(ComplexEntity)

        field_names = meta.get_entity_field_names()
        assert "id" in field_names
        assert "name" in field_names
        assert "amount" in field_names
        # lifecycle, owner, related_items — не простые поля
        assert "lifecycle" not in field_names
        assert "owner" not in field_names
        assert "related_items" not in field_names

    def test_complex_entity_relations(self):
        """Связи ComplexEntity."""
        coordinator = GateCoordinator()
        meta = coordinator.get(ComplexEntity)

        relation_names = meta.get_entity_relation_names()
        assert "owner" in relation_names
        assert "related_items" in relation_names

    def test_complex_entity_lifecycle(self):
        """Lifecycle ComplexEntity."""
        coordinator = GateCoordinator()
        meta = coordinator.get(ComplexEntity)

        lc_names = meta.get_entity_lifecycle_names()
        assert "lifecycle" in lc_names


class TestEntityInGraph:
    """Тесты entity-узлов в графе GateCoordinator."""

    def test_entity_node_in_graph(self):
        """Сущность попадает в граф как узел типа 'entity'."""
        coordinator = GateCoordinator()
        coordinator.get(SampleEntity)

        entity_nodes = coordinator.get_nodes_by_type("entity")
        assert len(entity_nodes) >= 1

        names = [n["name"] for n in entity_nodes]
        assert any("SampleEntity" in name for name in names)

    def test_entity_field_nodes(self):
        """Поля сущности — дочерние узлы типа 'entity_field'."""
        coordinator = GateCoordinator()
        coordinator.get(SampleEntity)

        field_nodes = coordinator.get_nodes_by_type("entity_field")
        field_names = [n["name"] for n in field_nodes]
        assert any("id" in name for name in field_names)
        assert any("name" in name for name in field_names)
        assert any("value" in name for name in field_names)

    def test_entity_domain_node(self):
        """Entity с domain создаёт узел домена и ребро belongs_to."""
        coordinator = GateCoordinator()
        coordinator.get(SampleEntity)

        domain_nodes = coordinator.get_nodes_by_type("domain")
        domain_names = [n["name"] for n in domain_nodes]
        assert "test" in domain_names

    def test_entity_lifecycle_node(self):
        """Lifecycle — дочерний узел типа 'entity_lifecycle'."""
        coordinator = GateCoordinator()
        coordinator.get(LifecycleEntity)

        lc_nodes = coordinator.get_nodes_by_type("entity_lifecycle")
        assert len(lc_nodes) >= 1
        assert any("lifecycle" in n["name"] for n in lc_nodes)

    def test_entity_relation_node(self):
        """Связи — дочерние узлы типа 'entity_relation'."""
        coordinator = GateCoordinator()
        coordinator.get(RelatedEntity)

        rel_nodes = coordinator.get_nodes_by_type("entity_relation")
        assert len(rel_nodes) >= 1

    def test_get_all_entities(self):
        """Получение всех зарегистрированных сущностей."""
        coordinator = GateCoordinator()
        coordinator.get(SampleEntity)
        coordinator.get(LifecycleEntity)
        coordinator.get(RelatedEntity)

        all_meta = coordinator.get_all_metadata()
        entity_meta = [m for m in all_meta if m.is_entity()]
        assert len(entity_meta) == 3

    def test_multiple_entities_share_domain(self):
        """Несколько сущностей с одним доменом — один узел domain."""
        coordinator = GateCoordinator()
        coordinator.get(SampleEntity)
        coordinator.get(LifecycleEntity)

        domain_nodes = coordinator.get_nodes_by_type("domain")
        test_domains = [n for n in domain_nodes if n["name"] == "test"]
        assert len(test_domains) == 1  # один узел, два ребра belongs_to
