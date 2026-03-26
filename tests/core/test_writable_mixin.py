# tests/core/test_writable_mixin.py
import pytest

from action_machine.core.base_state import BaseState


class TestWritableMixin:
    def test_setitem_sets_existing_attribute(self):
        state = BaseState({"existing": "value"})
        state["existing"] = "new"
        assert state.existing == "new"

    def test_setitem_creates_new_attribute(self):
        state = BaseState()
        state["new_attr"] = 42
        assert state.new_attr == 42

    def test_delitem(self):
        state = BaseState({"temp": True})
        del state["temp"]
        assert "temp" not in state
        with pytest.raises(KeyError):
            del state["missing"]

    def test_write_with_allowed_keys(self):
        state = BaseState()
        # Разрешенная запись
        state.write("total", 1500, allowed_keys=["total", "discount"])
        assert state.total == 1500

        # Запрещенная запись
        with pytest.raises(KeyError, match="не входит в список разрешённых"):
            state.write("secret", 42, allowed_keys=["total", "discount"])

    def test_update_mass_assignment(self):
        state = BaseState()
        state.update({"a": 1, "b": 2})
        assert state.a == 1
        assert state.b == 2
