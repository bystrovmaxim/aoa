# tests/metadata/test_metadata_and_coordinator.py
"""
Тесты для ClassMetadata, MetadataBuilder и GateCoordinator.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Полный набор тестов, покрывающий три компонента:

1. ClassMetadata — иммутабельность, вспомогательные методы, __repr__.
2. MetadataBuilder — сборка метаданных из временных атрибутов, валидация
   структурных инвариантов и гейт-хостов.
3. GateCoordinator — кеширование, ленивая сборка, инвалидация, инспекция.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИП СБОРА МЕТАДАННЫХ
═══════════════════════════════════════════════════════════════════════════════

Аспекты, чекеры и подписки собираются ТОЛЬКО из текущего класса (vars(cls)),
без обхода MRO. Потомок не наследует аспекты, чекеры и подписки родителя.

Зависимости, соединения, роли наследуются через getattr (учитывает MRO).
Чувствительные поля наследуются через обход MRO (свойство модели данных).

═══════════════════════════════════════════════════════════════════════════════
ГЕЙТ-ХОСТЫ В ТЕСТОВЫХ КЛАССАХ
═══════════════════════════════════════════════════════════════════════════════

Все тестовые классы с аспектами наследуют AspectGateHost.
Все тестовые классы с чекерами наследуют AspectGateHost и CheckerGateHost.
Все тестовые классы с подписками наследуют OnGateHost.

Это обязательное требование: MetadataBuilder проверяет гейт-хосты
и выбрасывает TypeError при их отсутствии.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    ClassMetadata,
    RoleMeta,
    SensitiveFieldMeta,
)
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.metadata import MetadataBuilder
from action_machine.plugins.on_gate_host import OnGateHost

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
# Фабричные функции для тестовых классов
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
    """Создаёт класс с _role_info."""
    cls = type("ActionWithRole", (), {})
    cls._role_info = {"spec": spec, "desc": desc}
    return cls


def _make_class_with_dependencies(*dep_pairs):
    """Создаёт класс с _depends_info."""
    cls = type("ActionWithDeps", (), {})
    cls._depends_info = [
        FakeDependencyInfo(cls=dep_cls, description=dep_desc)
        for dep_cls, dep_desc in dep_pairs
    ]
    return cls


def _make_class_with_connections(*conn_tuples):
    """Создаёт класс с _connection_info."""
    cls = type("ActionWithConns", (), {})
    cls._connection_info = [
        FakeConnectionInfo(cls=conn_cls, key=conn_key, description=conn_desc)
        for conn_cls, conn_key, conn_desc in conn_tuples
    ]
    return cls


def _make_class_with_aspects(*aspect_defs):
    """
    Создаёт класс с аспектами. Наследует AspectGateHost и CheckerGateHost.

    aspect_defs: кортежи (method_name, aspect_type, description).
    """
    attrs = {}
    for method_name, aspect_type, description in aspect_defs:
        method = _make_async_method(method_name)
        method._new_aspect_meta = {
            "type": aspect_type,
            "description": description,
        }
        attrs[method_name] = method
    return type("ActionWithAspects", (AspectGateHost, CheckerGateHost), attrs)


def _make_class_with_checkers_and_aspects(aspects, checkers):
    """
    Создаёт класс с аспектами и чекерами. Наследует AspectGateHost и CheckerGateHost.

    aspects: список кортежей (method_name, aspect_type, description).
    checkers: список кортежей (method_name, checker_class, field_name, description, required).
    """
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

    return type("ActionWithCheckers", (AspectGateHost, CheckerGateHost), attrs)


def _make_class_with_subscriptions(*sub_defs):
    """
    Создаёт класс с подписками. Наследует OnGateHost.

    sub_defs: кортежи (method_name, event_type, action_filter).
    """
    attrs = {}
    for method_name, event_type, action_filter in sub_defs:
        method = _make_async_method(method_name, param_count=3)
        method._on_subscriptions = [
            FakeSubscriptionInfo(event_type=event_type, action_filter=action_filter)
        ]
        attrs[method_name] = method
    return type("PluginWithSubs", (OnGateHost,), attrs)


def _make_class_with_sensitive(*field_defs):
    """
    Создаёт класс с чувствительными свойствами. Без гейт-хоста — допустимо.

    field_defs: кортежи (property_name, config_dict).
    """
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
        assert meta.class_name == "test.EmptyAction"
        assert meta.role is None
        assert meta.dependencies == ()
        assert meta.connections == ()
        assert meta.aspects == ()
        assert meta.checkers == ()
        assert meta.subscriptions == ()
        assert meta.sensitive_fields == ()
        assert meta.depends_bound is object

    def test_full_creation(self):
        cls = type("FullAction", (), {})
        role = RoleMeta(spec="admin", description="Только админ")
        dep = FakeDependencyInfo(cls=FakeServiceA, description="Сервис A")
        conn = FakeConnectionInfo(cls=FakeServiceB, key="db", description="БД")
        aspect = AspectMeta(method_name="do_work", aspect_type="regular", description="Работа", method_ref=None)
        checker = CheckerMeta(method_name="do_work", checker_class=FakeChecker, field_name="name", description="Имя", required=True, extra_params={})
        sub = FakeSubscriptionInfo(event_type="global_finish")
        sf = SensitiveFieldMeta(property_name="email", config={"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50})

        meta = ClassMetadata(
            class_ref=cls, class_name="test.FullAction", role=role,
            dependencies=(dep,), connections=(conn,), aspects=(aspect,),
            checkers=(checker,), subscriptions=(sub,), sensitive_fields=(sf,),
            depends_bound=object,
        )
        assert meta.role is role
        assert len(meta.dependencies) == 1
        assert len(meta.connections) == 1
        assert len(meta.aspects) == 1
        assert len(meta.checkers) == 1
        assert len(meta.subscriptions) == 1
        assert len(meta.sensitive_fields) == 1

    def test_immutability_class_ref(self):
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.class_ref = type("Other", (), {})

    def test_immutability_class_name(self):
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.class_name = "hacked"

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

    def test_immutability_aspects(self):
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.aspects = ()


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — вспомогательные методы
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataHelpers:

    def test_has_role_false(self):
        cls = type("NoRole", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.NoRole")
        assert meta.has_role() is False

    def test_has_role_true(self):
        cls = type("WithRole", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.WithRole", role=RoleMeta(spec="admin", description=""))
        assert meta.has_role() is True

    def test_has_dependencies(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_dependencies() is False
        with_deps = ClassMetadata(class_ref=cls, class_name="test.Test", dependencies=(FakeDependencyInfo(cls=FakeServiceA),))
        assert with_deps.has_dependencies() is True

    def test_has_connections(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_connections() is False
        with_conns = ClassMetadata(class_ref=cls, class_name="test.Test", connections=(FakeConnectionInfo(cls=FakeServiceA, key="db"),))
        assert with_conns.has_connections() is True

    def test_has_aspects(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_aspects() is False

    def test_has_subscriptions(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_subscriptions() is False

    def test_has_sensitive_fields(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_sensitive_fields() is False

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
        assert all(a.aspect_type == "regular" for a in regulars)

    def test_get_summary_aspect(self):
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.get_summary_aspect() is None
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
        deps = (FakeDependencyInfo(cls=FakeServiceA, description="A"), FakeDependencyInfo(cls=FakeServiceB, description="B"))
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", dependencies=deps)
        assert meta.get_dependency_classes() == (FakeServiceA, FakeServiceB)

    def test_get_connection_keys(self):
        cls = type("Test", (), {})
        conns = (FakeConnectionInfo(cls=FakeServiceA, key="db", description=""), FakeConnectionInfo(cls=FakeServiceB, key="cache", description=""))
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", connections=conns)
        assert meta.get_connection_keys() == ("db", "cache")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — __repr__
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataRepr:

    def test_repr_empty(self):
        cls = type("Empty", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Empty")
        assert "ClassMetadata(test.Empty" in repr(meta)

    def test_repr_with_role(self):
        cls = type("WithRole", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.WithRole", role=RoleMeta(spec="admin", description=""))
        r = repr(meta)
        assert "role=" in r
        assert "admin" in r

    def test_repr_with_deps(self):
        cls = type("WithDeps", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.WithDeps", dependencies=(FakeDependencyInfo(cls=FakeServiceA),))
        r = repr(meta)
        assert "deps=" in r
        assert "FakeServiceA" in r

    def test_repr_with_aspects(self):
        cls = type("WithAspects", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.WithAspects", aspects=(AspectMeta("do_work", "regular", "Работа", None),))
        r = repr(meta)
        assert "aspects=" in r
        assert "regular:do_work" in r


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — базовая сборка
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderBasic:

    def test_build_empty_class(self):
        cls = type("PlainClass", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta.class_ref is cls
        assert "PlainClass" in meta.class_name
        assert meta.role is None
        assert meta.dependencies == ()
        assert meta.connections == ()
        assert meta.aspects == ()
        assert meta.checkers == ()
        assert meta.subscriptions == ()
        assert meta.sensitive_fields == ()

    def test_build_with_role(self):
        cls = _make_class_with_role("admin", "Только админ")
        meta = MetadataBuilder.build(cls)
        assert meta.has_role() is True
        assert meta.role.spec == "admin"
        assert meta.role.description == "Только админ"

    def test_build_with_role_list(self):
        cls = _make_class_with_role(["admin", "manager"], "Админ или менеджер")
        meta = MetadataBuilder.build(cls)
        assert meta.role.spec == ["admin", "manager"]

    def test_build_with_dependencies(self):
        cls = _make_class_with_dependencies((FakeServiceA, "Сервис A"), (FakeServiceB, "Сервис B"))
        meta = MetadataBuilder.build(cls)
        assert meta.has_dependencies() is True
        assert len(meta.dependencies) == 2
        assert meta.dependencies[0].cls is FakeServiceA
        assert meta.dependencies[1].cls is FakeServiceB

    def test_build_with_connections(self):
        cls = _make_class_with_connections((FakeServiceA, "db", "База данных"), (FakeServiceB, "cache", "Кеш"))
        meta = MetadataBuilder.build(cls)
        assert meta.has_connections() is True
        assert len(meta.connections) == 2
        assert meta.get_connection_keys() == ("db", "cache")

    def test_build_not_a_class_raises(self):
        with pytest.raises(TypeError, match="ожидает класс"):
            MetadataBuilder.build("not_a_class")

    def test_build_instance_raises(self):
        with pytest.raises(TypeError, match="ожидает класс"):
            MetadataBuilder.build(FakeServiceA())


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
        assert meta.has_aspects() is True
        assert len(meta.aspects) == 3
        assert len(meta.get_regular_aspects()) == 2
        assert meta.get_summary_aspect().method_name == "finish"

    def test_build_only_summary(self):
        cls = _make_class_with_aspects(("result", "summary", "Результат"))
        meta = MetadataBuilder.build(cls)
        assert len(meta.aspects) == 1
        assert meta.get_summary_aspect().method_name == "result"

    def test_two_summaries_raises(self):
        cls = _make_class_with_aspects(("finish1", "summary", "Итог 1"), ("finish2", "summary", "Итог 2"))
        with pytest.raises(ValueError, match="summary-аспектов"):
            MetadataBuilder.build(cls)

    def test_regular_without_summary_raises(self):
        cls = _make_class_with_aspects(("step1", "regular", "Шаг 1"), ("step2", "regular", "Шаг 2"))
        with pytest.raises(ValueError, match="не имеет summary-аспекта"):
            MetadataBuilder.build(cls)

    def test_summary_not_last_raises(self):
        cls = _make_class_with_aspects(("finish", "summary", "Итог"), ("extra", "regular", "Дополнительно"))
        with pytest.raises(ValueError, match="должен быть объявлен последним"):
            MetadataBuilder.build(cls)

    def test_aspect_preserves_method_ref(self):
        cls = _make_class_with_aspects(("do_work", "regular", "Работа"), ("finish", "summary", "Итог"))
        meta = MetadataBuilder.build(cls)
        for aspect in meta.aspects:
            assert aspect.method_ref is not None
            assert callable(aspect.method_ref)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderCheckers:

    def test_checkers_on_aspect(self):
        cls = _make_class_with_checkers_and_aspects(
            aspects=[("process", "regular", "Обработка"), ("finish", "summary", "Итог")],
            checkers=[
                ("process", FakeChecker, "txn_id", "ID транзакции", True),
                ("process", FakeChecker, "amount", "Сумма", False),
            ],
        )
        meta = MetadataBuilder.build(cls)
        assert meta.has_checkers() is True
        assert len(meta.checkers) == 2
        process_checkers = meta.get_checkers_for_aspect("process")
        assert len(process_checkers) == 2
        assert process_checkers[0].field_name == "txn_id"
        assert process_checkers[1].field_name == "amount"

    def test_checker_on_non_aspect_raises(self):
        attrs = {}
        method = _make_async_method("orphan_method")
        method._checker_meta = [{"checker_class": FakeChecker, "field_name": "name", "description": "Имя", "required": True}]
        attrs["orphan_method"] = method
        summary = _make_async_method("finish")
        summary._new_aspect_meta = {"type": "summary", "description": "Итог"}
        attrs["finish"] = summary
        cls = type("BadCheckerAction", (AspectGateHost, CheckerGateHost), attrs)
        with pytest.raises(ValueError, match="не является аспектом"):
            MetadataBuilder.build(cls)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — подписки
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderSubscriptions:

    def test_single_subscription(self):
        cls = _make_class_with_subscriptions(("on_finish", "global_finish", ".*"))
        meta = MetadataBuilder.build(cls)
        assert meta.has_subscriptions() is True
        assert len(meta.subscriptions) == 1
        assert meta.subscriptions[0].event_type == "global_finish"

    def test_multiple_subscriptions(self):
        cls = _make_class_with_subscriptions(("on_finish", "global_finish", ".*"), ("on_before", "aspect_before", "CreateOrder.*"))
        meta = MetadataBuilder.build(cls)
        assert len(meta.subscriptions) == 2

    def test_no_subscriptions(self):
        cls = type("NoSubs", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta.subscriptions == ()


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — чувствительные поля
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderSensitive:

    def test_single_sensitive_field(self):
        cls = _make_class_with_sensitive(("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}))
        meta = MetadataBuilder.build(cls)
        assert meta.has_sensitive_fields() is True
        assert len(meta.sensitive_fields) == 1
        assert meta.sensitive_fields[0].property_name == "email"
        assert meta.sensitive_fields[0].config["max_chars"] == 3

    def test_multiple_sensitive_fields(self):
        cls = _make_class_with_sensitive(
            ("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}),
            ("phone", {"enabled": True, "max_chars": 4, "char": "#", "max_percent": 100}),
            ("ssn", {"enabled": True, "max_chars": 2, "char": "X", "max_percent": 30}),
        )
        meta = MetadataBuilder.build(cls)
        assert len(meta.sensitive_fields) == 3
        names = [sf.property_name for sf in meta.sensitive_fields]
        assert "email" in names
        assert "phone" in names
        assert "ssn" in names

    def test_no_sensitive_fields(self):
        cls = type("NoSensitive", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta.sensitive_fields == ()


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — наследование
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderInheritance:

    def test_child_does_not_inherit_parent_aspects(self):
        """
        Аспекты НЕ наследуются. Потомок без собственных аспектов
        имеет пустой конвейер, даже если родитель объявлял аспекты.
        Собираются только из vars(cls) текущего класса.
        """
        parent = _make_class_with_aspects(
            ("validate", "regular", "Валидация"),
            ("finish", "summary", "Итог"),
        )
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert len(meta.aspects) == 0

    def test_child_with_own_aspects_ignores_parent(self):
        """
        Потомок с собственными аспектами использует только свои.
        Аспекты родителя полностью игнорируются.
        """
        parent = _make_class_with_aspects(
            ("validate", "regular", "Валидация родителя"),
            ("finish", "summary", "Итог"),
        )
        new_process = _make_async_method("process")
        new_process._new_aspect_meta = {
            "type": "regular",
            "description": "Обработка дочернего",
        }
        new_summary = _make_async_method("summary")
        new_summary._new_aspect_meta = {
            "type": "summary",
            "description": "Итог дочернего",
        }
        child = type("ChildAction", (parent,), {
            "process": new_process,
            "summary": new_summary,
        })
        meta = MetadataBuilder.build(child)
        assert len(meta.aspects) == 2
        names = [a.method_name for a in meta.aspects]
        assert "process" in names
        assert "summary" in names
        # Родительские аспекты отсутствуют
        assert "validate" not in names
        assert "finish" not in names

    def test_child_overrides_parent_aspect_must_redeclare(self):
        """
        Потомок, переопределяющий метод родителя, должен повесить
        декоратор @regular_aspect/@summary_aspect заново. Простое
        переопределение метода без декоратора не делает его аспектом.
        Без summary потомок с regular-аспектом получит ошибку валидации.
        """
        parent = _make_class_with_aspects(
            ("validate", "regular", "Валидация родителя"),
            ("finish", "summary", "Итог"),
        )
        # Потомок переопределяет validate БЕЗ декоратора и добавляет summary
        new_validate = _make_async_method("validate")
        # НЕ прикрепляем _new_aspect_meta — это просто метод, не аспект
        new_summary = _make_async_method("finish")
        new_summary._new_aspect_meta = {
            "type": "summary",
            "description": "Итог дочернего",
        }
        child = type("ChildAction", (parent,), {
            "validate": new_validate,
            "finish": new_summary,
        })
        meta = MetadataBuilder.build(child)
        # Только finish — аспект. validate без декоратора — просто метод.
        assert len(meta.aspects) == 1
        assert meta.aspects[0].method_name == "finish"

    def test_child_inherits_role(self):
        """Роли наследуются через MRO (getattr)."""
        parent = _make_class_with_role("admin", "Только админ")
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert meta.has_role() is True
        assert meta.role.spec == "admin"

    def test_child_inherits_dependencies(self):
        """Зависимости наследуются через MRO (getattr)."""
        parent = _make_class_with_dependencies((FakeServiceA, "Сервис A"))
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert len(meta.dependencies) == 1
        assert meta.dependencies[0].cls is FakeServiceA

    def test_child_inherits_sensitive_fields(self):
        """
        Чувствительные поля наследуются через MRO.
        Это исключение из правила "только свои" — @sensitive
        описывает свойство модели данных, а не конвейер выполнения.
        """
        def email_getter(self):
            return "secret@example.com"
        email_getter._sensitive_config = {
            "enabled": True, "max_chars": 3, "char": "*", "max_percent": 50,
        }
        parent = type("ParentModel", (), {"email": property(email_getter)})
        child = type("ChildModel", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert len(meta.sensitive_fields) == 1
        assert meta.sensitive_fields[0].property_name == "email"

    def test_child_does_not_inherit_subscriptions(self):
        """
        Подписки НЕ наследуются. Потомок плагина без собственных @on
        не имеет подписок, даже если родитель объявлял их.
        """
        parent = _make_class_with_subscriptions(
            ("on_finish", "global_finish", ".*"),
        )
        child = type("ChildPlugin", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert len(meta.subscriptions) == 0


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — базовое использование
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorBasic:

    def test_get_builds_metadata(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user", "Пользователь")
        meta = coordinator.get(cls)
        assert meta.class_ref is cls
        assert meta.role.spec == "user"

    def test_get_caches_result(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user")
        meta1 = coordinator.get(cls)
        meta2 = coordinator.get(cls)
        assert meta1 is meta2

    def test_register_same_as_get(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("admin")
        meta_reg = coordinator.register(cls)
        meta_get = coordinator.get(cls)
        assert meta_reg is meta_get

    def test_has_before_get(self):
        coordinator = GateCoordinator()
        cls = type("Fresh", (), {})
        assert coordinator.has(cls) is False

    def test_has_after_get(self):
        coordinator = GateCoordinator()
        cls = type("Registered", (), {})
        coordinator.get(cls)
        assert coordinator.has(cls) is True

    def test_size(self):
        coordinator = GateCoordinator()
        assert coordinator.size == 0
        cls1 = type("A", (), {})
        cls2 = type("B", (), {})
        coordinator.get(cls1)
        assert coordinator.size == 1
        coordinator.get(cls2)
        assert coordinator.size == 2

    def test_get_all_metadata(self):
        coordinator = GateCoordinator()
        cls1 = type("A", (), {})
        cls2 = type("B", (), {})
        coordinator.get(cls1)
        coordinator.get(cls2)
        assert len(coordinator.get_all_metadata()) == 2

    def test_get_all_classes(self):
        coordinator = GateCoordinator()
        cls1 = type("A", (), {})
        cls2 = type("B", (), {})
        coordinator.get(cls1)
        coordinator.get(cls2)
        classes = coordinator.get_all_classes()
        assert cls1 in classes
        assert cls2 in classes


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
        cls = type("Unknown", (), {})
        assert coordinator.invalidate(cls) is False

    def test_invalidate_allows_rebuild(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user")
        meta1 = coordinator.get(cls)
        coordinator.invalidate(cls)
        meta2 = coordinator.get(cls)
        assert meta1 is not meta2
        assert meta1.role.spec == meta2.role.spec

    def test_invalidate_all(self):
        coordinator = GateCoordinator()
        for i in range(5):
            coordinator.get(type(f"Class{i}", (), {}))
        assert coordinator.invalidate_all() == 5
        assert coordinator.size == 0

    def test_invalidate_all_empty(self):
        coordinator = GateCoordinator()
        assert coordinator.invalidate_all() == 0


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — удобные методы
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorShortcuts:

    def test_get_dependencies(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_dependencies((FakeServiceA, "A"), (FakeServiceB, "B"))
        assert len(coordinator.get_dependencies(cls)) == 2

    def test_get_connections(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_connections((FakeServiceA, "db", "БД"))
        assert len(coordinator.get_connections(cls)) == 1

    def test_get_role(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_role("admin", "Админ")
        role = coordinator.get_role(cls)
        assert role is not None
        assert role.spec == "admin"

    def test_get_role_none(self):
        coordinator = GateCoordinator()
        cls = type("NoRole", (), {})
        assert coordinator.get_role(cls) is None

    def test_get_aspects(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_aspects(("step", "regular", "Шаг"), ("finish", "summary", "Итог"))
        assert len(coordinator.get_aspects(cls)) == 2

    def test_get_subscriptions(self):
        coordinator = GateCoordinator()
        cls = _make_class_with_subscriptions(("on_finish", "global_finish", ".*"))
        assert len(coordinator.get_subscriptions(cls)) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — ошибки
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorErrors:

    def test_get_not_a_class_raises(self):
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="ожидает класс"):
            coordinator.get("not_a_class")

    def test_get_instance_raises(self):
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="ожидает класс"):
            coordinator.get(FakeServiceA())

    def test_get_none_raises(self):
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="ожидает класс"):
            coordinator.get(None)

    def test_structural_error_propagates(self):
        """Regular-аспект без summary — ValueError (гейт-хост есть)."""
        cls = _make_class_with_aspects(("step1", "regular", "Шаг"))
        coordinator = GateCoordinator()
        with pytest.raises(ValueError, match="не имеет summary-аспекта"):
            coordinator.get(cls)

    def test_structural_error_not_cached(self):
        """
        При ошибке сборки метаданные не должны оставаться в кеше.
        GateCoordinator помещает метаданные в кеш ДО валидации
        (для защиты от циклических зависимостей), но при ошибке
        должен удалить их.
        """
        cls = _make_class_with_aspects(("step1", "regular", "Шаг"))
        coordinator = GateCoordinator()
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
        cls = type("MyAction", (), {})
        coordinator.get(cls)
        r = repr(coordinator)
        assert "size=1" in r
        assert "MyAction" in r
