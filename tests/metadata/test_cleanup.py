# tests/metadata/test_cleanup.py
"""
Тесты модуля очистки временных атрибутов декораторов.

Модуль metadata/cleanup.py предоставляет функцию cleanup_temporary_attributes(),
которая удаляет служебные атрибуты, оставленные декораторами на классах и методах
после того, как MetadataBuilder собрал из них метаданные.

Атрибуты-мишени:
    Уровень класса:
        _role_info        — данные @CheckRoles
        _depends_info     — данные @depends
        _connection_info  — данные @connection

    Уровень метода:
        _new_aspect_meta  — данные @regular_aspect / @summary_aspect
        _checker_meta     — данные чекеров (@ResultStringChecker и др.)
        _on_subscriptions — данные @on

    Уровень свойства:
        _sensitive_config — данные @sensitive

Принципы тестирования:
    - Атрибуты, определённые в собственном __dict__ класса, удаляются.
    - Атрибуты, унаследованные от родителя, НЕ удаляются (чтобы не сломать родителя).
    - Атрибуты методов удаляются только для методов, определённых в самом классе.
    - После очистки класс остаётся функциональным — можно инстанцировать,
      вызывать методы, обращаться к свойствам.
    - Повторный вызов очистки безопасен (идемпотентность).
"""


from action_machine.aspects import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.metadata.cleanup import cleanup_temporary_attributes
from action_machine.plugins.on_gate_host import OnGateHost

# ---------------------------------------------------------------------------
# Вспомогательные функции для создания тестовых классов
# ---------------------------------------------------------------------------

def _make_async_method(name: str = "method"):
    """Создаёт асинхронную функцию-заглушку с заданным именем."""
    async def method(self):
        return f"{name}_result"
    method.__name__ = name
    method.__qualname__ = name
    return method


def _make_class_with_class_attrs(**attrs):
    """
    Создаёт класс с указанными атрибутами уровня класса.

    Все классы наследуют AspectGateHost, чтобы проходить валидацию
    gate-host при необходимости.

    Args:
        **attrs: атрибуты для установки на классе.

    Returns:
        Динамически созданный класс.
    """
    namespace = dict(attrs)
    return type("TestClass", (AspectGateHost,), namespace)


def _make_class_with_method_attrs(method_name: str, **method_attrs):
    """
    Создаёт класс с методом, на котором установлены указанные атрибуты.

    Args:
        method_name: имя метода.
        **method_attrs: атрибуты для установки на методе.

    Returns:
        Динамически созданный класс.
    """
    method = _make_async_method(method_name)
    for key, value in method_attrs.items():
        setattr(method, key, value)
    namespace = {method_name: method}
    return type("TestClass", (AspectGateHost,), namespace)


def _make_class_with_sensitive_property(prop_name: str = "secret"):
    """
    Создаёт класс со свойством, помеченным _sensitive_config.

    Args:
        prop_name: имя свойства.

    Returns:
        Динамически созданный класс.
    """
    def getter(self):
        return "***"

    prop = property(getter)
    prop.fget._sensitive_config = {"mask": "***", "field": prop_name}

    namespace = {prop_name: prop}
    return type("TestClass", (AspectGateHost,), namespace)


# ---------------------------------------------------------------------------
# Тесты очистки атрибутов уровня класса
# ---------------------------------------------------------------------------

class TestClassLevelCleanup:
    """Проверяет удаление временных атрибутов с самого класса."""

    def test_removes_role_info(self):
        """_role_info удаляется из __dict__ класса."""
        cls = _make_class_with_class_attrs(
            _role_info={"role": "admin", "field": "user_role"}
        )
        assert "_role_info" in cls.__dict__
        cleanup_temporary_attributes(cls)
        assert "_role_info" not in cls.__dict__

    def test_removes_depends_info(self):
        """_depends_info удаляется из __dict__ класса."""
        cls = _make_class_with_class_attrs(
            _depends_info=[{"cls": str, "factory": None}]
        )
        assert "_depends_info" in cls.__dict__
        cleanup_temporary_attributes(cls)
        assert "_depends_info" not in cls.__dict__

    def test_removes_connection_info(self):
        """_connection_info удаляется из __dict__ класса."""
        cls = _make_class_with_class_attrs(
            _connection_info=[{"cls": dict, "key": "db"}]
        )
        assert "_connection_info" in cls.__dict__
        cleanup_temporary_attributes(cls)
        assert "_connection_info" not in cls.__dict__

    def test_removes_multiple_attrs_at_once(self):
        """Все три атрибута класса удаляются за один вызов."""
        cls = _make_class_with_class_attrs(
            _role_info={"role": "user"},
            _depends_info=[],
            _connection_info=[]
        )
        cleanup_temporary_attributes(cls)
        assert "_role_info" not in cls.__dict__
        assert "_depends_info" not in cls.__dict__
        assert "_connection_info" not in cls.__dict__

    def test_class_without_attrs_is_safe(self):
        """Класс без временных атрибутов не вызывает ошибок."""
        cls = _make_class_with_class_attrs()
        cleanup_temporary_attributes(cls)  # не должен упасть

    def test_idempotent(self):
        """Повторный вызов очистки безопасен."""
        cls = _make_class_with_class_attrs(
            _role_info={"role": "admin"}
        )
        cleanup_temporary_attributes(cls)
        cleanup_temporary_attributes(cls)  # второй вызов
        assert "_role_info" not in cls.__dict__


# ---------------------------------------------------------------------------
# Тесты очистки атрибутов уровня метода
# ---------------------------------------------------------------------------

class TestMethodLevelCleanup:
    """Проверяет удаление временных атрибутов с методов класса."""

    def test_removes_aspect_meta(self):
        """_new_aspect_meta удаляется с метода."""
        cls = _make_class_with_method_attrs(
            "validate",
            _new_aspect_meta={"kind": "regular", "order": 1}
        )
        method = cls.__dict__["validate"]
        assert hasattr(method, "_new_aspect_meta")
        cleanup_temporary_attributes(cls)
        assert not hasattr(method, "_new_aspect_meta")

    def test_removes_checker_meta(self):
        """_checker_meta удаляется с метода."""
        cls = _make_class_with_method_attrs(
            "check_amount",
            _checker_meta={"checker_class": "ResultStringChecker"}
        )
        method = cls.__dict__["check_amount"]
        assert hasattr(method, "_checker_meta")
        cleanup_temporary_attributes(cls)
        assert not hasattr(method, "_checker_meta")

    def test_removes_on_subscriptions(self):
        """_on_subscriptions удаляется с метода."""
        cls = _make_class_with_method_attrs(
            "on_start",
            _on_subscriptions=[{"event": "global_start", "pattern": ".*"}]
        )
        method = cls.__dict__["on_start"]
        assert hasattr(method, "_on_subscriptions")
        cleanup_temporary_attributes(cls)
        assert not hasattr(method, "_on_subscriptions")

    def test_removes_all_method_attrs(self):
        """Все атрибуты метода удаляются за один вызов."""
        method = _make_async_method("process")
        method._new_aspect_meta = {"kind": "regular"}
        method._checker_meta = {"checker_class": "FieldChecker"}
        method._on_subscriptions = [{"event": "finish"}]

        cls = type("TestClass", (AspectGateHost, OnGateHost), {"process": method})
        cleanup_temporary_attributes(cls)

        assert not hasattr(method, "_new_aspect_meta")
        assert not hasattr(method, "_checker_meta")
        assert not hasattr(method, "_on_subscriptions")

    def test_regular_methods_untouched(self):
        """Методы без временных атрибутов не модифицируются."""
        method = _make_async_method("regular")
        method.custom_flag = True

        cls = type("TestClass", (AspectGateHost,), {"regular": method})
        cleanup_temporary_attributes(cls)

        assert hasattr(method, "custom_flag")  # пользовательский атрибут сохранён


# ---------------------------------------------------------------------------
# Тесты очистки атрибутов уровня свойства
# ---------------------------------------------------------------------------

class TestPropertyLevelCleanup:
    """Проверяет удаление _sensitive_config со свойств."""

    def test_removes_sensitive_config(self):
        """_sensitive_config удаляется с getter-функции свойства."""
        cls = _make_class_with_sensitive_property("password")
        prop = cls.__dict__["password"]
        assert hasattr(prop.fget, "_sensitive_config")
        cleanup_temporary_attributes(cls)
        assert not hasattr(prop.fget, "_sensitive_config")

    def test_property_still_works_after_cleanup(self):
        """Свойство продолжает работать после очистки."""
        cls = _make_class_with_sensitive_property("token")
        cleanup_temporary_attributes(cls)
        instance = cls()
        assert instance.token == "***"


# ---------------------------------------------------------------------------
# Тесты наследования: родительские атрибуты не удаляются
# ---------------------------------------------------------------------------

class TestInheritanceProtection:
    """
    Проверяет, что очистка дочернего класса не затрагивает
    атрибуты родительского класса.

    Это критически важно: если Parent имеет _role_info,
    а Child наследует Parent, очистка Child не должна удалять
    _role_info из Parent.__dict__.
    """

    def test_parent_class_attrs_preserved(self):
        """Атрибуты родителя не удаляются при очистке потомка."""
        parent = _make_class_with_class_attrs(
            _role_info={"role": "admin"}
        )
        child = type("ChildClass", (parent,), {})

        # У потомка нет _role_info в собственном __dict__
        assert "_role_info" not in child.__dict__
        # Но доступен через наследование
        assert hasattr(child, "_role_info")

        cleanup_temporary_attributes(child)

        # Родительский атрибут не тронут
        assert "_role_info" in parent.__dict__
        assert hasattr(child, "_role_info")  # всё ещё доступен

    def test_parent_method_attrs_preserved(self):
        """Атрибуты методов родителя не удаляются при очистке потомка."""
        parent_method = _make_async_method("validate")
        parent_method._new_aspect_meta = {"kind": "regular", "order": 1}

        parent = type("Parent", (AspectGateHost,), {"validate": parent_method})
        child = type("Child", (parent,), {})

        cleanup_temporary_attributes(child)

        # Метод родителя сохранил свой атрибут
        assert hasattr(parent_method, "_new_aspect_meta")

    def test_child_own_attrs_removed_parent_untouched(self):
        """
        У потомка свои атрибуты удаляются,
        а родительские остаются на месте.
        """
        parent = _make_class_with_class_attrs(
            _role_info={"role": "admin"}
        )
        child = type("ChildClass", (parent,), {
            "_depends_info": [{"cls": int}]
        })

        assert "_depends_info" in child.__dict__
        cleanup_temporary_attributes(child)

        assert "_depends_info" not in child.__dict__  # удалён у потомка
        assert "_role_info" in parent.__dict__  # сохранён у родителя


# ---------------------------------------------------------------------------
# Тесты комплексных сценариев
# ---------------------------------------------------------------------------

class TestComplexScenarios:
    """
    Комплексные сценарии, приближённые к реальному использованию
    в ActionMachine.
    """

    def test_full_action_cleanup(self):
        """
        Имитация полного Action-класса со всеми типами
        временных атрибутов.
        """
        validate = _make_async_method("validate")
        validate._new_aspect_meta = {"kind": "regular", "order": 1}
        validate._checker_meta = {"checker_class": "StringChecker"}

        finish = _make_async_method("finish")
        finish._new_aspect_meta = {"kind": "summary", "order": 100}

        on_start = _make_async_method("on_start")
        on_start._on_subscriptions = [{"event": "global_start"}]

        def secret_getter(self):
            return "***"
        secret_getter._sensitive_config = {"mask": "***"}
        secret_prop = property(secret_getter)

        namespace = {
            "_role_info": {"role": "admin"},
            "_depends_info": [{"cls": str}],
            "_connection_info": [{"cls": dict, "key": "db"}],
            "validate": validate,
            "finish": finish,
            "on_start": on_start,
            "secret": secret_prop,
        }

        cls = type(
            "FullAction",
            (AspectGateHost, CheckerGateHost, OnGateHost),
            namespace
        )

        # Всё на месте до очистки
        assert "_role_info" in cls.__dict__
        assert "_depends_info" in cls.__dict__
        assert "_connection_info" in cls.__dict__
        assert hasattr(validate, "_new_aspect_meta")
        assert hasattr(validate, "_checker_meta")
        assert hasattr(finish, "_new_aspect_meta")
        assert hasattr(on_start, "_on_subscriptions")
        assert hasattr(secret_getter, "_sensitive_config")

        cleanup_temporary_attributes(cls)

        # Всё удалено после очистки
        assert "_role_info" not in cls.__dict__
        assert "_depends_info" not in cls.__dict__
        assert "_connection_info" not in cls.__dict__
        assert not hasattr(validate, "_new_aspect_meta")
        assert not hasattr(validate, "_checker_meta")
        assert not hasattr(finish, "_new_aspect_meta")
        assert not hasattr(on_start, "_on_subscriptions")
        assert not hasattr(secret_getter, "_sensitive_config")

    def test_class_still_instantiable_after_cleanup(self):
        """Класс можно создать и использовать после очистки."""
        method = _make_async_method("run")
        method._new_aspect_meta = {"kind": "regular"}

        cls = type("UsableClass", (AspectGateHost,), {
            "_role_info": {"role": "user"},
            "run": method,
        })

        cleanup_temporary_attributes(cls)

        instance = cls()
        assert instance is not None
        assert hasattr(instance, "run")

    def test_cleanup_with_no_temporary_attrs(self):
        """Класс без каких-либо временных атрибутов проходит очистку."""
        cls = type("CleanClass", (AspectGateHost,), {
            "value": 42,
            "name": "test",
        })

        cleanup_temporary_attributes(cls)  # не должен упасть

        assert cls.value == 42
        assert cls.name == "test"