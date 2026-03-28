# tests/metadata/test_builder_integration.py
"""
Тесты интеграции MetadataBuilder из подпакета action_machine.metadata.

Проверяется:
- Импорт MetadataBuilder из нового расположения работает.
- Сборка метаданных для классов с полным набором декораторов.
- Временные атрибуты остаются после сборки (очистка отключена).
- Повторный вызов build() возвращает эквивалентные метаданные (идемпотентность).
- Совместимость с GateCoordinator.
- Валидация структурных инвариантов работает.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from action_machine.core.class_metadata import ClassMetadata
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.metadata import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class FakeDependencyInfo:
    cls: type
    description: str = ""
    factory: object = None


@dataclass(frozen=True)
class FakeConnectionInfo:
    cls: type
    key: str
    description: str = ""


@dataclass(frozen=True)
class FakeSubscriptionInfo:
    event_type: str
    action_filter: str = ".*"
    ignore_exceptions: bool = True


class FakeServiceA:
    pass


class FakeServiceB:
    pass


class FakeChecker:
    pass


def _make_async_method(name: str, param_count: int = 5):
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


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Импорт
# ═════════════════════════════════════════════════════════════════════════════


class TestImport:

    def test_import_from_metadata_package(self):
        from action_machine.metadata import MetadataBuilder as MB
        assert MB is MetadataBuilder

    def test_import_from_builder_module(self):
        from action_machine.metadata.builder import MetadataBuilder as MB
        assert MB is MetadataBuilder


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Базовая сборка
# ═════════════════════════════════════════════════════════════════════════════


class TestBuilderBasic:

    def test_build_empty_class(self):
        cls = type("EmptyClass", (), {})
        meta = MetadataBuilder.build(cls)
        assert isinstance(meta, ClassMetadata)
        assert meta.class_ref is cls
        assert "EmptyClass" in meta.class_name
        assert meta.role is None
        assert meta.dependencies == ()
        assert meta.aspects == ()

    def test_build_with_role(self):
        cls = type("WithRole", (), {})
        cls._role_info = {"spec": "admin", "desc": "Только админ"}
        meta = MetadataBuilder.build(cls)
        assert meta.has_role() is True
        assert meta.role.spec == "admin"
        assert meta.role.description == "Только админ"

    def test_build_with_dependencies(self):
        cls = type("WithDeps", (), {})
        cls._depends_info = [
            FakeDependencyInfo(cls=FakeServiceA, description="A"),
            FakeDependencyInfo(cls=FakeServiceB, description="B"),
        ]
        meta = MetadataBuilder.build(cls)
        assert meta.has_dependencies() is True
        assert len(meta.dependencies) == 2

    def test_build_with_aspects(self):
        step = _make_async_method("step")
        step._new_aspect_meta = {"type": "regular", "description": "Шаг"}
        finish = _make_async_method("finish")
        finish._new_aspect_meta = {"type": "summary", "description": "Итог"}
        cls = type("WithAspects", (), {"step": step, "finish": finish})
        meta = MetadataBuilder.build(cls)
        assert meta.has_aspects() is True
        assert len(meta.aspects) == 2
        assert meta.get_regular_aspects()[0].method_name == "step"
        assert meta.get_summary_aspect().method_name == "finish"

    def test_build_with_checkers(self):
        process = _make_async_method("process")
        process._new_aspect_meta = {"type": "regular", "description": "Обработка"}
        process._checker_meta = [
            {"checker_class": FakeChecker, "field_name": "txn_id",
             "description": "ID", "required": True},
        ]
        finish = _make_async_method("finish")
        finish._new_aspect_meta = {"type": "summary", "description": "Итог"}
        cls = type("WithCheckers", (), {"process": process, "finish": finish})
        meta = MetadataBuilder.build(cls)
        assert meta.has_checkers() is True
        assert len(meta.checkers) == 1
        assert meta.checkers[0].field_name == "txn_id"

    def test_build_with_subscriptions(self):
        handler = _make_async_method("on_finish", param_count=3)
        handler._on_subscriptions = [
            FakeSubscriptionInfo(event_type="global_finish", action_filter=".*"),
        ]
        cls = type("WithSubs", (), {"on_finish": handler})
        meta = MetadataBuilder.build(cls)
        assert meta.has_subscriptions() is True
        assert len(meta.subscriptions) == 1

    def test_build_with_sensitive(self):
        def getter(self):
            return "secret"
        getter._sensitive_config = {
            "enabled": True, "max_chars": 3, "char": "*", "max_percent": 50,
        }
        cls = type("WithSensitive", (), {"email": property(getter)})
        meta = MetadataBuilder.build(cls)
        assert meta.has_sensitive_fields() is True
        assert len(meta.sensitive_fields) == 1
        assert meta.sensitive_fields[0].property_name == "email"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Идемпотентность (очистка отключена)
# ═════════════════════════════════════════════════════════════════════════════


class TestBuilderIdempotency:
    """Временные атрибуты остаются после build(), повторные вызовы идемпотентны."""

    def test_role_info_preserved(self):
        """_role_info остаётся на классе после build()."""
        cls = type("Action", (), {})
        cls._role_info = {"spec": "user", "desc": ""}
        MetadataBuilder.build(cls)
        assert hasattr(cls, "_role_info")

    def test_depends_info_preserved(self):
        """_depends_info остаётся на классе после build()."""
        cls = type("Action", (), {})
        cls._depends_info = [FakeDependencyInfo(cls=FakeServiceA)]
        MetadataBuilder.build(cls)
        assert "_depends_info" in cls.__dict__

    def test_aspect_meta_preserved(self):
        """_new_aspect_meta остаётся на методе после build()."""
        method = _make_async_method("summary")
        method._new_aspect_meta = {"type": "summary", "description": ""}
        cls = type("Action", (), {"summary": method})
        MetadataBuilder.build(cls)
        assert hasattr(cls.__dict__["summary"], "_new_aspect_meta")

    def test_rebuild_returns_equivalent(self):
        """Повторный build() возвращает эквивалентные метаданные."""
        cls = type("Action", (), {})
        cls._role_info = {"spec": "admin", "desc": ""}
        meta1 = MetadataBuilder.build(cls)
        meta2 = MetadataBuilder.build(cls)
        assert meta1.has_role() is True
        assert meta2.has_role() is True
        assert meta1.role.spec == meta2.role.spec


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Валидация
# ═════════════════════════════════════════════════════════════════════════════


class TestBuilderValidation:

    def test_two_summaries_raises(self):
        m1 = _make_async_method("finish1")
        m1._new_aspect_meta = {"type": "summary", "description": ""}
        m2 = _make_async_method("finish2")
        m2._new_aspect_meta = {"type": "summary", "description": ""}
        cls = type("BadAction", (), {"finish1": m1, "finish2": m2})
        with pytest.raises(ValueError, match="summary-аспектов"):
            MetadataBuilder.build(cls)

    def test_regular_without_summary_raises(self):
        m = _make_async_method("step")
        m._new_aspect_meta = {"type": "regular", "description": ""}
        cls = type("BadAction", (), {"step": m})
        with pytest.raises(ValueError, match="не имеет summary-аспекта"):
            MetadataBuilder.build(cls)

    def test_checker_on_non_aspect_raises(self):
        orphan = _make_async_method("orphan")
        orphan._checker_meta = [
            {"checker_class": FakeChecker, "field_name": "x",
             "description": "", "required": True},
        ]
        summary = _make_async_method("finish")
        summary._new_aspect_meta = {"type": "summary", "description": ""}
        cls = type("BadAction", (), {"orphan": orphan, "finish": summary})
        with pytest.raises(ValueError, match="не является аспектом"):
            MetadataBuilder.build(cls)

    def test_not_a_class_raises(self):
        with pytest.raises(TypeError, match="ожидает класс"):
            MetadataBuilder.build("not_a_class")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Совместимость с GateCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorCompatibility:

    def test_coordinator_uses_new_builder(self):
        coordinator = GateCoordinator()
        cls = type("TestAction", (), {})
        cls._role_info = {"spec": "user", "desc": "Пользователь"}
        summary = _make_async_method("summary")
        summary._new_aspect_meta = {"type": "summary", "description": "Итог"}
        cls.summary = summary
        meta = coordinator.get(cls)
        assert meta.has_role() is True
        assert meta.role.spec == "user"
        assert meta.has_aspects() is True

    def test_coordinator_caches_after_build(self):
        coordinator = GateCoordinator()
        cls = type("CachedAction", (), {})
        cls._role_info = {"spec": "admin", "desc": ""}
        meta1 = coordinator.get(cls)
        meta2 = coordinator.get(cls)
        assert meta1 is meta2
        assert meta1.has_role() is True

    def test_coordinator_invalidate_allows_rebuild(self):
        """После invalidate() повторный get() пересобирает метаданные корректно."""
        coordinator = GateCoordinator()
        cls = type("InvalidateAction", (), {})
        cls._role_info = {"spec": "admin", "desc": ""}
        meta1 = coordinator.get(cls)
        assert meta1.has_role() is True
        coordinator.invalidate(cls)
        meta2 = coordinator.get(cls)
        assert meta2.has_role() is True
        assert meta1 is not meta2
        assert meta1.role.spec == meta2.role.spec

    def test_factory_works_with_new_builder(self):
        coordinator = GateCoordinator()
        cls = type("FactoryAction", (), {})
        cls._depends_info = [FakeDependencyInfo(cls=FakeServiceA, description="A")]
        summary = _make_async_method("summary")
        summary._new_aspect_meta = {"type": "summary", "description": ""}
        cls.summary = summary
        factory = coordinator.get_factory(cls)
        instance = factory.resolve(FakeServiceA)
        assert isinstance(instance, FakeServiceA)
