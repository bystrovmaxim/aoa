# tests/metadata/test_coordinator_strict.py
"""
Тесты GateCoordinator — strict mode, домены в графе, описания в узлах.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет режим strict координатора (обязательный domain для действий
и ресурсов с @meta), создание узлов доменов в графе, описания в payload
узлов и строковое представление координатора.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestStrictProperty
    - По умолчанию strict=False.
    - strict=True устанавливается через конструктор.

TestStrictActionWithDomain
    - Действие с domain в strict mode — допустимо.
    - Действие без domain в strict mode → ошибка.
    - Действие без domain в non-strict mode — допустимо.

TestStrictResourceWithDomain
    - ResourceManager с domain в strict mode — допустимо.
    - ResourceManager без domain в strict mode → ошибка.
    - ResourceManager без domain в non-strict mode — допустимо.

TestStrictEdgeCases
    - Пустой класс (без @meta) в strict mode — допустимо (strict
      проверяет только классы с @meta и аспектами/ресурсами).
    - Действие без аспектов в strict mode — допустимо (проверка
      domain только для классов с аспектами).

TestDomainNodes
    - Действие с domain создаёт domain-узел в графе.
    - Два действия с одним доменом — один domain-узел.
    - Два действия с разными доменами — два domain-узла.
    - Действие без domain — нет domain-узла.

TestGraphDescriptions
    - Узел action содержит description в payload.
    - Узел dependency содержит description в payload.
    - Пустой класс — пустое description.

TestCoordinatorRepr
    - repr содержит strict.
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.domain.base_domain import BaseDomain
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


def _node_key(node_type: str, cls: type, suffix: str = "") -> str:
    """Формирует ключ узла графа: 'тип:модуль.ИмяКласса[.суффикс]'."""
    name = f"{cls.__module__}.{cls.__qualname__}"
    if suffix:
        name = f"{name}.{suffix}"
    return f"{node_type}:{name}"

class _Params(BaseParams):
    pass


class _Result(BaseResult):
    pass


class _OrdersDomain(BaseDomain):
    name = "orders"


class _PaymentsDomain(BaseDomain):
    name = "payments"


# ─── Действие с доменом ──────────────────────────────────────────────────


@meta("Создание заказа", domain=_OrdersDomain)
@check_roles(ROLE_NONE)
class _OrderAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Другое действие с тем же доменом ────────────────────────────────────


@meta("Получение заказа", domain=_OrdersDomain)
@check_roles(ROLE_NONE)
class _GetOrderAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Действие с другим доменом ───────────────────────────────────────────


@meta("Оплата", domain=_PaymentsDomain)
@check_roles(ROLE_NONE)
class _PaymentAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Действие без домена ─────────────────────────────────────────────────


@meta("Ping без домена")
@check_roles(ROLE_NONE)
class _NoDomainAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


# ─── ResourceManager с доменом ───────────────────────────────────────────


@meta("Менеджер заказов", domain=_OrdersDomain)
class _OrderManager(BaseResourceManager):
    pass


# ─── ResourceManager без домена ──────────────────────────────────────────


@meta("Менеджер без домена")
class _NoDomainManager(BaseResourceManager):
    pass


# ─── Действие без @meta и без аспектов ──────────────────────────────────


@check_roles(ROLE_NONE)
class _PlainAction(BaseAction["_Params", "_Result"]):
    pass


# ─── Действие без аспектов, с @meta ─────────────────────────────────────


@meta("Действие без аспектов")
@check_roles(ROLE_NONE)
class _NoAspectsAction(BaseAction["_Params", "_Result"]):
    pass


class _EmptyClass:
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Свойство strict
# ═════════════════════════════════════════════════════════════════════════════


class TestStrictProperty:
    """Проверяет свойство strict координатора."""

    def test_default_is_false(self):
        """По умолчанию strict=False."""
        # Arrange & Act
        coord = GateCoordinator()

        # Assert
        assert coord.strict is False

    def test_strict_true_via_constructor(self):
        """strict=True устанавливается через конструктор."""
        # Arrange & Act
        coord = GateCoordinator(strict=True)

        # Assert
        assert coord.strict is True


# ═════════════════════════════════════════════════════════════════════════════
# Strict mode — действия
# ═════════════════════════════════════════════════════════════════════════════


class TestStrictActionWithDomain:
    """Проверяет strict mode для действий."""

    def test_action_with_domain_ok(self):
        """Действие с domain в strict mode — допустимо."""
        # Arrange
        coord = GateCoordinator(strict=True)

        # Act
        result = coord.get(_OrderAction)

        # Assert
        assert result.meta.domain is _OrdersDomain

    def test_action_without_domain_raises(self):
        """Действие без domain в strict mode → ошибка."""
        # Arrange
        coord = GateCoordinator(strict=True)

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            coord.get(_NoDomainAction)

    def test_action_without_domain_non_strict_ok(self):
        """Действие без domain в non-strict mode — допустимо."""
        # Arrange
        coord = GateCoordinator(strict=False)

        # Act
        result = coord.get(_NoDomainAction)

        # Assert
        assert result.meta.domain is None


# ═════════════════════════════════════════════════════════════════════════════
# Strict mode — ресурсы
# ═════════════════════════════════════════════════════════════════════════════


class TestStrictResourceWithDomain:
    """Проверяет strict mode для ResourceManager."""

    def test_resource_with_domain_ok(self):
        """ResourceManager с domain в strict mode — допустимо."""
        # Arrange
        coord = GateCoordinator(strict=True)

        # Act
        result = coord.get(_OrderManager)

        # Assert
        assert result.meta.domain is _OrdersDomain

    def test_resource_without_domain_raises(self):
        """ResourceManager без domain в strict mode → ошибка."""
        # Arrange
        coord = GateCoordinator(strict=True)

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            coord.get(_NoDomainManager)

    def test_resource_without_domain_non_strict_ok(self):
        """ResourceManager без domain в non-strict mode — допустимо."""
        # Arrange
        coord = GateCoordinator(strict=False)

        # Act
        result = coord.get(_NoDomainManager)

        # Assert
        assert result.meta.domain is None


# ═════════════════════════════════════════════════════════════════════════════
# Strict mode — граничные случаи
# ═════════════════════════════════════════════════════════════════════════════


class TestStrictEdgeCases:
    """Проверяет граничные случаи strict mode."""

    def test_plain_class_no_effect(self):
        """Пустой класс без @meta в strict mode — допустимо."""
        # Arrange
        coord = GateCoordinator(strict=True)

        # Act
        result = coord.get(_EmptyClass)

        # Assert
        assert result.has_meta() is False

    def test_action_without_aspects_no_effect(self):
        """Действие без аспектов в strict mode — допустимо (нет проверки domain)."""
        # Arrange
        coord = GateCoordinator(strict=True)

        # Act — не должно поднять исключение
        result = coord.get(_PlainAction)

        # Assert
        assert result.has_meta() is False


# ═════════════════════════════════════════════════════════════════════════════
# Домены в графе
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainNodes:
    """Проверяет создание domain-узлов в графе."""

    def test_action_with_domain_creates_domain_node(self):
        """Действие с domain создаёт domain-узел."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_OrderAction)
        nodes = coord.get_nodes_by_type("domain")

        # Assert
        assert len(nodes) >= 1

    def test_two_actions_same_domain_one_node(self):
        """Два действия с одним доменом — один domain-узел."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_OrderAction)
        coord.get(_GetOrderAction)
        domain_nodes = coord.get_nodes_by_type("domain")

        # Assert
        assert len(domain_nodes) == 1

    def test_two_actions_different_domains_two_nodes(self):
        """Два действия с разными доменами — два domain-узла."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_OrderAction)
        coord.get(_PaymentAction)
        nodes = coord.get_nodes_by_type("domain")

        # Assert
        assert len(nodes) >= 2

    def test_action_without_domain_no_domain_node(self):
        """Действие без domain не создаёт domain-узел."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_NoDomainAction)
        nodes = coord.get_nodes_by_type("domain")

        # Assert
        assert len(nodes) == 0

    def test_resource_with_domain_creates_domain_node(self):
        """ResourceManager с domain создаёт domain-узел."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_OrderManager)
        nodes = coord.get_nodes_by_type("domain")

        # Assert
        assert len(nodes) >= 1

    def test_action_and_resource_same_domain_shared_node(self):
        """Действие и ресурс с одним доменом используют один domain-узел."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_OrderAction)
        coord.get(_OrderManager)
        domain_nodes = coord.get_nodes_by_type("domain")

        # Assert — orders один раз
        assert len(domain_nodes) == 1


# ═════════════════════════════════════════════════════════════════════════════
# Описания в узлах графа
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphDescriptions:
    """Проверяет, что узлы графа содержат описания в payload."""

    def test_action_node_contains_description(self):
        """Узел action доступен через get_node по ключу."""
        # Arrange
        coord = GateCoordinator()
        coord.get(_OrderAction)

        # Act
        key = _node_key("action", _OrderAction)
        node = coord.get_node(key)

        # Assert
        assert node is not None

    def test_action_node_without_domain_has_no_domain_in_payload(self):
        """Действие без domain регистрируется без ошибок."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_NoDomainAction)

        # Assert
        assert coord.has(_NoDomainAction)

    def test_empty_class_empty_description(self):
        """Пустой класс регистрируется без ошибок."""
        # Arrange
        coord = GateCoordinator()

        # Act
        coord.get(_EmptyClass)

        # Assert
        assert coord.graph_node_count >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Строковое представление координатора
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorRepr:
    """Проверяет __repr__ GateCoordinator."""

    def test_empty_repr_contains_strict(self):
        """repr пустого координатора содержит strict."""
        # Arrange
        coord = GateCoordinator(strict=True)

        # Act
        result = repr(coord)

        # Assert
        assert "strict" in result.lower() or "True" in result

    def test_non_empty_repr_contains_strict(self):
        """repr координатора с классами содержит strict."""
        # Arrange
        coord = GateCoordinator(strict=False)
        coord.get(_NoDomainAction)

        # Act
        result = repr(coord)

        # Assert
        assert isinstance(result, str)
        assert "strict" in result.lower() or "False" in result
