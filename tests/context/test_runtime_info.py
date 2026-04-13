# tests/context/test_runtime_info.py
"""
Тесты RuntimeInfo — информация об окружении выполнения.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RuntimeInfo — frozen pydantic-модель (наследник BaseSchema), хранящая
информацию об окружении: имя хоста, название и версия сервиса,
идентификатор контейнера, имя пода Kubernetes.

RuntimeInfo заполняется один раз при старте приложения и копируется
в каждый Context. Произвольные поля запрещены (extra="forbid").
Расширение — только через наследование с явно объявленными полями.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - С полным набором полей — production-сервер.
    - Без аргументов — все поля None.
    - С частичными данными — только hostname.

BaseSchema — dict-подобный доступ:
    - __getitem__, __contains__, get, keys.

BaseSchema — resolve:
    - Плоские поля: resolve("hostname"), resolve("service_version").
    - Отсутствующие пути: resolve("missing") → default.

Расширение через наследование:
    - Наследник с полями region, cluster.
    - resolve через наследника.
"""


from pydantic import ConfigDict

from action_machine.intents.context.runtime_info import RuntimeInfo

# ═════════════════════════════════════════════════════════════════════════════
# Наследник RuntimeInfo для тестов расширения
# ═════════════════════════════════════════════════════════════════════════════


class _CloudRuntimeInfo(RuntimeInfo):
    """Наследник RuntimeInfo с полями для cloud-окружения."""
    model_config = ConfigDict(frozen=True)
    region: str | None = None
    cluster: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoCreation:
    """Создание RuntimeInfo с разными наборами параметров."""

    def test_create_full_production(self) -> None:
        """
        RuntimeInfo с полным набором полей — production Kubernetes pod.

        Расширение для cloud-специфичных полей (region, cluster) —
        через наследника _CloudRuntimeInfo.
        """
        # Arrange & Act — наследник с cloud-полями
        runtime = _CloudRuntimeInfo(
            hostname="pod-orders-7b4f9c-xyz",
            service_name="order-service",
            service_version="2.3.1",
            container_id="abc123def456",
            pod_name="orders-deployment-7b4f9c-xyz",
            region="eu-west-1",
            cluster="prod-main",
        )

        # Assert — все поля установлены
        assert runtime.hostname == "pod-orders-7b4f9c-xyz"
        assert runtime.service_name == "order-service"
        assert runtime.service_version == "2.3.1"
        assert runtime.container_id == "abc123def456"
        assert runtime.pod_name == "orders-deployment-7b4f9c-xyz"
        assert runtime.region == "eu-west-1"
        assert runtime.cluster == "prod-main"

    def test_create_default(self) -> None:
        """
        RuntimeInfo без аргументов — все поля None.
        """
        # Arrange & Act — без аргументов
        runtime = RuntimeInfo()

        # Assert — все поля по умолчанию
        assert runtime.hostname is None
        assert runtime.service_name is None
        assert runtime.service_version is None
        assert runtime.container_id is None
        assert runtime.pod_name is None

    def test_create_partial(self) -> None:
        """
        RuntimeInfo с минимальными данными — только hostname.
        """
        # Arrange & Act — только hostname
        runtime = RuntimeInfo(hostname="dev-laptop")

        # Assert — hostname установлен, остальное None
        assert runtime.hostname == "dev-laptop"
        assert runtime.service_name is None
        assert runtime.service_version is None


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — dict-подобный доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoDictAccess:
    """Dict-подобный доступ к полям RuntimeInfo через BaseSchema."""

    def test_getitem(self) -> None:
        """runtime["hostname"] → значение поля."""
        # Arrange
        runtime = RuntimeInfo(hostname="prod-01")

        # Act & Assert
        assert runtime["hostname"] == "prod-01"

    def test_contains(self) -> None:
        """
        "hostname" in runtime → True для объявленных pydantic-полей.
        """
        # Arrange
        runtime = RuntimeInfo()

        # Act & Assert — объявленные поля присутствуют
        assert "hostname" in runtime
        assert "service_name" in runtime
        assert "nonexistent" not in runtime

    def test_get_with_default(self) -> None:
        """runtime.get("nonexistent", "default") → "default"."""
        # Arrange
        runtime = RuntimeInfo(hostname="host-1")

        # Act & Assert
        assert runtime.get("hostname") == "host-1"
        assert runtime.get("nonexistent", "fallback") == "fallback"

    def test_keys(self) -> None:
        """
        keys() возвращает объявленные pydantic-поля.
        RuntimeInfo имеет 5 полей: hostname, service_name,
        service_version, container_id, pod_name.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="h1")

        # Act
        keys = runtime.keys()

        # Assert — все объявленные поля присутствуют
        assert "hostname" in keys
        assert "service_name" in keys
        assert "service_version" in keys
        assert "container_id" in keys
        assert "pod_name" in keys


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoResolve:
    """Навигация по полям RuntimeInfo через resolve()."""

    def test_resolve_flat_field(self) -> None:
        """resolve("hostname") — прямой доступ к плоскому полю."""
        # Arrange
        runtime = RuntimeInfo(hostname="pod-xyz-42")

        # Act
        result = runtime.resolve("hostname")

        # Assert
        assert result == "pod-xyz-42"

    def test_resolve_service_version(self) -> None:
        """resolve("service_version") — доступ к версии сервиса."""
        # Arrange
        runtime = RuntimeInfo(service_version="1.2.3")

        # Act
        result = runtime.resolve("service_version")

        # Assert
        assert result == "1.2.3"

    def test_resolve_none_field(self) -> None:
        """
        resolve("container_id") когда container_id=None → None.
        None — валидное значение поля.
        """
        # Arrange — container_id не задан
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("container_id")

        # Assert — None из поля
        assert result is None

    def test_resolve_extended_field(self) -> None:
        """
        resolve("region") на наследнике — навигация к полю наследника.
        """
        # Arrange — наследник с полем region
        runtime = _CloudRuntimeInfo(region="eu-west-1")

        # Act
        result = runtime.resolve("region")

        # Assert
        assert result == "eu-west-1"

    def test_resolve_missing_returns_default(self) -> None:
        """resolve("nonexistent", default="unknown") → "unknown"."""
        # Arrange
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("nonexistent", default="unknown")

        # Assert
        assert result == "unknown"

    def test_resolve_missing_nested_returns_default(self) -> None:
        """
        resolve("nonexistent.deep", default="none") → "none".
        Первый сегмент не найден — цепочка прерывается.
        """
        # Arrange
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("nonexistent.deep", default="none")

        # Assert
        assert result == "none"
