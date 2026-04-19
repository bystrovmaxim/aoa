# tests/intents/context/test_runtime_info.py
"""
Tests for RuntimeInfo — execution environment metadata.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

RuntimeInfo is a frozen pydantic model (subclass of BaseSchema) holding
environment data: hostname, service name and version, container id, Kubernetes
pod name.

RuntimeInfo is filled once at app startup and copied into each Context.
Arbitrary fields are forbidden (extra="forbid"). Extend only via subclasses
with explicitly declared fields.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Construction:
    - Full field set — production server.
    - No arguments — all fields None.
    - Partial data — hostname only.

BaseSchema — dict-like access:
    - __getitem__, __contains__, get, keys.

BaseSchema — resolve:
    - Flat fields: resolve("hostname"), resolve("service_version").
    - Missing paths: resolve("missing") → default.

Extension via inheritance:
    - Subclass with region, cluster.
    - resolve on subclass.
"""


from pydantic import ConfigDict

from action_machine.context.runtime_info import RuntimeInfo

# ═════════════════════════════════════════════════════════════════════════════
# RuntimeInfo subclass for extension tests
# ═════════════════════════════════════════════════════════════════════════════


class _CloudRuntimeInfo(RuntimeInfo):
    """RuntimeInfo subclass with cloud environment fields."""
    model_config = ConfigDict(frozen=True)
    region: str | None = None
    cluster: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# Construction and initialization
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoCreation:
    """Creating RuntimeInfo with different argument sets."""

    def test_create_full_production(self) -> None:
        """
        RuntimeInfo with all fields — production Kubernetes pod.

        Cloud-specific fields (region, cluster) via _CloudRuntimeInfo subclass.
        """
        # Arrange & Act — subclass with cloud fields
        runtime = _CloudRuntimeInfo(
            hostname="pod-orders-7b4f9c-xyz",
            service_name="order-service",
            service_version="2.3.1",
            container_id="abc123def456",
            pod_name="orders-deployment-7b4f9c-xyz",
            region="eu-west-1",
            cluster="prod-main",
        )

        # Assert — all fields set
        assert runtime.hostname == "pod-orders-7b4f9c-xyz"
        assert runtime.service_name == "order-service"
        assert runtime.service_version == "2.3.1"
        assert runtime.container_id == "abc123def456"
        assert runtime.pod_name == "orders-deployment-7b4f9c-xyz"
        assert runtime.region == "eu-west-1"
        assert runtime.cluster == "prod-main"

    def test_create_default(self) -> None:
        """
        RuntimeInfo with no arguments — all fields None.
        """
        # Arrange & Act — no arguments
        runtime = RuntimeInfo()

        # Assert — default fields
        assert runtime.hostname is None
        assert runtime.service_name is None
        assert runtime.service_version is None
        assert runtime.container_id is None
        assert runtime.pod_name is None

    def test_create_partial(self) -> None:
        """
        RuntimeInfo with minimal data — hostname only.
        """
        # Arrange & Act — hostname only
        runtime = RuntimeInfo(hostname="dev-laptop")

        # Assert — hostname set, rest None
        assert runtime.hostname == "dev-laptop"
        assert runtime.service_name is None
        assert runtime.service_version is None


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — dict-like access
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoDictAccess:
    """Dict-like access to RuntimeInfo fields via BaseSchema."""

    def test_getitem(self) -> None:
        """runtime["hostname"] → field value."""
        # Arrange
        runtime = RuntimeInfo(hostname="prod-01")

        # Act & Assert
        assert runtime["hostname"] == "prod-01"

    def test_contains(self) -> None:
        """
        "hostname" in runtime → True for declared pydantic fields.
        """
        # Arrange
        runtime = RuntimeInfo()

        # Act & Assert — declared fields present
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
        keys() returns declared pydantic fields.
        RuntimeInfo has 5 fields: hostname, service_name,
        service_version, container_id, pod_name.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="h1")

        # Act
        keys = runtime.keys()

        # Assert — all declared fields present
        assert "hostname" in keys
        assert "service_name" in keys
        assert "service_version" in keys
        assert "container_id" in keys
        assert "pod_name" in keys


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoResolve:
    """Field navigation on RuntimeInfo via resolve()."""

    def test_resolve_flat_field(self) -> None:
        """resolve("hostname") — direct access to flat field."""
        # Arrange
        runtime = RuntimeInfo(hostname="pod-xyz-42")

        # Act
        result = runtime.resolve("hostname")

        # Assert
        assert result == "pod-xyz-42"

    def test_resolve_service_version(self) -> None:
        """resolve("service_version") — service version field."""
        # Arrange
        runtime = RuntimeInfo(service_version="1.2.3")

        # Act
        result = runtime.resolve("service_version")

        # Assert
        assert result == "1.2.3"

    def test_resolve_none_field(self) -> None:
        """
        resolve("container_id") when container_id=None → None.
        None is a valid field value.
        """
        # Arrange — container_id unset
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("container_id")

        # Assert — None from field
        assert result is None

    def test_resolve_extended_field(self) -> None:
        """
        resolve("region") on subclass — navigate to subclass field.
        """
        # Arrange — subclass with region
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
        First segment missing — chain stops.
        """
        # Arrange
        runtime = RuntimeInfo()

        # Act
        result = runtime.resolve("nonexistent.deep", default="none")

        # Assert
        assert result == "none"
