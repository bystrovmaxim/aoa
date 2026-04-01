# tests2/context/test_runtime_info.py
"""
Тесты RuntimeInfo — информация об окружении выполнения.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RuntimeInfo — dataclass с ReadableMixin, хранящий информацию об окружении,
в котором выполняется код: имя хоста, название и версия сервиса,
идентификатор контейнера, имя пода Kubernetes.

RuntimeInfo заполняется один раз при старте приложения и затем копируется
в каждый Context. Это позволяет идентифицировать, на каком сервере
и в какой версии выполняется действие — особенно полезно при горизонтальном
масштабировании и анализе логов.

Используется в шаблонах логирования через {%context.runtime.hostname},
{%context.runtime.service_name} и т.д.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - С полным набором полей — production-сервер.
    - Без аргументов — все поля None/пустые.
    - С частичными данными — только hostname.
    - С Kubernetes-полями (pod_name, container_id).

ReadableMixin — dict-подобный доступ:
    - __getitem__, __contains__, get, keys.

ReadableMixin — resolve:
    - Плоские поля: resolve("hostname"), resolve("service_version").
    - Вложенные через extra: resolve("extra.region").
    - Отсутствующие пути: resolve("missing") → default.
"""

from action_machine.context.runtime_info import RuntimeInfo

# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoCreation:
    """Создание RuntimeInfo с разными наборами параметров."""

    def test_create_full_production(self) -> None:
        """
        RuntimeInfo с полным набором полей — production Kubernetes pod.

        Типичная инициализация при старте сервиса в Kubernetes:
        hostname из os.uname(), service_name и version из конфигурации,
        pod_name и container_id из переменных окружения.
        """
        # Arrange & Act — полный набор данных production-окружения
        runtime = RuntimeInfo(
            hostname="pod-orders-7b4f9c-xyz",
            service_name="order-service",
            service_version="2.3.1",
            container_id="abc123def456",
            pod_name="orders-deployment-7b4f9c-xyz",
            extra={"region": "eu-west-1", "cluster": "prod-main"},
        )

        # Assert — все поля установлены
        assert runtime.hostname == "pod-orders-7b4f9c-xyz"
        assert runtime.service_name == "order-service"
        assert runtime.service_version == "2.3.1"
        assert runtime.container_id == "abc123def456"
        assert runtime.pod_name == "orders-deployment-7b4f9c-xyz"
        assert runtime.extra == {"region": "eu-west-1", "cluster": "prod-main"}

    def test_create_default(self) -> None:
        """
        RuntimeInfo без аргументов — все поля None, extra пустой.

        NoAuthCoordinator и тестовые стабы создают RuntimeInfo()
        с дефолтными значениями.
        """
        # Arrange & Act — без аргументов
        runtime = RuntimeInfo()

        # Assert — все поля по умолчанию
        assert runtime.hostname is None
        assert runtime.service_name is None
        assert runtime.service_version is None
        assert runtime.container_id is None
        assert runtime.pod_name is None
        assert runtime.extra == {}

    def test_create_partial(self) -> None:
        """
        RuntimeInfo с минимальными данными — только hostname.

        Типичная ситуация при локальной разработке: hostname известен,
        остальное не настроено.
        """
        # Arrange & Act — только hostname
        runtime = RuntimeInfo(hostname="dev-laptop")

        # Assert — hostname установлен, остальное None
        assert runtime.hostname == "dev-laptop"
        assert runtime.service_name is None
        assert runtime.service_version is None

    def test_extra_is_independent_dict(self) -> None:
        """
        Каждый экземпляр RuntimeInfo имеет свой словарь extra.

        Dataclass field(default_factory=dict) гарантирует независимость
        экземпляров.
        """
        # Arrange — два экземпляра без явного extra
        r1 = RuntimeInfo()
        r2 = RuntimeInfo()

        # Act — модификация extra одного экземпляра
        r1.extra["zone"] = "us-east-1a"

        # Assert — второй экземпляр не затронут
        assert r1.extra == {"zone": "us-east-1a"}
        assert r2.extra == {}


# ═════════════════════════════════════════════════════════════════════════════
# ReadableMixin — dict-подобный доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoDictAccess:
    """Dict-подобный доступ к полям RuntimeInfo через ReadableMixin."""

    def test_getitem(self) -> None:
        """
        runtime["hostname"] → значение поля.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="prod-01")

        # Act & Assert
        assert runtime["hostname"] == "prod-01"

    def test_contains(self) -> None:
        """
        "hostname" in runtime → True для существующих атрибутов dataclass.

        Все поля dataclass существуют как атрибуты, даже со значением None.
        """
        # Arrange
        runtime = RuntimeInfo()

        # Act & Assert — поля dataclass всегда присутствуют
        assert "hostname" in runtime
        assert "service_name" in runtime
        assert "extra" in runtime
        assert "nonexistent" not in runtime

    def test_get_with_default(self) -> None:
        """
        runtime.get("nonexistent", "default") → "default".
        """
        # Arrange
        runtime = RuntimeInfo(hostname="host-1")

        # Act & Assert
        assert runtime.get("hostname") == "host-1"
        assert runtime.get("nonexistent", "fallback") == "fallback"

    def test_keys(self) -> None:
        """
        keys() возвращает все публичные поля dataclass.

        RuntimeInfo имеет 6 полей: hostname, service_name,
        service_version, container_id, pod_name, extra.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="h1")

        # Act
        keys = runtime.keys()

        # Assert — ключевые поля присутствуют
        assert "hostname" in keys
        assert "service_name" in keys
        assert "service_version" in keys
        assert "container_id" in keys
        assert "pod_name" in keys
        assert "extra" in keys


# ═════════════════════════════════════════════════════════════════════════════
# ReadableMixin — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoResolve:
    """Навигация по полям RuntimeInfo через resolve()."""

    def test_resolve_flat_field(self) -> None:
        """
        resolve("hostname") — прямой доступ к плоскому полю.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="pod-xyz-42")

        # Act
        result = runtime.resolve("hostname")

        # Assert
        assert result == "pod-xyz-42"

    def test_resolve_service_version(self) -> None:
        """
        resolve("service_version") — доступ к версии сервиса.
        """
        # Arrange
        runtime = RuntimeInfo(service_version="1.2.3")

        # Act
        result = runtime.resolve("service_version")

        # Assert
        assert result == "1.2.3"

    def test_resolve_none_field(self) -> None:
        """
        resolve("container_id") когда container_id=None → None.

        None — валидное значение, поле существует в dataclass.
        """
        # Arrange — container_id не задан
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("container_id")

        # Assert — None из атрибута
        assert result is None

    def test_resolve_extra_nested(self) -> None:
        """
        resolve("extra.region") — навигация через extra-словарь.
        """
        # Arrange
        runtime = RuntimeInfo(extra={"region": "eu-west-1"})

        # Act
        result = runtime.resolve("extra.region")

        # Assert
        assert result == "eu-west-1"

    def test_resolve_missing_returns_default(self) -> None:
        """
        resolve("nonexistent", default="unknown") → "unknown".
        """
        # Arrange
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("nonexistent", default="unknown")

        # Assert
        assert result == "unknown"

    def test_resolve_extra_missing_key(self) -> None:
        """
        resolve("extra.missing_key") на пустом extra → default.
        """
        # Arrange — пустой extra
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("extra.missing_key", default="none")

        # Assert
        assert result == "none"
