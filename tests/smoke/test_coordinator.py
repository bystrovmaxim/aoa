# tests/smoke/test_coordinator.py
"""
Smoke-тест GateCoordinator — сборка метаданных тестовой доменной модели.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что GateCoordinator корректно собирает метаданные для всех
Action тестовой доменной модели. Метаданные включают: описание и домен
(@meta), роли (@check_roles), аспекты (@regular_aspect, @summary_aspect),
чекеры, зависимости (@depends), соединения (@connection).

Если координатор не может собрать метаданные — декораторы применены
некорректно, структурные инварианты нарушены, или MetadataBuilder
содержит баг.
"""


from action_machine.core.gate_coordinator import GateCoordinator
from tests.domain import (
    AdminAction,
    ChildAction,
    FullAction,
    OrdersDomain,
    PingAction,
    SimpleAction,
    SystemDomain,
)

# ═════════════════════════════════════════════════════════════════════════════
# Регистрация всех Action без ошибок
# ═════════════════════════════════════════════════════════════════════════════


def test_all_actions_register_without_errors(coordinator: GateCoordinator) -> None:
    """
    Все пять Action тестовой доменной модели регистрируются без ошибок.

    Проверяет: MetadataBuilder.build() успешно собирает метаданные
    для каждого Action, декораторы корректны, структурные инварианты
    соблюдены (summary последний, чекеры привязаны к аспектам и т.д.).
    """
    # Arrange
    all_actions = [PingAction, SimpleAction, FullAction, ChildAction, AdminAction]

    # Act & Assert
    for action_class in all_actions:
        metadata = coordinator.get(action_class)
        assert metadata.has_aspects(), f"{action_class.__name__} должен содержать аспекты"
        assert metadata.has_meta(), f"{action_class.__name__} должен иметь @meta"
        assert metadata.has_role(), f"{action_class.__name__} должен иметь @check_roles"


# ═════════════════════════════════════════════════════════════════════════════
# Метаданные PingAction
# ═════════════════════════════════════════════════════════════════════════════


def test_ping_metadata_description(coordinator: GateCoordinator) -> None:
    """
    PingAction имеет описание 'Проверка доступности сервиса'.

    Проверяет, что @meta(description=...) корректно записан
    и MetadataBuilder собрал его в ClassMetadata.meta.
    """
    # Arrange & Act
    metadata = coordinator.get(PingAction)

    # Assert
    assert metadata.meta is not None
    assert metadata.meta.description == "Проверка доступности сервиса"


def test_ping_metadata_domain(coordinator: GateCoordinator) -> None:
    """
    PingAction принадлежит SystemDomain.

    Проверяет, что @meta(domain=SystemDomain) корректно собран.
    """
    # Arrange & Act
    metadata = coordinator.get(PingAction)

    # Assert
    assert metadata.meta is not None
    assert metadata.meta.domain is SystemDomain


def test_ping_metadata_role_none(coordinator: GateCoordinator) -> None:
    """
    PingAction имеет роль ROLE_NONE (доступен всем).

    Проверяет, что @check_roles(ROLE_NONE) собран как spec="__NONE__".
    """
    # Arrange & Act
    metadata = coordinator.get(PingAction)

    # Assert
    assert metadata.role is not None
    assert metadata.role.spec == "__NONE__"


def test_ping_metadata_single_summary_aspect(coordinator: GateCoordinator) -> None:
    """
    PingAction содержит ровно один аспект типа summary.

    Проверяет, что MetadataBuilder обнаружил summary-аспект pong_summary.
    """
    # Arrange & Act
    metadata = coordinator.get(PingAction)

    # Assert
    assert len(metadata.aspects) == 1
    assert metadata.aspects[0].aspect_type == "summary"
    assert metadata.aspects[0].method_name == "pong_summary"


# ═════════════════════════════════════════════════════════════════════════════
# Метаданные FullAction
# ═════════════════════════════════════════════════════════════════════════════


def test_full_metadata_domain(coordinator: GateCoordinator) -> None:
    """
    FullAction принадлежит OrdersDomain.
    """
    # Arrange & Act
    metadata = coordinator.get(FullAction)

    # Assert
    assert metadata.meta is not None
    assert metadata.meta.domain is OrdersDomain


def test_full_metadata_role_manager(coordinator: GateCoordinator) -> None:
    """
    FullAction требует роль 'manager'.
    """
    # Arrange & Act
    metadata = coordinator.get(FullAction)

    # Assert
    assert metadata.role is not None
    assert metadata.role.spec == "manager"


def test_full_metadata_three_aspects(coordinator: GateCoordinator) -> None:
    """
    FullAction содержит три аспекта: 2 regular + 1 summary.

    Порядок аспектов: process_payment_aspect, calc_total_aspect, build_result_summary.
    Summary-аспект обязан быть последним.
    """
    # Arrange & Act
    metadata = coordinator.get(FullAction)

    # Assert
    assert len(metadata.aspects) == 3
    assert metadata.aspects[0].aspect_type == "regular"
    assert metadata.aspects[0].method_name == "process_payment_aspect"
    assert metadata.aspects[1].aspect_type == "regular"
    assert metadata.aspects[1].method_name == "calc_total_aspect"
    assert metadata.aspects[2].aspect_type == "summary"
    assert metadata.aspects[2].method_name == "build_result_summary"


def test_full_metadata_dependencies(coordinator: GateCoordinator) -> None:
    """
    FullAction объявляет две зависимости: PaymentService, NotificationService.
    """
    # Arrange & Act
    metadata = coordinator.get(FullAction)

    # Assert
    assert metadata.has_dependencies()
    dep_classes = metadata.get_dependency_classes()
    assert len(dep_classes) == 2


def test_full_metadata_connections(coordinator: GateCoordinator) -> None:
    """
    FullAction объявляет одно connection с ключом 'db'.
    """
    # Arrange & Act
    metadata = coordinator.get(FullAction)

    # Assert
    assert metadata.has_connections()
    conn_keys = metadata.get_connection_keys()
    assert conn_keys == ("db",)


def test_full_metadata_checkers(coordinator: GateCoordinator) -> None:
    """
    FullAction содержит чекеры для двух полей: txn_id и total.

    txn_id привязан к аспекту process_payment_aspect (result_string).
    total привязан к аспекту calc_total_aspect (result_float).
    """
    # Arrange & Act
    metadata = coordinator.get(FullAction)

    # Assert
    assert metadata.has_checkers()
    checker_fields = {c.field_name for c in metadata.checkers}
    assert "txn_id" in checker_fields
    assert "total" in checker_fields


# ═════════════════════════════════════════════════════════════════════════════
# Метаданные AdminAction
# ═════════════════════════════════════════════════════════════════════════════


def test_admin_metadata_role(coordinator: GateCoordinator) -> None:
    """
    AdminAction требует роль 'admin'.
    """
    # Arrange & Act
    metadata = coordinator.get(AdminAction)

    # Assert
    assert metadata.role is not None
    assert metadata.role.spec == "admin"


def test_admin_metadata_no_dependencies(coordinator: GateCoordinator) -> None:
    """
    AdminAction не объявляет зависимостей и connections.
    """
    # Arrange & Act
    metadata = coordinator.get(AdminAction)

    # Assert
    assert not metadata.has_dependencies()
    assert not metadata.has_connections()
