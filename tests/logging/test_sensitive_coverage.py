# tests/logging/test_sensitive_coverage.py
"""
Тесты для полного покрытия функциональности декоратора @sensitive и правил доступа к именам с подчёркиванием.
Проверяются 12 комбинаций: атрибуты/свойства с одним/двумя/без подчёркивания, с декоратором (enabled=True/False) и без.
"""

import pytest

from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.log_scope import LogScope
from action_machine.Logging.sensitive_decorator import sensitive
from action_machine.Logging.variable_substitutor import VariableSubstitutor


class TestSensitiveCoverage:
    """Полное покрытие правил доступа и маскировки."""

    @pytest.fixture
    def substitutor(self):
        return VariableSubstitutor()

    @pytest.fixture
    def empty_ctx(self):
        return Context()

    @pytest.fixture
    def empty_scope(self):
        return LogScope()

    @pytest.fixture
    def empty_state(self):
        return BaseState()

    @pytest.fixture
    def empty_params(self):
        return BaseParams()

    # ----------------------------------------------------------------------
    # 1. Атрибуты (поля) – не свойства
    # ----------------------------------------------------------------------

    def test_attr_one_underscore_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Атрибут с одним подчёркиванием в имени -> LogTemplateError."""
        class AttrOneUnderscore:
            def __init__(self):
                self._secret = "value"

        obj = AttrOneUnderscore()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj._secret}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_attr_two_underscores_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Атрибут с двумя подчёркиваниями -> LogTemplateError."""
        class AttrTwoUnderscores:
            def __init__(self):
                self.__secret = "value"

        obj = AttrTwoUnderscores()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj.__secret}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_attr_no_underscore_ok(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Атрибут без подчёркивания выводится без изменений."""
        class AttrPublic:
            def __init__(self):
                self.data = "hello"

        obj = AttrPublic()
        result = substitutor.substitute(
            "{%var.obj.data}",
            {"obj": obj},
            empty_scope, empty_ctx, empty_state, empty_params
        )
        assert result == "hello"

    # ----------------------------------------------------------------------
    # 2. Свойства без декоратора @sensitive
    # ----------------------------------------------------------------------

    def test_prop_no_sensitive_one_underscore_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство без sensitive, имя с одним подчёркиванием -> исключение."""
        class PropNoSensitiveOneUnderscore:
            def __init__(self):
                self._value = "secret"

            @property
            def _prop(self):
                return self._value

        obj = PropNoSensitiveOneUnderscore()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj._prop}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_prop_no_sensitive_two_underscores_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство без sensitive, имя с двумя подчёркиваниями -> исключение."""
        class PropNoSensitiveTwoUnderscores:
            def __init__(self):
                self.__value = "secret"

            @property
            def __prop(self):
                return self.__value

        obj = PropNoSensitiveTwoUnderscores()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj.__prop}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_prop_no_sensitive_public_ok(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство без sensitive, публичное имя -> выводится без изменений."""
        class PropNoSensitivePublic:
            def __init__(self):
                self._value = "hello"

            @property
            def prop(self):
                return self._value

        obj = PropNoSensitivePublic()
        result = substitutor.substitute(
            "{%var.obj.prop}",
            {"obj": obj},
            empty_scope, empty_ctx, empty_state, empty_params
        )
        assert result == "hello"

    # ----------------------------------------------------------------------
    # 3. Свойства с @sensitive enabled=True
    # ----------------------------------------------------------------------

    def test_sensitive_enabled_one_underscore_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство с sensitive enabled=True, имя с одним подчёркиванием -> исключение (приоритет у правила подчёркивания)."""
        class SensitiveEnabledOneUnderscore:
            def __init__(self):
                self._value = "sensitive"

            @property
            @sensitive(True, max_chars=2)
            def _prop(self):
                return self._value

        obj = SensitiveEnabledOneUnderscore()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj._prop}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_sensitive_enabled_two_underscores_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство с sensitive enabled=True, имя с двумя подчёркиваниями -> исключение."""
        class SensitiveEnabledTwoUnderscores:
            def __init__(self):
                self.__value = "sensitive"

            @property
            @sensitive(True, max_chars=2)
            def __prop(self):
                return self.__value

        obj = SensitiveEnabledTwoUnderscores()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj.__prop}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_sensitive_enabled_public_masked(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство с sensitive enabled=True, публичное имя -> маскируется."""
        class SensitiveEnabledPublic:
            def __init__(self):
                self._value = "1234567890"

            @property
            @sensitive(True, max_chars=3, char='*', max_percent=50)
            def phone(self):
                return self._value

        obj = SensitiveEnabledPublic()
        result = substitutor.substitute(
            "{%var.obj.phone}",
            {"obj": obj},
            empty_scope, empty_ctx, empty_state, empty_params
        )
        # Длина 10, max_percent=50 → 5, max_chars=3 → покажем 3 символа.
        assert result == "123*****"

    # ----------------------------------------------------------------------
    # 4. Свойства с @sensitive enabled=False
    # ----------------------------------------------------------------------

    def test_sensitive_disabled_one_underscore_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство с sensitive enabled=False, имя с одним подчёркиванием -> исключение."""
        class SensitiveDisabledOneUnderscore:
            def __init__(self):
                self._value = "sensitive"

            @property
            @sensitive(False, max_chars=2)
            def _prop(self):
                return self._value

        obj = SensitiveDisabledOneUnderscore()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj._prop}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_sensitive_disabled_two_underscores_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство с sensitive enabled=False, имя с двумя подчёркиваниями -> исключение."""
        class SensitiveDisabledTwoUnderscores:
            def __init__(self):
                self.__value = "sensitive"

            @property
            @sensitive(False, max_chars=2)
            def __prop(self):
                return self.__value

        obj = SensitiveDisabledTwoUnderscores()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj.__prop}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_sensitive_disabled_public_not_masked(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Свойство с sensitive enabled=False, публичное имя -> выводится без маски (как обычное свойство)."""
        class SensitiveDisabledPublic:
            def __init__(self):
                self._value = "1234567890"

            @property
            @sensitive(False, max_chars=3, char='*', max_percent=50)
            def phone(self):
                return self._value

        obj = SensitiveDisabledPublic()
        result = substitutor.substitute(
            "{%var.obj.phone}",
            {"obj": obj},
            empty_scope, empty_ctx, empty_state, empty_params
        )
        # Маскировка отключена, должно вернуть исходную строку
        assert result == "1234567890"

    # ----------------------------------------------------------------------
    # Дополнительные тесты для граничных случаев
    # ----------------------------------------------------------------------

    def test_nested_underscore_in_path_raises(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Доступ к вложенному полю, где последний сегмент начинается с _ -> исключение."""
        class Outer:
            def __init__(self):
                self.inner = self.Inner()
            class Inner:
                def __init__(self):
                    self._secret = 42

        obj = Outer()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj.inner._secret}",
                {"obj": obj},
                empty_scope, empty_ctx, empty_state, empty_params
            )

    def test_property_with_underscore_in_middle_ok(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """Имя свойства содержит подчёркивание не в начале, допустимо."""
        class PropWithUnderscore:
            def __init__(self):
                self._value = "ok"

            @property
            def user_name(self):
                return self._value

        obj = PropWithUnderscore()
        result = substitutor.substitute(
            "{%var.obj.user_name}",
            {"obj": obj},
            empty_scope, empty_ctx, empty_state, empty_params
        )
        assert result == "ok"

    def test_sensitive_with_zero_max_chars(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """max_chars=0 означает показывать 0 символов, только маска."""
        class ZeroChars:
            def __init__(self):
                self._value = "12345"

            @property
            @sensitive(True, max_chars=0, char='?', max_percent=100)
            def code(self):
                return self._value

        obj = ZeroChars()
        result = substitutor.substitute(
            "{%var.obj.code}",
            {"obj": obj},
            empty_scope, empty_ctx, empty_state, empty_params
        )
        assert result == "?????"  # 5 символов замены

    def test_sensitive_with_max_percent_zero(self, substitutor, empty_ctx, empty_scope, empty_state, empty_params):
        """max_percent=0 означает показывать 0% (только маска)."""
        class ZeroPercent:
            def __init__(self):
                self._value = "abcdef"

            @property
            @sensitive(True, max_chars=10, char='#', max_percent=0)
            def text(self):
                return self._value

        obj = ZeroPercent()
        result = substitutor.substitute(
            "{%var.obj.text}",
            {"obj": obj},
            empty_scope, empty_ctx, empty_state, empty_params
        )

        # Маска всегда 5 символов, чтобы скрыть длину исходных данных.
        # При max_percent=0 исходная строка заменяется полностью, но маска остаётся длиной 5.
        assert result == "#####"