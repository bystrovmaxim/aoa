# tests/metadata/test_cleanup.py
"""
Тесты для функции cleanup_temporary_attributes() при явном вызове.

MetadataBuilder.build() НЕ вызывает очистку автоматически — временные
атрибуты остаются на классе для обеспечения идемпотентности повторных
вызовов build(). Функция cleanup_temporary_attributes() доступна
для явного вызова в специальных сценариях (финализация, оптимизация памяти).
"""
from dataclasses import dataclass

from action_machine.metadata.cleanup import cleanup_temporary_attributes

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═════════════════════════════════════════════════════════════════════════════


def _make_async_method(name: str, param_count: int = 5):
    """Создаёт фейковый async-метод."""
    if param_count == 5:
        async def method(self, params, state, box, connections):
            pass
    elif param_count == 3:
        async def method(self, state, event):
            pass
    else:
        async def method(self):
            pass
    method.__name__ = name
    method.__qualname__ = name
    return method


@dataclass(frozen=True)
class FakeDependencyInfo:
    cls: type
    description: str = ""


@dataclass(frozen=True)
class FakeSubscriptionInfo:
    event_type: str
    action_filter: str = ".*"
    ignore_exceptions: bool = True


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Удаление атрибутов уровня класса
# ═════════════════════════════════════════════════════════════════════════════


class TestCleanupClassAttrs:
    """Тесты удаления _role_info, _depends_info, _connection_info при явном вызове."""

    def test_role_info_removed(self):
        cls = type("ActionWithRole", (), {})
        cls._role_info = {"spec": "admin", "desc": ""}
        assert "_role_info" in cls.__dict__
        cleanup_temporary_attributes(cls)
        assert "_role_info" not in cls.__dict__
        assert not hasattr(cls, "_role_info")

    def test_depends_info_removed(self):
        cls = type("ActionWithDeps", (), {})
        cls._depends_info = [FakeDependencyInfo(cls=str)]
        cleanup_temporary_attributes(cls)
        assert "_depends_info" not in cls.__dict__

    def test_connection_info_removed(self):
        cls = type("ActionWithConns", (), {})
        cls._connection_info = []
        cleanup_temporary_attributes(cls)
        assert "_connection_info" not in cls.__dict__

    def test_all_class_attrs_removed(self):
        cls = type("FullAction", (), {})
        cls._role_info = {"spec": "user", "desc": ""}
        cls._depends_info = []
        cls._connection_info = []
        cleanup_temporary_attributes(cls)
        assert "_role_info" not in cls.__dict__
        assert "_depends_info" not in cls.__dict__
        assert "_connection_info" not in cls.__dict__


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Удаление атрибутов уровня методов
# ═════════════════════════════════════════════════════════════════════════════


class TestCleanupMethodAttrs:
    """Тесты удаления _new_aspect_meta, _checker_meta, _on_subscriptions, _sensitive_config."""

    def test_aspect_meta_removed(self):
        method = _make_async_method("validate")
        method._new_aspect_meta = {"type": "regular", "description": "Валидация"}
        cls = type("Action", (), {"validate": method})
        assert hasattr(cls.__dict__["validate"], "_new_aspect_meta")
        cleanup_temporary_attributes(cls)
        assert not hasattr(cls.__dict__["validate"], "_new_aspect_meta")

    def test_checker_meta_removed(self):
        method = _make_async_method("process")
        method._checker_meta = [{"checker_class": type, "field_name": "x"}]
        cls = type("Action", (), {"process": method})
        cleanup_temporary_attributes(cls)
        assert not hasattr(cls.__dict__["process"], "_checker_meta")

    def test_on_subscriptions_removed(self):
        method = _make_async_method("on_finish", param_count=3)
        method._on_subscriptions = [FakeSubscriptionInfo(event_type="global_finish")]
        cls = type("Plugin", (), {"on_finish": method})
        cleanup_temporary_attributes(cls)
        assert not hasattr(cls.__dict__["on_finish"], "_on_subscriptions")

    def test_sensitive_config_removed_from_property(self):
        def getter(self):
            return "secret"
        getter._sensitive_config = {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}
        cls = type("Model", (), {"email": property(getter)})
        prop = cls.__dict__["email"]
        assert hasattr(prop.fget, "_sensitive_config")
        cleanup_temporary_attributes(cls)
        prop_after = cls.__dict__["email"]
        assert not hasattr(prop_after.fget, "_sensitive_config")

    def test_multiple_attrs_on_one_method(self):
        method = _make_async_method("process")
        method._new_aspect_meta = {"type": "regular", "description": ""}
        method._checker_meta = [{"field_name": "x"}]
        cls = type("Action", (), {"process": method})
        cleanup_temporary_attributes(cls)
        assert not hasattr(cls.__dict__["process"], "_new_aspect_meta")
        assert not hasattr(cls.__dict__["process"], "_checker_meta")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Изоляция наследования
# ═════════════════════════════════════════════════════════════════════════════


class TestCleanupInheritanceIsolation:
    """Тесты: унаследованные атрибуты родителя НЕ затрагиваются."""

    def test_parent_role_info_not_removed(self):
        parent = type("Parent", (), {})
        parent._role_info = {"spec": "admin", "desc": ""}
        child = type("Child", (parent,), {})
        assert "_role_info" not in child.__dict__
        assert hasattr(child, "_role_info")
        cleanup_temporary_attributes(child)
        assert "_role_info" in parent.__dict__
        assert parent._role_info == {"spec": "admin", "desc": ""}

    def test_parent_depends_info_not_removed(self):
        parent = type("Parent", (), {})
        parent._depends_info = [FakeDependencyInfo(cls=str)]
        child = type("Child", (parent,), {})
        cleanup_temporary_attributes(child)
        assert "_depends_info" in parent.__dict__
        assert len(parent._depends_info) == 1

    def test_child_own_attr_removed_parent_preserved(self):
        parent = type("Parent", (), {})
        parent._depends_info = [FakeDependencyInfo(cls=str, description="parent")]
        child = type("Child", (parent,), {})
        child._depends_info = list(parent._depends_info) + [
            FakeDependencyInfo(cls=int, description="child")
        ]
        assert "_depends_info" in child.__dict__
        cleanup_temporary_attributes(child)
        assert "_depends_info" not in child.__dict__
        assert "_depends_info" in parent.__dict__
        assert len(parent._depends_info) == 1

    def test_parent_method_attrs_not_removed(self):
        method = _make_async_method("validate")
        method._new_aspect_meta = {"type": "regular", "description": "Parent validate"}
        parent = type("Parent", (), {"validate": method})
        child = type("Child", (parent,), {})
        assert "validate" not in child.__dict__
        cleanup_temporary_attributes(child)
        assert hasattr(parent.__dict__["validate"], "_new_aspect_meta")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Идемпотентность
# ═════════════════════════════════════════════════════════════════════════════


class TestCleanupIdempotency:
    """Тесты: повторный вызов очистки безопасен."""

    def test_double_cleanup_class_attrs(self):
        cls = type("Action", (), {})
        cls._role_info = {"spec": "user", "desc": ""}
        cleanup_temporary_attributes(cls)
        cleanup_temporary_attributes(cls)
        assert not hasattr(cls, "_role_info")

    def test_double_cleanup_method_attrs(self):
        method = _make_async_method("validate")
        method._new_aspect_meta = {"type": "regular", "description": ""}
        cls = type("Action", (), {"validate": method})
        cleanup_temporary_attributes(cls)
        cleanup_temporary_attributes(cls)
        assert not hasattr(cls.__dict__["validate"], "_new_aspect_meta")

    def test_cleanup_empty_class(self):
        cls = type("EmptyClass", (), {})
        cleanup_temporary_attributes(cls)

    def test_cleanup_class_with_regular_methods(self):
        def regular_method(self):
            return 42
        cls = type("PlainClass", (), {"method": regular_method, "value": 42})
        cleanup_temporary_attributes(cls)
        assert cls.__dict__["value"] == 42
        assert callable(cls.__dict__["method"])


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder.build() НЕ удаляет атрибуты
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildDoesNotCleanup:
    """Подтверждение что MetadataBuilder.build() оставляет атрибуты на месте."""

    def test_build_preserves_role_info(self):
        from action_machine.metadata import MetadataBuilder

        cls = type("ActionWithRole", (), {})
        cls._role_info = {"spec": "admin", "desc": "Только админ"}
        metadata = MetadataBuilder.build(cls)
        assert metadata.has_role() is True
        assert metadata.role.spec == "admin"
        assert hasattr(cls, "_role_info")

    def test_build_preserves_aspect_meta(self):
        from action_machine.metadata import MetadataBuilder

        method = _make_async_method("summary")
        method._new_aspect_meta = {"type": "summary", "description": "Итог"}
        cls = type("ActionWithAspect", (), {"summary": method})
        metadata = MetadataBuilder.build(cls)
        assert metadata.has_aspects() is True
        assert hasattr(cls.__dict__["summary"], "_new_aspect_meta")

    def test_build_idempotent(self):
        from action_machine.metadata import MetadataBuilder

        method = _make_async_method("finish")
        method._new_aspect_meta = {"type": "summary", "description": ""}
        cls = type("FullAction", (), {"finish": method})
        cls._role_info = {"spec": "user", "desc": ""}
        cls._depends_info = [FakeDependencyInfo(cls=str)]
        meta1 = MetadataBuilder.build(cls)
        meta2 = MetadataBuilder.build(cls)
        assert meta1.has_role() == meta2.has_role()
        assert meta1.role.spec == meta2.role.spec
        assert len(meta1.dependencies) == len(meta2.dependencies)
