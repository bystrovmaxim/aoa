# tests/core/test_metadata_and_coordinator.py
"""
Модуль: Тесты для ClassMetadata, MetadataBuilder и GateCoordinator.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Полный набор тестов, покрывающий три компонента фазы «координатор»:

1. ClassMetadata — иммутабельность, вспомогательные методы, __repr__.
2. MetadataBuilder — сборка метаданных из временных атрибутов, валидация
   структурных инвариантов (summary-аспекты, чекеры без аспектов и т.д.).
3. GateCoordinator — кеширование, ленивая сборка, инвалидация, инспекция.

Тесты используют «чистые» классы, определённые прямо в файле, чтобы
не зависеть от реального BaseAction (который тянет за собой всю цепочку
миксинов). Это позволяет тестировать каждый слой изолированно.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════

    TestClassMetadataCreation       — создание и иммутабельность
    TestClassMetadataHelpers        — вспомогательные методы (has_*, get_*)
    TestClassMetadataRepr           — строковое представление
    TestMetadataBuilderBasic        — базовая сборка (пустой класс, с ролями, ...)
    TestMetadataBuilderAspects      — сборка аспектов и валидация инвариантов
    TestMetadataBuilderCheckers     — сборка чекеров и привязка к аспектам
    TestMetadataBuilderSubscriptions — сборка подписок (@on)
    TestMetadataBuilderSensitive    — сборка чувствительных полей
    TestMetadataBuilderInheritance  — наследование метаданных
    TestMetadataBuilderErrors       — ошибки при невалидных входных данных
    TestGateCoordinatorBasic        — get, кеширование, register
    TestGateCoordinatorInvalidation — invalidate, invalidate_all
    TestGateCoordinatorShortcuts    — удобные методы (get_dependencies, ...)
    TestGateCoordinatorErrors       — ошибки (не-класс, структурные проблемы)
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from action_machine.Core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    ClassMetadata,
    RoleMeta,
    SensitiveFieldMeta,
)
from action_machine.Core.gate_coordinator import GateCoordinator
from action_machine.Core.metadata_builder import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы для тестов
# ═════════════════════════════════════════════════════════════════════════════


class FakeServiceA:
    """Фейковый сервис A для тестирования зависимостей."""
    pass


class FakeServiceB:
    """Фейковый сервис B для тестирования зависимостей."""
    pass


@dataclass(frozen=True)
class FakeDependencyInfo:
    """
    Имитация DependencyInfo для тестов, не зависящая от реального модуля.
    Поля совпадают с настоящим DependencyInfo.
    """
    cls: type
    description: str = ""


@dataclass(frozen=True)
class FakeConnectionInfo:
    """
    Имитация ConnectionInfo для тестов.
    Поля совпадают с настоящим ConnectionInfo.
    """
    cls: type
    key: str
    description: str = ""


@dataclass(frozen=True)
class FakeSubscriptionInfo:
    """
    Имитация SubscriptionInfo для тестов.
    """
    event_type: str
    action_filter: str = ".*"
    ignore_exceptions: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Классы, имитирующие декорированные Action/Plugin
# ─────────────────────────────────────────────────────────────────────────────


def _make_async_method(name: str, param_count: int = 5):
    """
    Создаёт фейковый async-метод с нужным числом параметров.
    Используется для имитации аспектов без реальных декораторов.
    """
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
    """Создаёт класс с _role_info, как после @CheckRoles."""
    cls = type("ActionWithRole", (), {})
    cls._role_info = {"spec": spec, "desc": desc}
    return cls


def _make_class_with_dependencies(*dep_pairs):
    """
    Создаёт класс с _depends_info, как после @depends.
    dep_pairs: кортежи (cls, description).
    """
    cls = type("ActionWithDeps", (), {})
    cls._depends_info = [
        FakeDependencyInfo(cls=dep_cls, description=dep_desc)
        for dep_cls, dep_desc in dep_pairs
    ]
    return cls


def _make_class_with_connections(*conn_tuples):
    """
    Создаёт класс с _connection_info, как после @connection.
    conn_tuples: кортежи (cls, key, description).
    """
    cls = type("ActionWithConns", (), {})
    cls._connection_info = [
        FakeConnectionInfo(cls=conn_cls, key=conn_key, description=conn_desc)
        for conn_cls, conn_key, conn_desc in conn_tuples
    ]
    return cls


def _make_class_with_aspects(*aspect_defs):
    """
    Создаёт класс с методами, помеченными _new_aspect_meta.
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
    return type("ActionWithAspects", (), attrs)


def _make_class_with_checkers_and_aspects(aspects, checkers):
    """
    Создаёт класс с аспектами и чекерами.
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

    # Навешиваем чекеры на уже созданные методы
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
    """
    Создаёт класс с методами, помеченными _on_subscriptions.
    sub_defs: кортежи (method_name, event_type, action_filter).
    """
    attrs = {}
    for method_name, event_type, action_filter in sub_defs:
        method = _make_async_method(method_name, param_count=3)
        method._on_subscriptions = [
            FakeSubscriptionInfo(event_type=event_type, action_filter=action_filter)
        ]
        attrs[method_name] = method
    return type("PluginWithSubs", (), attrs)


def _make_class_with_sensitive(*field_defs):
    """
    Создаёт класс с property, помеченными _sensitive_config.
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
    """Имитация класса чекера."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — создание и иммутабельность
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataCreation:
    """Тесты создания ClassMetadata и проверки иммутабельности."""

    def test_minimal_creation(self):
        """ClassMetadata можно создать с минимальными параметрами."""
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
        """ClassMetadata можно создать со всеми полями."""
        cls = type("FullAction", (), {})
        role = RoleMeta(spec="admin", description="Только админ")
        dep = FakeDependencyInfo(cls=FakeServiceA, description="Сервис A")
        conn = FakeConnectionInfo(cls=FakeServiceB, key="db", description="БД")
        aspect = AspectMeta(
            method_name="do_work",
            aspect_type="regular",
            description="Работа",
            method_ref=None,
        )
        checker = CheckerMeta(
            method_name="do_work",
            checker_class=FakeChecker,
            field_name="name",
            description="Имя",
            required=True,
            extra_params={},
        )
        sub = FakeSubscriptionInfo(event_type="global_finish")
        sf = SensitiveFieldMeta(
            property_name="email",
            config={"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50},
        )

        meta = ClassMetadata(
            class_ref=cls,
            class_name="test.FullAction",
            role=role,
            dependencies=(dep,),
            connections=(conn,),
            aspects=(aspect,),
            checkers=(checker,),
            subscriptions=(sub,),
            sensitive_fields=(sf,),
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
        """Поле class_ref нельзя изменить после создания."""
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.class_ref = type("Other", (), {})

    def test_immutability_class_name(self):
        """Поле class_name нельзя изменить после создания."""
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.class_name = "hacked"

    def test_immutability_role(self):
        """Поле role нельзя изменить после создания."""
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.role = RoleMeta(spec="hacker", description="")

    def test_immutability_dependencies(self):
        """Поле dependencies нельзя изменить после создания."""
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.dependencies = (FakeDependencyInfo(cls=FakeServiceA),)

    def test_immutability_aspects(self):
        """Поле aspects нельзя изменить после создания."""
        cls = type("Immutable", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Immutable")
        with pytest.raises(FrozenInstanceError):
            meta.aspects = ()


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — вспомогательные методы
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataHelpers:
    """Тесты вспомогательных методов ClassMetadata."""

    def test_has_role_false(self):
        """has_role() возвращает False если role=None."""
        cls = type("NoRole", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.NoRole")
        assert meta.has_role() is False

    def test_has_role_true(self):
        """has_role() возвращает True если роль назначена."""
        cls = type("WithRole", (), {})
        meta = ClassMetadata(
            class_ref=cls,
            class_name="test.WithRole",
            role=RoleMeta(spec="admin", description=""),
        )
        assert meta.has_role() is True

    def test_has_dependencies(self):
        """has_dependencies() корректно отражает наличие зависимостей."""
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_dependencies() is False

        with_deps = ClassMetadata(
            class_ref=cls,
            class_name="test.Test",
            dependencies=(FakeDependencyInfo(cls=FakeServiceA),),
        )
        assert with_deps.has_dependencies() is True

    def test_has_connections(self):
        """has_connections() корректно отражает наличие соединений."""
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_connections() is False

        with_conns = ClassMetadata(
            class_ref=cls,
            class_name="test.Test",
            connections=(FakeConnectionInfo(cls=FakeServiceA, key="db"),),
        )
        assert with_conns.has_connections() is True

    def test_has_aspects(self):
        """has_aspects() корректно отражает наличие аспектов."""
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_aspects() is False

    def test_has_subscriptions(self):
        """has_subscriptions() корректно отражает наличие подписок."""
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_subscriptions() is False

    def test_has_sensitive_fields(self):
        """has_sensitive_fields() корректно отражает наличие чувствительных полей."""
        cls = type("Test", (), {})
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.has_sensitive_fields() is False

    def test_get_regular_aspects(self):
        """get_regular_aspects() возвращает только regular-аспекты."""
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
        """get_summary_aspect() возвращает summary или None."""
        cls = type("Test", (), {})

        # Без аспектов
        empty = ClassMetadata(class_ref=cls, class_name="test.Test")
        assert empty.get_summary_aspect() is None

        # С summary
        aspects = (
            AspectMeta("step1", "regular", "Шаг 1", None),
            AspectMeta("finish", "summary", "Итог", None),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", aspects=aspects)
        summary = meta.get_summary_aspect()
        assert summary is not None
        assert summary.method_name == "finish"
        assert summary.aspect_type == "summary"

    def test_get_checkers_for_aspect(self):
        """get_checkers_for_aspect() возвращает чекеры для конкретного метода."""
        cls = type("Test", (), {})
        checkers = (
            CheckerMeta("step1", FakeChecker, "name", "Имя", True, {}),
            CheckerMeta("step1", FakeChecker, "age", "Возраст", False, {}),
            CheckerMeta("step2", FakeChecker, "email", "Email", True, {}),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", checkers=checkers)

        step1_checkers = meta.get_checkers_for_aspect("step1")
        assert len(step1_checkers) == 2

        step2_checkers = meta.get_checkers_for_aspect("step2")
        assert len(step2_checkers) == 1

        missing_checkers = meta.get_checkers_for_aspect("step3")
        assert len(missing_checkers) == 0

    def test_get_dependency_classes(self):
        """get_dependency_classes() возвращает кортеж классов зависимостей."""
        cls = type("Test", (), {})
        deps = (
            FakeDependencyInfo(cls=FakeServiceA, description="A"),
            FakeDependencyInfo(cls=FakeServiceB, description="B"),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", dependencies=deps)
        classes = meta.get_dependency_classes()
        assert classes == (FakeServiceA, FakeServiceB)

    def test_get_connection_keys(self):
        """get_connection_keys() возвращает кортеж ключей соединений."""
        cls = type("Test", (), {})
        conns = (
            FakeConnectionInfo(cls=FakeServiceA, key="db", description=""),
            FakeConnectionInfo(cls=FakeServiceB, key="cache", description=""),
        )
        meta = ClassMetadata(class_ref=cls, class_name="test.Test", connections=conns)
        keys = meta.get_connection_keys()
        assert keys == ("db", "cache")


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ClassMetadata — __repr__
# ═════════════════════════════════════════════════════════════════════════════


class TestClassMetadataRepr:
    """Тесты строкового представления ClassMetadata."""

    def test_repr_empty(self):
        """__repr__ для пустого ClassMetadata."""
        cls = type("Empty", (), {})
        meta = ClassMetadata(class_ref=cls, class_name="test.Empty")
        r = repr(meta)
        assert "ClassMetadata(test.Empty" in r

    def test_repr_with_role(self):
        """__repr__ отображает роль."""
        cls = type("WithRole", (), {})
        meta = ClassMetadata(
            class_ref=cls,
            class_name="test.WithRole",
            role=RoleMeta(spec="admin", description=""),
        )
        r = repr(meta)
        assert "role=" in r
        assert "admin" in r

    def test_repr_with_deps(self):
        """__repr__ отображает зависимости."""
        cls = type("WithDeps", (), {})
        meta = ClassMetadata(
            class_ref=cls,
            class_name="test.WithDeps",
            dependencies=(FakeDependencyInfo(cls=FakeServiceA),),
        )
        r = repr(meta)
        assert "deps=" in r
        assert "FakeServiceA" in r

    def test_repr_with_aspects(self):
        """__repr__ отображает аспекты."""
        cls = type("WithAspects", (), {})
        meta = ClassMetadata(
            class_ref=cls,
            class_name="test.WithAspects",
            aspects=(AspectMeta("do_work", "regular", "Работа", None),),
        )
        r = repr(meta)
        assert "aspects=" in r
        assert "regular:do_work" in r


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — базовая сборка
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderBasic:
    """Тесты базовой сборки MetadataBuilder."""

    def test_build_empty_class(self):
        """Сборка пустого класса (без декораторов) — все поля пустые."""
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
        """Сборка класса с _role_info."""
        cls = _make_class_with_role("admin", "Только админ")
        meta = MetadataBuilder.build(cls)

        assert meta.has_role() is True
        assert meta.role.spec == "admin"
        assert meta.role.description == "Только админ"

    def test_build_with_role_list(self):
        """Сборка класса с ролью-списком."""
        cls = _make_class_with_role(["admin", "manager"], "Админ или менеджер")
        meta = MetadataBuilder.build(cls)

        assert meta.role.spec == ["admin", "manager"]

    def test_build_with_dependencies(self):
        """Сборка класса с _depends_info."""
        cls = _make_class_with_dependencies(
            (FakeServiceA, "Сервис A"),
            (FakeServiceB, "Сервис B"),
        )
        meta = MetadataBuilder.build(cls)

        assert meta.has_dependencies() is True
        assert len(meta.dependencies) == 2
        assert meta.dependencies[0].cls is FakeServiceA
        assert meta.dependencies[1].cls is FakeServiceB

    def test_build_with_connections(self):
        """Сборка класса с _connection_info."""
        cls = _make_class_with_connections(
            (FakeServiceA, "db", "База данных"),
            (FakeServiceB, "cache", "Кеш"),
        )
        meta = MetadataBuilder.build(cls)

        assert meta.has_connections() is True
        assert len(meta.connections) == 2
        assert meta.get_connection_keys() == ("db", "cache")

    def test_build_not_a_class_raises(self):
        """build() с не-классом вызывает TypeError."""
        with pytest.raises(TypeError, match="ожидает класс"):
            MetadataBuilder.build("not_a_class")

    def test_build_instance_raises(self):
        """build() с экземпляром вызывает TypeError."""
        obj = FakeServiceA()
        with pytest.raises(TypeError, match="ожидает класс"):
            MetadataBuilder.build(obj)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — аспекты
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderAspects:
    """Тесты сборки и валидации аспектов."""

    def test_build_regular_and_summary(self):
        """Сборка класса с regular и summary аспектами."""
        cls = _make_class_with_aspects(
            ("validate", "regular", "Валидация"),
            ("process", "regular", "Обработка"),
            ("finish", "summary", "Результат"),
        )
        meta = MetadataBuilder.build(cls)

        assert meta.has_aspects() is True
        assert len(meta.aspects) == 3
        regulars = meta.get_regular_aspects()
        assert len(regulars) == 2
        summary = meta.get_summary_aspect()
        assert summary is not None
        assert summary.method_name == "finish"

    def test_build_only_summary(self):
        """Класс только с summary-аспектом — допустимо."""
        cls = _make_class_with_aspects(
            ("result", "summary", "Результат"),
        )
        meta = MetadataBuilder.build(cls)
        assert len(meta.aspects) == 1
        assert meta.get_summary_aspect().method_name == "result"

    def test_two_summaries_raises(self):
        """Два summary-аспекта — ошибка."""
        cls = _make_class_with_aspects(
            ("finish1", "summary", "Итог 1"),
            ("finish2", "summary", "Итог 2"),
        )
        with pytest.raises(ValueError, match="summary-аспектов"):
            MetadataBuilder.build(cls)

    def test_regular_without_summary_raises(self):
        """Regular-аспекты без summary — ошибка."""
        cls = _make_class_with_aspects(
            ("step1", "regular", "Шаг 1"),
            ("step2", "regular", "Шаг 2"),
        )
        with pytest.raises(ValueError, match="не имеет summary-аспекта"):
            MetadataBuilder.build(cls)

    def test_summary_not_last_raises(self):
        """Summary-аспект не последний — ошибка."""
        cls = _make_class_with_aspects(
            ("finish", "summary", "Итог"),
            ("extra", "regular", "Дополнительно"),
        )
        with pytest.raises(ValueError, match="должен быть объявлен последним"):
            MetadataBuilder.build(cls)

    def test_aspect_preserves_method_ref(self):
        """AspectMeta хранит ссылку на метод."""
        cls = _make_class_with_aspects(
            ("do_work", "regular", "Работа"),
            ("finish", "summary", "Итог"),
        )
        meta = MetadataBuilder.build(cls)
        for aspect in meta.aspects:
            assert aspect.method_ref is not None
            assert callable(aspect.method_ref)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — чекеры
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderCheckers:
    """Тесты сборки чекеров и привязки к аспектам."""

    def test_checkers_on_aspect(self):
        """Чекеры на аспекте собираются корректно."""
        cls = _make_class_with_checkers_and_aspects(
            aspects=[
                ("process", "regular", "Обработка"),
                ("finish", "summary", "Итог"),
            ],
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
        assert process_checkers[0].required is True
        assert process_checkers[1].field_name == "amount"
        assert process_checkers[1].required is False

    def test_checker_on_non_aspect_raises(self):
        """Чекер на методе без аспекта — ошибка."""
        attrs = {}

        # Метод с чекером, но без аспекта
        method = _make_async_method("orphan_method")
        method._checker_meta = [{
            "checker_class": FakeChecker,
            "field_name": "name",
            "description": "Имя",
            "required": True,
        }]
        attrs["orphan_method"] = method

        # Аспект и summary (чтобы пройти валидацию аспектов)
        summary = _make_async_method("finish")
        summary._new_aspect_meta = {"type": "summary", "description": "Итог"}
        attrs["finish"] = summary

        cls = type("BadCheckerAction", (), attrs)
        with pytest.raises(ValueError, match="не является аспектом"):
            MetadataBuilder.build(cls)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — подписки
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderSubscriptions:
    """Тесты сборки подписок (@on)."""

    def test_single_subscription(self):
        """Одна подписка собирается корректно."""
        cls = _make_class_with_subscriptions(
            ("on_finish", "global_finish", ".*"),
        )
        meta = MetadataBuilder.build(cls)

        assert meta.has_subscriptions() is True
        assert len(meta.subscriptions) == 1
        assert meta.subscriptions[0].event_type == "global_finish"

    def test_multiple_subscriptions(self):
        """Несколько подписок на разные события."""
        cls = _make_class_with_subscriptions(
            ("on_finish", "global_finish", ".*"),
            ("on_before", "aspect_before", "CreateOrder.*"),
        )
        meta = MetadataBuilder.build(cls)

        assert len(meta.subscriptions) == 2

    def test_no_subscriptions(self):
        """Класс без подписок — пустой кортеж."""
        cls = type("NoSubs", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta.subscriptions == ()


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — чувствительные поля
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderSensitive:
    """Тесты сборки чувствительных полей (@sensitive)."""

    def test_single_sensitive_field(self):
        """Одно чувствительное поле собирается корректно."""
        cls = _make_class_with_sensitive(
            ("email", {"enabled": True, "max_chars": 3, "char": "*", "max_percent": 50}),
        )
        meta = MetadataBuilder.build(cls)

        assert meta.has_sensitive_fields() is True
        assert len(meta.sensitive_fields) == 1
        assert meta.sensitive_fields[0].property_name == "email"
        assert meta.sensitive_fields[0].config["max_chars"] == 3

    def test_multiple_sensitive_fields(self):
        """Несколько чувствительных полей."""
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
        """Класс без @sensitive — пустой кортеж."""
        cls = type("NoSensitive", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta.sensitive_fields == ()


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: MetadataBuilder — наследование
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataBuilderInheritance:
    """Тесты наследования метаданных через MRO."""

    def test_child_inherits_parent_aspects(self):
        """Дочерний класс наследует аспекты родителя."""
        parent = _make_class_with_aspects(
            ("validate", "regular", "Валидация"),
            ("finish", "summary", "Итог"),
        )
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)

        assert len(meta.aspects) == 2
        assert meta.aspects[0].method_name == "validate"
        assert meta.aspects[1].method_name == "finish"

    def test_child_overrides_parent_aspect(self):
        """Дочерний класс переопределяет аспект родителя."""
        parent = _make_class_with_aspects(
            ("validate", "regular", "Валидация родителя"),
            ("finish", "summary", "Итог"),
        )

        # Переопределяем validate в дочернем
        new_validate = _make_async_method("validate")
        new_validate._new_aspect_meta = {
            "type": "regular",
            "description": "Валидация дочернего",
        }

        child = type("ChildAction", (parent,), {"validate": new_validate})
        meta = MetadataBuilder.build(child)

        # Должен быть аспект из дочернего класса
        validate_aspect = next(a for a in meta.aspects if a.method_name == "validate")
        assert validate_aspect.description == "Валидация дочернего"

    def test_child_inherits_role(self):
        """Дочерний класс наследует роль родителя."""
        parent = _make_class_with_role("admin", "Только админ")
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)

        assert meta.has_role() is True
        assert meta.role.spec == "admin"

    def test_child_inherits_dependencies(self):
        """Дочерний класс наследует зависимости родителя."""
        parent = _make_class_with_dependencies(
            (FakeServiceA, "Сервис A"),
        )
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)

        assert len(meta.dependencies) == 1
        assert meta.dependencies[0].cls is FakeServiceA


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — базовое использование
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorBasic:
    """Тесты базового использования GateCoordinator."""

    def test_get_builds_metadata(self):
        """get() собирает метаданные при первом вызове."""
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user", "Пользователь")
        meta = coordinator.get(cls)

        assert meta.class_ref is cls
        assert meta.role.spec == "user"

    def test_get_caches_result(self):
        """Повторный get() возвращает тот же объект из кеша."""
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user")
        meta1 = coordinator.get(cls)
        meta2 = coordinator.get(cls)

        assert meta1 is meta2  # один и тот же объект

    def test_register_same_as_get(self):
        """register() и get() дают одинаковый результат."""
        coordinator = GateCoordinator()
        cls = _make_class_with_role("admin")
        meta_reg = coordinator.register(cls)
        meta_get = coordinator.get(cls)

        assert meta_reg is meta_get

    def test_has_before_get(self):
        """has() возвращает False до первого get()."""
        coordinator = GateCoordinator()
        cls = type("Fresh", (), {})
        assert coordinator.has(cls) is False

    def test_has_after_get(self):
        """has() возвращает True после get()."""
        coordinator = GateCoordinator()
        cls = type("Registered", (), {})
        coordinator.get(cls)
        assert coordinator.has(cls) is True

    def test_size(self):
        """size отражает количество закешированных классов."""
        coordinator = GateCoordinator()
        assert coordinator.size == 0

        cls1 = type("A", (), {})
        cls2 = type("B", (), {})
        coordinator.get(cls1)
        assert coordinator.size == 1
        coordinator.get(cls2)
        assert coordinator.size == 2

    def test_get_all_metadata(self):
        """get_all_metadata() возвращает все закешированные ClassMetadata."""
        coordinator = GateCoordinator()
        cls1 = type("A", (), {})
        cls2 = type("B", (), {})
        coordinator.get(cls1)
        coordinator.get(cls2)

        all_meta = coordinator.get_all_metadata()
        assert len(all_meta) == 2

    def test_get_all_classes(self):
        """get_all_classes() возвращает все зарегистрированные классы."""
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
    """Тесты инвалидации кеша."""

    def test_invalidate_existing(self):
        """invalidate() удаляет класс из кеша, возвращает True."""
        coordinator = GateCoordinator()
        cls = type("Temp", (), {})
        coordinator.get(cls)
        assert coordinator.has(cls) is True

        result = coordinator.invalidate(cls)
        assert result is True
        assert coordinator.has(cls) is False

    def test_invalidate_non_existing(self):
        """invalidate() для незарегистрированного класса возвращает False."""
        coordinator = GateCoordinator()
        cls = type("Unknown", (), {})
        result = coordinator.invalidate(cls)
        assert result is False

    def test_invalidate_allows_rebuild(self):
        """После invalidate() следующий get() пересобирает метаданные."""
        coordinator = GateCoordinator()
        cls = _make_class_with_role("user")
        meta1 = coordinator.get(cls)
        coordinator.invalidate(cls)
        meta2 = coordinator.get(cls)

        # Новый объект (пересобран)
        assert meta1 is not meta2
        # Но эквивалентен
        assert meta1.role.spec == meta2.role.spec

    def test_invalidate_all(self):
        """invalidate_all() очищает весь кеш."""
        coordinator = GateCoordinator()
        for i in range(5):
            coordinator.get(type(f"Class{i}", (), {}))
        assert coordinator.size == 5

        count = coordinator.invalidate_all()
        assert count == 5
        assert coordinator.size == 0

    def test_invalidate_all_empty(self):
        """invalidate_all() на пустом кеше возвращает 0."""
        coordinator = GateCoordinator()
        assert coordinator.invalidate_all() == 0


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — удобные методы
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorShortcuts:
    """Тесты удобных методов-делегатов."""

    def test_get_dependencies(self):
        """get_dependencies() делегирует к ClassMetadata.dependencies."""
        coordinator = GateCoordinator()
        cls = _make_class_with_dependencies(
            (FakeServiceA, "A"),
            (FakeServiceB, "B"),
        )
        deps = coordinator.get_dependencies(cls)
        assert len(deps) == 2

    def test_get_connections(self):
        """get_connections() делегирует к ClassMetadata.connections."""
        coordinator = GateCoordinator()
        cls = _make_class_with_connections(
            (FakeServiceA, "db", "БД"),
        )
        conns = coordinator.get_connections(cls)
        assert len(conns) == 1

    def test_get_role(self):
        """get_role() делегирует к ClassMetadata.role."""
        coordinator = GateCoordinator()
        cls = _make_class_with_role("admin", "Админ")
        role = coordinator.get_role(cls)
        assert role is not None
        assert role.spec == "admin"

    def test_get_role_none(self):
        """get_role() возвращает None для класса без роли."""
        coordinator = GateCoordinator()
        cls = type("NoRole", (), {})
        role = coordinator.get_role(cls)
        assert role is None

    def test_get_aspects(self):
        """get_aspects() делегирует к ClassMetadata.aspects."""
        coordinator = GateCoordinator()
        cls = _make_class_with_aspects(
            ("step", "regular", "Шаг"),
            ("finish", "summary", "Итог"),
        )
        aspects = coordinator.get_aspects(cls)
        assert len(aspects) == 2

    def test_get_subscriptions(self):
        """get_subscriptions() делегирует к ClassMetadata.subscriptions."""
        coordinator = GateCoordinator()
        cls = _make_class_with_subscriptions(
            ("on_finish", "global_finish", ".*"),
        )
        subs = coordinator.get_subscriptions(cls)
        assert len(subs) == 1


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — ошибки
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorErrors:
    """Тесты обработки ошибок в GateCoordinator."""

    def test_get_not_a_class_raises(self):
        """get() с не-классом вызывает TypeError."""
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="ожидает класс"):
            coordinator.get("not_a_class")

    def test_get_instance_raises(self):
        """get() с экземпляром вызывает TypeError."""
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="ожидает класс"):
            coordinator.get(FakeServiceA())

    def test_get_none_raises(self):
        """get() с None вызывает TypeError."""
        coordinator = GateCoordinator()
        with pytest.raises(TypeError, match="ожидает класс"):
            coordinator.get(None)

    def test_structural_error_propagates(self):
        """Структурная ошибка из MetadataBuilder пробрасывается через get()."""
        coordinator = GateCoordinator()
        cls = _make_class_with_aspects(
            ("step1", "regular", "Шаг"),
            # Нет summary → ошибка
        )
        with pytest.raises(ValueError, match="не имеет summary-аспекта"):
            coordinator.get(cls)

    def test_structural_error_not_cached(self):
        """Класс с ошибкой не попадает в кеш."""
        coordinator = GateCoordinator()
        cls = _make_class_with_aspects(
            ("step1", "regular", "Шаг"),
        )
        with pytest.raises(ValueError):
            coordinator.get(cls)

        # Не закешировался
        assert coordinator.has(cls) is False


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: GateCoordinator — __repr__
# ═════════════════════════════════════════════════════════════════════════════


class TestGateCoordinatorRepr:
    """Тесты строкового представления GateCoordinator."""

    def test_repr_empty(self):
        """__repr__ пустого координатора."""
        coordinator = GateCoordinator()
        r = repr(coordinator)
        assert "empty" in r

    def test_repr_with_classes(self):
        """__repr__ координатора с зарегистрированными классами."""
        coordinator = GateCoordinator()
        cls = type("MyAction", (), {})
        coordinator.get(cls)
        r = repr(coordinator)
        assert "size=1" in r
        assert "MyAction" in r
