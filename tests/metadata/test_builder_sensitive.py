# tests/metadata/test_builder_sensitive.py
"""
Тесты MetadataBuilder — сборка sensitive-полей и подписок (subscriptions).

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что MetadataBuilder корректно собирает sensitive-поля
(SensitiveFieldMeta) из свойств, декорированных @sensitive, и подписки
(SubscriptionInfo) из методов, декорированных @on.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestSensitiveFields
    - Одно sensitive-поле собирается.
    - Несколько sensitive-полей собираются.
    - sensitive(enabled=False) всё равно собирается.
    - Класс без sensitive — пустой кортеж.

TestSensitiveFieldAttributes
    - property_name сохраняется.
    - config содержит max_chars, char, max_percent, enabled.

TestSubscriptions
    - Одна подписка собирается.
    - Несколько подписок собираются.
    - event_type, action_filter, ignore_exceptions сохраняются.
    - Класс без подписок — пустой кортеж.

TestSubscriptionsWithoutGateHost
    - Подписки на классе без OnGateHost → ошибка.
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.metadata.builder import MetadataBuilder
from action_machine.plugins.decorators import on
from action_machine.plugins.on_gate_host import OnGateHost

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class _Params(BaseParams):
    pass


class _Result(BaseResult):
    pass


# ─── Действие с одним sensitive-полем ────────────────────────────────────


@meta("Действие с sensitive")
@check_roles(ROLE_NONE)
class _ActionOneSensitiveAction(BaseAction["_Params", "_Result"]):

    def __init__(self):
        self._phone = "+7-999-123-4567"

    @sensitive()
    @property
    def phone(self):
        return self._phone

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Действие с несколькими sensitive-полями ─────────────────────────────


@meta("Действие с несколькими sensitive")
@check_roles(ROLE_NONE)
class _ActionMultipleSensitiveAction(BaseAction["_Params", "_Result"]):

    def __init__(self):
        self._phone = "+7-999-123-4567"
        self._email = "alice@example.com"

    @sensitive(max_chars=4, char="*", max_percent=30)
    @property
    def phone(self):
        return self._phone

    @sensitive(max_chars=3, char="#", max_percent=50)
    @property
    def email(self):
        return self._email

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Действие с disabled sensitive ───────────────────────────────────────


@meta("Действие с disabled sensitive")
@check_roles(ROLE_NONE)
class _ActionDisabledSensitiveAction(BaseAction["_Params", "_Result"]):

    def __init__(self):
        self._token = "secret-token"

    @sensitive(enabled=False)
    @property
    def token(self):
        return self._token

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Действие без sensitive ──────────────────────────────────────────────


@meta("Действие без sensitive")
@check_roles(ROLE_NONE)
class _ActionNoSensitiveAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Плагин-наследник OnGateHost с подписками ───────────────────────────


class _AuditPlugin(OnGateHost):

    @on("global.start")
    async def on_start(self, event, state, logger):
        pass

    @on("global.finish", action_filter="*", ignore_exceptions=True)
    async def on_finish(self, event, state, logger):
        pass


class _MetricsPlugin(OnGateHost):

    @on("global.finish")
    async def on_finish(self, event, state, logger):
        pass


class _EmptyPluginHost(OnGateHost):
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Sensitive-поля
# ═════════════════════════════════════════════════════════════════════════════


class TestSensitiveFields:
    """Проверяет сборку sensitive-полей из декоратора @sensitive."""

    def test_single_sensitive_collected(self):
        """Одно sensitive-поле собирается."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneSensitiveAction)

        # Assert
        assert result.has_sensitive_fields() is True
        assert len(result.sensitive_fields) == 1

    def test_multiple_sensitive_collected(self):
        """Несколько sensitive-полей собираются."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionMultipleSensitiveAction)

        # Assert
        assert len(result.sensitive_fields) == 2
        names = {sf.property_name for sf in result.sensitive_fields}
        assert names == {"phone", "email"}

    def test_disabled_sensitive_still_collected(self):
        """sensitive(enabled=False) всё равно собирается в метаданных."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionDisabledSensitiveAction)

        # Assert
        assert result.has_sensitive_fields() is True
        assert len(result.sensitive_fields) == 1

    def test_no_sensitive_fields_empty(self):
        """Класс без sensitive → пустой кортеж."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionNoSensitiveAction)

        # Assert
        assert result.has_sensitive_fields() is False
        assert result.sensitive_fields == ()


# ═════════════════════════════════════════════════════════════════════════════
# Атрибуты sensitive-поля
# ═════════════════════════════════════════════════════════════════════════════


class TestSensitiveFieldAttributes:
    """Проверяет атрибуты SensitiveFieldMeta."""

    def test_property_name_preserved(self):
        """property_name сохраняет имя свойства."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneSensitiveAction)
        sf = result.sensitive_fields[0]

        # Assert
        assert sf.property_name == "phone"

    def test_config_contains_max_chars(self):
        """config содержит max_chars из декоратора."""
        result = MetadataBuilder().build(_ActionMultipleSensitiveAction)
        phone_sf = next(sf for sf in result.sensitive_fields if sf.property_name == "phone")
        assert phone_sf.config["max_chars"] == 4

    def test_config_contains_char(self):
        """config содержит char из декоратора."""
        result = MetadataBuilder().build(_ActionMultipleSensitiveAction)
        phone_sf = next(sf for sf in result.sensitive_fields if sf.property_name == "phone")
        assert phone_sf.config["char"] == "*"

    def test_config_contains_max_percent(self):
        """config содержит max_percent из декоратора."""
        result = MetadataBuilder().build(_ActionMultipleSensitiveAction)
        email_sf = next(sf for sf in result.sensitive_fields if sf.property_name == "email")
        assert email_sf.config["max_percent"] == 50

    def test_disabled_sensitive_config_enabled_false(self):
        """enabled=False сохраняется в config."""
        result = MetadataBuilder().build(_ActionDisabledSensitiveAction)
        sf = result.sensitive_fields[0]
        assert sf.config["enabled"] is False


# ═════════════════════════════════════════════════════════════════════════════
# Подписки (subscriptions)
# ═════════════════════════════════════════════════════════════════════════════


class TestSubscriptions:
    """Проверяет сборку подписок из декоратора @on."""

    def test_single_subscription_collected(self):
        """Одна подписка собирается."""
        # Arrange & Act
        result = MetadataBuilder().build(_MetricsPlugin)

        # Assert
        assert result.has_subscriptions() is True
        assert len(result.subscriptions) == 1

    def test_multiple_subscriptions_collected(self):
        """Несколько подписок собираются."""
        # Arrange & Act
        result = MetadataBuilder().build(_AuditPlugin)

        # Assert
        assert len(result.subscriptions) == 2

    def test_event_type_preserved(self):
        """event_type сохраняется в SubscriptionInfo."""
        # Arrange & Act
        result = MetadataBuilder().build(_MetricsPlugin)
        sub = result.subscriptions[0]

        # Assert
        assert sub.event_type == "global.finish"

    def test_action_filter_preserved(self):
        """action_filter сохраняется в SubscriptionInfo."""
        # Arrange & Act
        result = MetadataBuilder().build(_AuditPlugin)
        finish_sub = next(s for s in result.subscriptions if s.event_type == "global.finish")

        # Assert
        assert finish_sub.action_filter == "*"

    def test_ignore_exceptions_preserved(self):
        """ignore_exceptions сохраняется в SubscriptionInfo."""
        # Arrange & Act
        result = MetadataBuilder().build(_AuditPlugin)
        finish_sub = next(s for s in result.subscriptions if s.event_type == "global.finish")

        # Assert
        assert finish_sub.ignore_exceptions is True

    def test_no_subscriptions_empty(self):
        """Класс без подписок → пустой кортеж."""
        # Arrange & Act
        result = MetadataBuilder().build(_EmptyPluginHost)

        # Assert
        assert result.has_subscriptions() is False
        assert result.subscriptions == ()


# ═════════════════════════════════════════════════════════════════════════════
# Подписки без GateHost
# ═════════════════════════════════════════════════════════════════════════════


class TestSubscriptionsWithoutGateHost:
    """Проверяет, что подписки на классе без OnGateHost вызывают ошибку."""

    def test_subscriptions_without_host_raises(self):
        """@on на классе без OnGateHost отклоняется."""
        # Arrange
        class _NoHost:
            @on("global.start")
            async def on_start(self, event, state, logger):
                pass

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            MetadataBuilder().build(_NoHost)
