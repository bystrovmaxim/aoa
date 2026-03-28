# tests/core/test_metadata_and_coordinator.py
"""
Модуль: Тесты для ClassMetadata, MetadataBuilder и GateCoordinator.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Полный набор тестов, покрывающий три компонента:

1. ClassMetadata — иммутабельность, вспомогательные методы, __repr__.
2. MetadataBuilder — сборка метаданных из временных атрибутов, валидация
   структурных инвариантов (summary-аспекты, чекеры без аспектов и т.д.).
3. GateCoordinator — кеширование, ленивая сборка, инвалидация, инспекция.

Тесты используют «чистые» классы, определённые прямо в файле, чтобы
не зависеть от реального BaseAction. Это позволяет тестировать каждый
слой изолированно.

MetadataBuilder импортируется из нового подпакета action_machine.metadata.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from action_machine.core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    ClassMetadata,
    RoleMeta,
    SensitiveFieldMeta,
)
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.metadata import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы для тестов
# ═════════════════════════════════════════════════════════════════════════════


class FakeServiceA:
    pass


class FakeServiceB:
    pass


@dataclass(frozen=True)
class FakeDependencyInfo:
    cls: type
    description: str = ""


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


# ─────────────────────────────────────────────────────────────────────────────
# Фабрики классов с временными атрибутами
# ─────────────────────────────────────────────────────────────────────────────


def _make_async_method(name: str, param_count: int = 5):
    """Создаёт фейковый async-метод с нужным числом параметров."""
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


def _make_class_with_role(spec, desc=""):
    cls = type("ActionWithRole", (), {})
    cls._role_info = {"spec": spec, "desc": desc}
    return cls


def _make_class_with_dependencies(*dep_pairs):
    cls = type("ActionWithDeps", (), {})
    cls._depends_info = [
        FakeDependencyInfo(cls=dep_cls, description=dep_desc)
        for dep_cls, dep_desc in dep_pairs
    ]
    return cls


def _make_class_with_connections(*conn_tuples):
    cls = type("ActionWithConns", (), {})
    cls._connection_info = [
        FakeConnectionInfo(cls=conn_cls, key=conn_key, description=conn_desc)
        for conn_cls, conn_key, conn_desc in conn_tuples
    ]
    return cls


def _make_class_with_aspects(*aspect_defs):
    attrs = {}
    for method_name, aspect_type, description in aspect_defs:
        method = _make_async_method(method_name)
        method._new_aspect_meta = {
            "type": aspect_type,
            "description": description,
        }
        attrs[method_name] = method
    return type("ActionWithAspects", (), attrs)


def _make_class_with_checkers_and_aspects(aspects, checkers):
    attrs = {}
    for method_name, aspect_type, description in aspects:
        method = _make_async_method(method_name)
        method._new_aspect_meta = {
            "type": aspect_type,
            "description": description,
        }
        attrs[method_name] = method

    for method_name, checker_class, field_name, desc, required in checkers:
        method = attrs[method_name]
        if not hasattr(method, "_checker_meta"):
            method._checker_meta = []
        method._checker_meta.append({
            "checker_class": checker_class,
            "field_name": field_name,
            "description": desc,
            "required": required,
        })

    return type("ActionWithCheckers", (), attrs)


def _make_class_with_subscriptions(*sub_defs):
    attrs = {}
    for method_name, event_type, action_filter in sub_defs:
        method = _make_async_method(method_name, param_count=3)
        method._on_subscriptions = [
            FakeSubscriptionInfo(event_type=event_type, action_filter=action_filter)
        ]
        attrs[method_name] = method
    return type("PluginWithSubs", (), attrs)


def _make_class_with_sensitive(*field_defs):
    attrs = {}
    for prop_name, config in field_defs:
        def make_getter(val):
            def getter(self):
                return val
            return getter
        getter = make_getter(f"value_of_{prop_name}")
        getter._sensitive_config = dict(config)
        attrs[prop_name] = property(getter)
    return type("ModelWithSensitive", (), attrs)


class FakeChecker:
    pass


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — создание и иммутабельность
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataCreation:

    def test_minimal_creation(self):
        cls = type("EmptyAction", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.EmptyAction")
        assert meta.class_ref is cls
        assert meta.role is None
        assert meta.dependencies == ()

    def test_full_creation(self):
        cls = type("FullAction", (), {})
        role = RoleMeta(spec="admin", description="Только админ")
        dep = FakeDependencyInfo(cls=FakeServiceA, description="A")
        aspect = AspectMeta(method_name="do_work", aspect_type="regular",
                            description="Работа", method_ref=None)
        checker = CheckerMeta(method_name="do_work", checker_class=FakeChecker,
                              field_name="name", description="Имя",
                              required=True, extra_params={})
        sf = SensitiveFieldMeta(property_name="email",
                                config={"enabled": True, "max_chars": 3,
                                        "char": "*", "max_percent": 50})

        meta = ClassMetadata(
            class_ref=cls, class_name="test.FullAction",
            role=role, dependencies=(dep,), aspects=(aspect,),
            checkers=(checker,), sensitive_fields=(sf,),
        )
        assert meta.role is role
        assert len(meta.dependencies) == 1

    def test_immutability_class_ref(self):
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.class_ref = type("Other", (), {})

    def test_immutability_role(self):
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.role = RoleMeta(spec="hacker", description="")

    def test_immutability_dependencies(self):
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.dependencies = (FakeDependencyInfo(cls=FakeServiceA),)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — вспомогательные методы
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataHelpers:

    def test_has_role(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_role() is False

        with_role = ClassMetadata(class_ref=cls, class_name="test.Test",
                                  role=RoleMeta(spec="admin", description=""))
        assert with_role.has_role() is True

    def test_has_dependencies(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_dependencies() is False

        with_deps = ClassMetadata(class_ref=cls, class_name="test.Test",
                                  dependencies=(FakeDependencyInfo(cls=FakeServiceA),))
        assert with_deps.has_dependencies() is True

    def test_get_regular_aspects(self):
        cls = type("Test", (), {})
        aspects = (
            AspectMeta("step1", "regular", "Шаг 1", None),
            AspectMeta("step2", "regular", "Шаг 2", None),
            AspectMeta("finish", "summary", "Итог", None),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", aspects=aspects)
        regulars = meta.get_regular_aspects()
        assert len(regulars) == 2

    def test_get_summary_aspect(self):
        cls = type("Test", (), {})
        aspects = (
            AspectMeta("step1", "regular", "Шаг 1", None),
            AspectMeta("finish", "summary", "Итог", None),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", aspects=aspects)
        summary = meta.get_summary_aspect()
        assert summary is not None
        assert summary.method_name == "finish"

    def test_get_checkers_for_aspect(self):
        cls = type("Test", (), {})
        checkers = (
            CheckerMeta("step1", FakeChecker, "name", "Имя", True, {}),
            CheckerMeta("step1", FakeChecker, "age", "Возраст", False, {}),
            CheckerMeta("step2", FakeChecker, "email", "Email", True, {}),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", checkers=checkers)
        assert len(meta.get_checkers_for_aspect("step1")) == 2
        assert len(meta.get_checkers_for_aspect("step2")) == 1
        assert len(meta.get_checkers_for_aspect("step3")) == 0

    def test_get_dependency_classes(self):
        cls = type("Test", (), {})
        deps = (FakeDependencyInfo(cls=FakeServiceA), FakeDependencyInfo(cls=FakeServiceB))
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", dependencies=deps)
        assert meta.get_dependency_classes() == (FakeServiceA, FakeServiceB)

    def test_get_connection_keys(self):
        cls = type("Test", (), {})
        conns = (
            FakeConnectionInfo(cls=FakeServiceA, key="db"),
            FakeConnectionInfo(cls=FakeServiceB, key="cache"),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", connections=conns)
        assert meta.get_connection_keys() == ("db", "cache")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — __repr__
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataRepr:

    def test_repr_empty(self):
        cls = type("Empty", (), {})
        r = repr(ClassMetadata(class_ref=cls, class_name="test.Empty"))
        assert "ClassMetadata(test.Empty" in r

    def test_repr_with_role(self):
        cls = type("WithRole", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.WithRole",
                             role=RoleMeta(spec="admin", description=""))
        assert "admin" in repr(meta)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — базовая сборка
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderBasic:

    def test_build_empty_class(self):
        cls = type("PlainClass", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta.class_ref is cls
        assert meta.role is None
        assert meta.dependencies == ()

    def test_build_with_role(self):
        cls = _make_class_with_role("admin", "Только админ")
        meta = MetadataBuilder.build(cls)
        assert meta.role.spec == "admin"

    def test_build_with_dependencies(self):
        cls = _make_class_with_dependencies((FakeServiceA, "A"), (FakeServiceB, "B"))
        meta = MetadataBuilder.build(cls)
        assert len(meta.dependencies) == 2

    def test_build_with_connections(self):
        cls = _make_class_with_connections((FakeServiceA, "db", "БД"))
        meta = MetadataBuilder.build(cls)
        assert meta.get_connection_keys() == ("db",)

    def test_build_not_a_class_raises(self):
        with pytest.raises(TypeError, match="ожидает класс"):
            MetadataBuilder.build("not_a_class")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — аспекты
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderAspects:

    def test_build_regular_and_summary(self):
        cls = _make_class_with_aspects(
            ("validate", "regular", "Валидация"),
            ("process", "regular", "Обработка"),
            ("finish", "summary", "Результат"),
        )
        meta = MetadataBuilder.build(cls)
        assert len(meta.aspects) == 3
        assert len(meta.get_regular_aspects()) == 2
        assert meta.get_summary_aspect().method_name == "finish"

    def test_two_summaries_raises(self):
        cls = _make_class_with_aspects(("f1", "summary", ""), ("f2", "summary", ""))
        with pytest.raises(ValueError, match="summary-аспектов"):
            MetadataBuilder.build(cls)

    def test_regular_without_summary_raises(self):
        cls = _make_class_with_aspects(("step", "regular", ""))
        with pytest.raises(ValueError, match="не имеет summary-аспекта"):
            MetadataBuilder.build(cls)

    def test_summary_not_last_raises(self):
        cls = _make_class_with_aspects(("finish", "summary", ""), ("extra", "regular", ""))
        with pytest.raises(ValueError, match="должен быть объявлен последним"):
            MetadataBuilder.build(cls)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderCheckers:

    def test_checkers_on_aspect(self):
        cls = _make_class_with_checkers_and_aspects(
            aspects=[("process", "regular", ""), ("finish", "summary", "")],
            checkers=[("process", FakeChecker, "txn_id", "ID", True)],
        )
        meta = MetadataBuilder.build(cls)
        assert len(meta.checkers) == 1

    def test_checker_on_non_aspect_raises(self):
        attrs = {}
        method = _make_async_method("orphan")
        method._checker_meta = [{"checker_class": FakeChecker, "field_name": "x",
                                  "description": "", "required": True}]
        attrs["orphan"] = method
        summary = _make_async_method("finish")
        summary._new_aspect_meta = {"type": "summary", "description": ""}
        attrs["finish"] = summary
        cls = type("Bad", (), attrs)
        with pytest.raises(ValueError, match="не является аспектом"):
            MetadataBuilder.build(cls)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — подписки и чувствительные поля
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderSubscriptions:

    def test_single_subscription(self):
        cls = _make_class_with_subscriptions(("on_finish", "global_finish", ".*"))
        meta = MetadataBuilder.build(cls)
        assert len(meta.subscriptions) == 1


class TestMetadataBuilderSensitive:

    def test_single_sensitive_field(self):
        cls = _make_class_with_sensitive(
            ("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}),
        )
        meta = MetadataBuilder.build(cls)
        assert len(meta.sensitive_fields) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — наследование
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderInheritance:

    def test_child_inherits_parent_aspects(self):
        parent = _make_class_with_aspects(("validate", "regular", ""), ("finish", "summary", ""))
        child = type("Child", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert len(meta.aspects) == 2

    def test_child_inherits_role(self):
        parent = _make_class_with_role("admin")
        child = type("Child", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert meta.role.spec == "admin"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — базовое использование
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorBasic:

    def test_get_builds_metadata(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user")
        meta = coordinator.get(cls)
        assert meta.role.spec == "user"

    def test_get_caches_result(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user")
        meta1 = coordinator.get(cls)
        meta2 = coordinator.get(cls)
        assert meta1 is meta2

    def test_has_before_and_after_get(self):
        coordinator = GateCoordinator()
        cls = type("Fresh", (), {})
        assert coordinator.has(cls) is False
        coordinator.get(cls)
        assert coordinator.has(cls) is True

    def test_size(self):
        coordinator = GateCoordinator()
        coordinator.get(type("A", (), {}))
        coordinator.get(type("B", (), {}))
        assert coordinator.size == 2


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — инвалидация
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorInvalidation:

    def test_invalidate_existing(self):
        coordinator = GateCoordinator()
        cls = type("Temp", (), {})
        coordinator.get(cls)
        assert coordinator.invalidate(cls) is True
        assert coordinator.has(cls) is False

    def test_invalidate_non_existing(self):
        coordinator = GateCoordinator()
        assert coordinator.invalidate(type("Unknown", (), {})) is False

    def test_invalidate_all(self):
        coordinator = GateCoordinator()
        for i in range(5):
            coordinator.get(type(f"C{i}", (), {}))
        assert coordinator.invalidate_all() == 5
        assert coordinator.size == 0


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — удобные методы
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorShortcuts:

    def test_get_dependencies(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_dependencies((FakeServiceA, "A"))
        assert len(coordinator.get_dependencies(cls)) == 1

    def test_get_role(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("admin")
        assert coordinator.get_role(cls).spec == "admin"

    def test_get_role_none(self):
        coordinator = GateCoordinator()
        assert coordinator.get_role(type("NoRole", (), {})) is None

    def test_get_aspects(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_aspects(("s", "regular", ""), ("f", "summary", ""))
        assert len(coordinator.get_aspects(cls)) == 2

    def test_get_subscriptions(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_subscriptions(("h", "global_finish", ".*"))
        assert len(coordinator.get_subscriptions(cls)) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — ошибки
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorErrors:

    def test_get_not_a_class_raises(self):
        with pytest.raises(TypeError, match="ожидает класс"):
            GateCoordinator().get("not_a_class")

    def test_structural_error_propagates(self):
        cls = _make_class_with_aspects(("step", "regular", ""))
        with pytest.raises(ValueError, match="не имеет summary-аспекта"):
            GateCoordinator().get(cls)

    def test_structural_error_not_cached(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_aspects(("step", "regular", ""))
        with pytest.raises(ValueError):
            coordinator.get(cls)
        assert coordinator.has(cls) is False


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — __repr__
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorRepr:

    def test_repr_empty(self):
        assert "empty" in repr(GateCoordinator())

    def test_repr_with_classes(self):
        coordinator = GateCoordinator()
        coordinator.get(type("MyAction", (), {}))
        r = repr(coordinator)
        assert "size=1" in r
        assert "MyAction" in r
