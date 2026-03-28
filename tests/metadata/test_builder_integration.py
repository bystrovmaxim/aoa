# tests/metadata/test_builder_integration.py
"""
Интеграционные тесты MetadataBuilder.build() — единственной точки входа
для сборки ClassMetadata из временных атрибутов декораторов.

Все тестовые классы создаются через реальные декораторы фреймворка
(@CheckRoles, @depends, @regular_aspect, @summary_aspect, чекеры, @on,
@sensitive), чтобы временные атрибуты имели точно тот формат,
который ожидают коллекторы в metadata/collectors.py.

Где декораторы невозможно использовать (динамические классы через type()),
атрибуты устанавливаются в точном формате, соответствующем реальным
декораторам.

Принцип сбора аспектов, чекеров и подписок: собираются ТОЛЬКО из текущего
класса (vars(cls)), без обхода MRO. Потомок не наследует аспекты родителя.
Зависимости, соединения, роли и чувствительные поля — наследуются через MRO.
"""

import pytest

from action_machine.aspects import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.metadata import MetadataBuilder
from action_machine.plugins.on_gate_host import OnGateHost

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _async_method(name: str):
    """Создаёт async-функцию с сигнатурой аспекта (5 параметров)."""
    async def method(self, params, state, box, connections):
        return {}
    method.__name__ = name
    method.__qualname__ = name
    return method


def _attach_aspect(method, kind: str = "regular"):
    """Устанавливает _new_aspect_meta в формате реальных декораторов."""
    method._new_aspect_meta = {
        "type": kind,
        "description": f"Aspect {method.__name__}",
    }
    return method


def _attach_checker(method, field: str = "amount"):
    """Устанавливает _checker_meta в формате реальных чекеров."""
    if not hasattr(method, "_checker_meta"):
        method._checker_meta = []
    method._checker_meta.append({
        "checker_class": type("FakeChecker", (), {}),
        "field_name": field,
        "description": f"Check {field}",
        "required": True,
    })
    return method


def _attach_subscription(method, event: str = "global_start"):
    """Устанавливает _on_subscriptions в формате реального @on."""
    from action_machine.plugins.decorators import SubscriptionInfo
    if not hasattr(method, "_on_subscriptions"):
        method._on_subscriptions = []
    method._on_subscriptions.append(
        SubscriptionInfo(event_type=event, action_filter=".*")
    )
    return method


def _attach_sensitive(prop_getter, field: str, mask: str = "***"):
    """Устанавливает _sensitive_config в формате реального @sensitive."""
    prop_getter._sensitive_config = {
        "enabled": True,
        "max_chars": 3,
        "char": mask[0] if mask else "*",
        "max_percent": 50,
    }
    return prop_getter


def _make_depends_info(cls: type, desc: str = ""):
    """Создаёт DependencyInfo в формате реального @depends."""
    from action_machine.dependencies.depends import DependencyInfo
    return DependencyInfo(cls=cls, description=desc)


def _make_connection_info(cls: type, key: str, desc: str = ""):
    """Создаёт ConnectionInfo в формате реального @connection."""
    from action_machine.resource_managers.connection import ConnectionInfo
    return ConnectionInfo(cls=cls, key=key, description=desc)


def _make_role_info(spec, desc: str = ""):
    """Создаёт _role_info в формате реального @CheckRoles."""
    return {"spec": spec, "desc": desc}


# ---------------------------------------------------------------------------
# Тесты: пустой класс
# ---------------------------------------------------------------------------

class TestBuildEmptyClass:

    def test_empty_class_returns_metadata(self):
        cls = type("EmptyAction", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta is not None
        assert meta.class_ref is cls

    def test_empty_class_has_no_role(self):
        cls = type("EmptyAction", (), {})
        meta = MetadataBuilder.build(cls)
        assert meta.role is None

    def test_empty_class_has_empty_collections(self):
        cls = type("EmptyAction", (), {})
        meta = MetadataBuilder.build(cls)
        assert len(meta.dependencies) == 0
        assert len(meta.connections) == 0
        assert len(meta.aspects) == 0
        assert len(meta.checkers) == 0
        assert len(meta.subscriptions) == 0
        assert len(meta.sensitive_fields) == 0


# ---------------------------------------------------------------------------
# Тесты: роль
# ---------------------------------------------------------------------------

class TestBuildWithRole:

    def test_role_collected(self):
        cls = type("AdminAction", (), {
            "_role_info": _make_role_info("admin"),
        })
        meta = MetadataBuilder.build(cls)
        assert meta.role is not None
        assert meta.role.spec == "admin"

    def test_role_without_other_metadata(self):
        cls = type("RoleOnly", (), {
            "_role_info": _make_role_info("manager"),
        })
        meta = MetadataBuilder.build(cls)
        assert len(meta.aspects) == 0
        assert len(meta.dependencies) == 0


# ---------------------------------------------------------------------------
# Тесты: зависимости
# ---------------------------------------------------------------------------

class TestBuildWithDependencies:

    def test_dependencies_collected(self):
        class FakeA:
            pass
        class FakeB:
            pass
        cls = type("ActionWithDeps", (), {
            "_depends_info": [
                _make_depends_info(FakeA, "A"),
                _make_depends_info(FakeB, "B"),
            ],
        })
        meta = MetadataBuilder.build(cls)
        assert len(meta.dependencies) == 2

    def test_dependency_classes_preserved(self):
        class FakeService:
            pass
        cls = type("ActionWithService", (), {
            "_depends_info": [_make_depends_info(FakeService, "svc")],
        })
        meta = MetadataBuilder.build(cls)
        dep_classes = [d.cls for d in meta.dependencies]
        assert FakeService in dep_classes


# ---------------------------------------------------------------------------
# Тесты: соединения
# ---------------------------------------------------------------------------

class TestBuildWithConnections:

    def test_connections_collected(self):
        class FakeManager:
            pass
        cls = type("ActionWithConns", (), {
            "_connection_info": [_make_connection_info(FakeManager, "db")],
        })
        meta = MetadataBuilder.build(cls)
        assert len(meta.connections) == 1

    def test_connection_key_preserved(self):
        class RedisManager:
            pass
        cls = type("ActionWithRedis", (), {
            "_connection_info": [_make_connection_info(RedisManager, "cache")],
        })
        meta = MetadataBuilder.build(cls)
        conn_keys = [c.key for c in meta.connections]
        assert "cache" in conn_keys


# ---------------------------------------------------------------------------
# Тесты: аспекты
# ---------------------------------------------------------------------------

class TestBuildWithAspects:

    def test_aspects_collected(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        finish = _attach_aspect(_async_method("finish"), "summary")
        cls = type("ActionWithAspects", (AspectGateHost,), {
            "validate": validate,
            "finish": finish,
        })
        meta = MetadataBuilder.build(cls)
        assert len(meta.aspects) == 2

    def test_aspects_ordered(self):
        """Порядок аспектов определяется порядком в vars(cls)."""
        step_b = _attach_aspect(_async_method("step_b"), "regular")
        step_a = _attach_aspect(_async_method("step_a"), "regular")
        done = _attach_aspect(_async_method("done"), "summary")
        cls = type("OrderedAction", (AspectGateHost,), {
            "step_b": step_b,
            "step_a": step_a,
            "done": done,
        })
        meta = MetadataBuilder.build(cls)
        names = [a.method_name for a in meta.aspects]
        # summary должен быть последним
        assert names[-1] == "done"

    def test_aspects_require_gate_host(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        finish = _attach_aspect(_async_method("finish"), "summary")
        cls = type("BadAction", (), {
            "validate": validate,
            "finish": finish,
        })
        with pytest.raises(TypeError, match="AspectGateHost"):
            MetadataBuilder.build(cls)


# ---------------------------------------------------------------------------
# Тесты: чекеры
# ---------------------------------------------------------------------------

class TestBuildWithCheckers:

    def test_checkers_collected(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        _attach_checker(validate, "amount")
        finish = _attach_aspect(_async_method("finish"), "summary")
        cls = type("ActionWithCheckers", (AspectGateHost, CheckerGateHost), {
            "validate": validate,
            "finish": finish,
        })
        meta = MetadataBuilder.build(cls)
        assert len(meta.checkers) >= 1

    def test_checkers_require_gate_host(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        _attach_checker(validate, "name")
        finish = _attach_aspect(_async_method("finish"), "summary")
        cls = type("NoCheckerHost", (AspectGateHost,), {
            "validate": validate,
            "finish": finish,
        })
        with pytest.raises(TypeError, match="CheckerGateHost"):
            MetadataBuilder.build(cls)


# ---------------------------------------------------------------------------
# Тесты: подписки
# ---------------------------------------------------------------------------

class TestBuildWithSubscriptions:

    def test_subscriptions_collected(self):
        async def on_handler(self, state, event):
            pass
        on_handler.__name__ = "on_start"
        on_handler.__qualname__ = "on_start"
        _attach_subscription(on_handler, "global_start")
        cls = type("PluginWithSubs", (OnGateHost,), {"on_start": on_handler})
        meta = MetadataBuilder.build(cls)
        assert len(meta.subscriptions) >= 1

    def test_subscriptions_require_gate_host(self):
        async def on_handler(self, state, event):
            pass
        on_handler.__name__ = "on_finish"
        on_handler.__qualname__ = "on_finish"
        _attach_subscription(on_handler, "global_finish")
        cls = type("BadPlugin", (), {"on_finish": on_handler})
        with pytest.raises(TypeError, match="OnGateHost"):
            MetadataBuilder.build(cls)


# ---------------------------------------------------------------------------
# Тесты: чувствительные поля
# ---------------------------------------------------------------------------

class TestBuildWithSensitiveFields:

    def test_sensitive_fields_collected(self):
        def password_getter(self):
            return "secret"
        _attach_sensitive(password_getter, "password")
        cls = type("SecureAction", (), {"password": property(password_getter)})
        meta = MetadataBuilder.build(cls)
        assert len(meta.sensitive_fields) >= 1

    def test_sensitive_no_gate_required(self):
        def token_getter(self):
            return "tok"
        _attach_sensitive(token_getter, "token")
        cls = type("DataModel", (), {"token": property(token_getter)})
        meta = MetadataBuilder.build(cls)
        assert len(meta.sensitive_fields) >= 1


# ---------------------------------------------------------------------------
# Тесты: полный Action
# ---------------------------------------------------------------------------

class TestBuildFullAction:

    def test_full_action_all_fields_populated(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        load_data = _attach_aspect(_async_method("load_data"), "regular")
        finish = _attach_aspect(_async_method("finish"), "summary")
        _attach_checker(validate, "total")

        async def on_done(self, state, event):
            pass
        on_done.__name__ = "on_done"
        on_done.__qualname__ = "on_done"
        _attach_subscription(on_done, "action_finish")

        def card_getter(self):
            return "4111****"
        _attach_sensitive(card_getter, "card_number")

        class FakePaymentService:
            pass
        class FakeDbManager:
            pass

        namespace = {
            "_role_info": _make_role_info("operator"),
            "_depends_info": [_make_depends_info(FakePaymentService, "pay")],
            "_connection_info": [_make_connection_info(FakeDbManager, "db")],
            "validate": validate,
            "load_data": load_data,
            "finish": finish,
            "on_done": on_done,
            "card_number": property(card_getter),
        }

        cls = type(
            "CreateOrderAction",
            (AspectGateHost, CheckerGateHost, OnGateHost),
            namespace
        )

        meta = MetadataBuilder.build(cls)

        assert meta.class_ref is cls
        assert meta.role is not None
        assert len(meta.dependencies) == 1
        assert len(meta.connections) == 1
        assert len(meta.aspects) == 3
        assert len(meta.checkers) >= 1
        assert len(meta.subscriptions) >= 1
        assert len(meta.sensitive_fields) >= 1


# ---------------------------------------------------------------------------
# Тесты: наследование
# ---------------------------------------------------------------------------

class TestBuildWithInheritance:

    def test_child_inherits_parent_role(self):
        """Роли наследуются через MRO (getattr)."""
        parent = type("ParentAction", (), {
            "_role_info": _make_role_info("admin"),
        })
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert meta.role is not None

    def test_child_does_not_inherit_parent_aspects(self):
        """
        Аспекты НЕ наследуются. Потомок без собственных аспектов
        имеет пустой конвейер, даже если родитель объявлял аспекты.
        Это принципиальное решение: потомок обязан явно объявить
        все свои аспекты.
        """
        validate = _attach_aspect(_async_method("validate"), "regular")
        finish = _attach_aspect(_async_method("finish"), "summary")
        parent = type("ParentAction", (AspectGateHost,), {
            "validate": validate,
            "finish": finish,
        })
        child = type("ChildAction", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert len(meta.aspects) == 0

    def test_child_with_own_aspects_ignores_parent(self):
        """
        Потомок с собственными аспектами использует только свои.
        Аспекты родителя полностью игнорируются.
        """
        parent_validate = _attach_aspect(_async_method("validate"), "regular")
        parent_finish = _attach_aspect(_async_method("finish"), "summary")
        parent = type("ParentAction", (AspectGateHost,), {
            "validate": parent_validate,
            "finish": parent_finish,
        })

        child_process = _attach_aspect(_async_method("process"), "regular")
        child_summary = _attach_aspect(_async_method("summary"), "summary")
        child = type("ChildAction", (parent,), {
            "process": child_process,
            "summary": child_summary,
        })
        meta = MetadataBuilder.build(child)
        assert len(meta.aspects) == 2
        names = [a.method_name for a in meta.aspects]
        assert "process" in names
        assert "summary" in names
        # Родительские аспекты отсутствуют
        assert "validate" not in names
        assert "finish" not in names

    def test_child_adds_own_dependencies(self):
        """Зависимости наследуются через MRO (getattr)."""
        class ServiceA:
            pass
        class ServiceB:
            pass
        parent = type("ParentAction", (), {
            "_depends_info": [_make_depends_info(ServiceA)],
        })
        child = type("ChildAction", (parent,), {
            "_depends_info": [
                _make_depends_info(ServiceA),
                _make_depends_info(ServiceB),
            ],
        })
        meta = MetadataBuilder.build(child)
        dep_classes = [d.cls for d in meta.dependencies]
        assert ServiceB in dep_classes

    def test_child_inherits_sensitive_fields(self):
        """
        Чувствительные поля наследуются через MRO.
        Это исключение из правила "только свои" — @sensitive
        описывает свойство модели данных, а не конвейер выполнения.
        """
        def email_getter(self):
            return "secret@example.com"
        _attach_sensitive(email_getter, "email")
        parent = type("ParentModel", (), {"email": property(email_getter)})
        child = type("ChildModel", (parent,), {})
        meta = MetadataBuilder.build(child)
        assert len(meta.sensitive_fields) == 1
        assert meta.sensitive_fields[0].property_name == "email"


# ---------------------------------------------------------------------------
# Тесты: ошибки валидации
# ---------------------------------------------------------------------------

class TestBuildValidationErrors:

    def test_not_a_class_raises_error(self):
        with pytest.raises((TypeError, ValueError)):
            MetadataBuilder.build("not_a_class")

    def test_regular_aspect_without_summary_raises_error(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        cls = type("IncompleteAction", (AspectGateHost,), {"validate": validate})
        with pytest.raises((ValueError, TypeError)):
            MetadataBuilder.build(cls)

    def test_summary_must_be_last(self):
        """Summary-аспект должен быть последним в порядке vars(cls)."""
        finish = _attach_aspect(_async_method("aaa_finish"), "summary")
        validate = _attach_aspect(_async_method("zzz_validate"), "regular")
        cls = type("BadOrderAction", (AspectGateHost,), {
            "aaa_finish": finish,
            "zzz_validate": validate,
        })
        with pytest.raises((ValueError, TypeError)):
            MetadataBuilder.build(cls)

    def test_aspects_without_aspect_gate_host(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        finish = _attach_aspect(_async_method("finish"), "summary")
        cls = type("NoHostAction", (), {"validate": validate, "finish": finish})
        with pytest.raises(TypeError, match="AspectGateHost"):
            MetadataBuilder.build(cls)

    def test_checkers_without_checker_gate_host(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        _attach_checker(validate, "field")
        finish = _attach_aspect(_async_method("finish"), "summary")
        cls = type("NoCheckerHost", (AspectGateHost,), {
            "validate": validate, "finish": finish,
        })
        with pytest.raises(TypeError, match="CheckerGateHost"):
            MetadataBuilder.build(cls)

    def test_subscriptions_without_on_gate_host(self):
        async def handler(self, state, event):
            pass
        handler.__name__ = "on_event"
        handler.__qualname__ = "on_event"
        _attach_subscription(handler, "global_start")
        cls = type("NoOnHost", (), {"on_event": handler})
        with pytest.raises(TypeError, match="OnGateHost"):
            MetadataBuilder.build(cls)


# ---------------------------------------------------------------------------
# Тесты: идемпотентность
# ---------------------------------------------------------------------------

class TestBuildIdempotency:

    def test_repeated_build_same_result(self):
        validate = _attach_aspect(_async_method("validate"), "regular")
        finish = _attach_aspect(_async_method("finish"), "summary")
        cls = type("IdempotentAction", (AspectGateHost,), {
            "validate": validate,
            "finish": finish,
        })
        meta1 = MetadataBuilder.build(cls)
        meta2 = MetadataBuilder.build(cls)
        assert meta1.class_ref is meta2.class_ref
        assert len(meta1.aspects) == len(meta2.aspects)