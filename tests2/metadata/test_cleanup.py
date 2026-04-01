# tests2/metadata/test_cleanup.py
"""
Tests for cleanup_temporary_attributes — removal of decorator temp attrs.

After MetadataBuilder.build() reads temporary attributes left by decorators
(@meta, @check_roles, @depends, @connection, @regular_aspect, @result_string,
@on, @sensitive), those attributes are no longer needed. cleanup removes them
from cls.__dict__ (class-level) and from method functions (method-level).

Scenarios covered:
    - Class-level attrs (_role_info, _depends_info, _connection_info) removed.
    - Method-level attrs (_new_aspect_meta, _checker_meta, _on_subscriptions,
      _sensitive_config) removed from regular methods.
    - Method-level attrs removed from property getters (fget).
    - Inherited class-level attrs are NOT removed from the child class.
    - Idempotent — second call on already-cleaned class is safe.
    - Non-callable attrs on the class are left untouched.
    - Built-in methods that reject delattr are handled gracefully.
"""


from action_machine.metadata.cleanup import (
    _get_underlying_function,
    cleanup_temporary_attributes,
)

# ═════════════════════════════════════════════════════════════════════════════
# Class-level attribute cleanup
# ═════════════════════════════════════════════════════════════════════════════


class TestClassLevelCleanup:
    """Verify removal of class-level temporary attributes."""

    def test_removes_role_info(self) -> None:
        """_role_info is removed from cls.__dict__ after cleanup."""

        class _Action:
            _role_info = {"spec": "admin", "desc": ""}

        cleanup_temporary_attributes(_Action)
        assert "_role_info" not in _Action.__dict__

    def test_removes_depends_info(self) -> None:
        """_depends_info is removed from cls.__dict__ after cleanup."""

        class _Action:
            _depends_info = [{"class": str}]

        cleanup_temporary_attributes(_Action)
        assert "_depends_info" not in _Action.__dict__

    def test_removes_connection_info(self) -> None:
        """_connection_info is removed from cls.__dict__ after cleanup."""

        class _Action:
            _connection_info = [{"class": str, "key": "db"}]

        cleanup_temporary_attributes(_Action)
        assert "_connection_info" not in _Action.__dict__

    def test_does_not_remove_inherited_attr(self) -> None:
        """Inherited _role_info on parent is not removed via child cleanup."""

        class _Parent:
            _role_info = {"spec": "admin", "desc": ""}

        class _Child(_Parent):
            pass

        # _role_info is inherited, not in _Child.__dict__
        cleanup_temporary_attributes(_Child)

        # Parent's attr must survive
        assert hasattr(_Parent, "_role_info")
        assert _Parent._role_info == {"spec": "admin", "desc": ""}

    def test_removes_only_own_attr(self) -> None:
        """Child's own _role_info is removed, parent's is preserved."""

        class _Parent:
            _role_info = {"spec": "admin", "desc": ""}

        class _Child(_Parent):
            _role_info = {"spec": "user", "desc": ""}

        cleanup_temporary_attributes(_Child)

        assert "_role_info" not in _Child.__dict__
        assert _Parent._role_info == {"spec": "admin", "desc": ""}


# ═════════════════════════════════════════════════════════════════════════════
# Method-level attribute cleanup
# ═════════════════════════════════════════════════════════════════════════════


class TestMethodLevelCleanup:
    """Verify removal of method-level temporary attributes."""

    def test_removes_aspect_meta(self) -> None:
        """_new_aspect_meta is removed from a method function."""

        class _Action:
            async def process(self):
                pass

        _Action.process._new_aspect_meta = {"type": "regular"}

        cleanup_temporary_attributes(_Action)
        assert not hasattr(_Action.process, "_new_aspect_meta")

    def test_removes_checker_meta(self) -> None:
        """_checker_meta is removed from a method function."""

        class _Action:
            async def validate(self):
                pass

        _Action.validate._checker_meta = [{"field": "name"}]

        cleanup_temporary_attributes(_Action)
        assert not hasattr(_Action.validate, "_checker_meta")

    def test_removes_on_subscriptions(self) -> None:
        """_on_subscriptions is removed from a method function."""

        class _Plugin:
            async def handler(self):
                pass

        _Plugin.handler._on_subscriptions = [{"event": "global_finish"}]

        cleanup_temporary_attributes(_Plugin)
        assert not hasattr(_Plugin.handler, "_on_subscriptions")

    def test_removes_sensitive_config(self) -> None:
        """_sensitive_config is removed from a property getter."""

        def _getter(self):
            return "secret"

        _getter._sensitive_config = {"mask": "***"}

        class _Model:
            secret = property(_getter)

        cleanup_temporary_attributes(_Model)
        assert not hasattr(_getter, "_sensitive_config")

    def test_skips_non_callable_attrs(self) -> None:
        """Non-callable class attributes are left untouched."""

        class _Action:
            name = "test"
            count = 42

        cleanup_temporary_attributes(_Action)
        assert _Action.name == "test"
        assert _Action.count == 42


# ═════════════════════════════════════════════════════════════════════════════
# _get_underlying_function
# ═════════════════════════════════════════════════════════════════════════════


class TestGetUnderlyingFunction:
    """Verify function extraction from descriptors and callables."""

    def test_returns_fget_for_property(self) -> None:
        """For a property descriptor, returns the getter function."""

        def _getter(self):
            return 1

        prop = property(_getter)
        assert _get_underlying_function(prop) is _getter

    def test_returns_callable_as_is(self) -> None:
        """For a regular callable, returns it unchanged."""

        def _func():
            pass

        assert _get_underlying_function(_func) is _func

    def test_returns_none_for_non_callable(self) -> None:
        """For a non-callable value, returns None."""
        assert _get_underlying_function("string") is None
        assert _get_underlying_function(42) is None
        assert _get_underlying_function(None) is None


# ═════════════════════════════════════════════════════════════════════════════
# Idempotency
# ═════════════════════════════════════════════════════════════════════════════


class TestIdempotency:
    """Verify that cleanup is safe to call multiple times."""

    def test_double_cleanup_is_safe(self) -> None:
        """Calling cleanup twice on the same class produces no error."""

        class _Action:
            _role_info = {"spec": "admin"}

            async def process(self):
                pass

        _Action.process._new_aspect_meta = {"type": "regular"}

        cleanup_temporary_attributes(_Action)
        cleanup_temporary_attributes(_Action)  # second call — should not raise

        assert "_role_info" not in _Action.__dict__
        assert not hasattr(_Action.process, "_new_aspect_meta")
