# tests/intents/context_requires/test_request_info.py
"""
Tests for RequestInfo — incoming request metadata.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

RequestInfo is a frozen pydantic model (subclass of BaseSchema) holding
incoming request metadata: trace_id for distributed tracing, endpoint path,
HTTP method, client IP, protocol, User-Agent.

Arbitrary fields are forbidden (extra="forbid"). Extend only via subclasses
with explicitly declared fields.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Construction:
    - Full field set — real HTTP request.
    - No arguments — all fields None.
    - Partial data — trace_id and path only.

BaseSchema — dict-like access:
    - __getitem__, __contains__, get, keys.

BaseSchema — resolve:
    - Flat fields: resolve("trace_id"), resolve("client_ip").
    - Missing paths: resolve("missing") → default.

Extension via inheritance:
    - Subclass with correlation_id, ab_variant, tags.
    - resolve on subclass.
"""

from datetime import UTC, datetime

from pydantic import ConfigDict

from aoa.action_machine.context.request_info import RequestInfo

# ═════════════════════════════════════════════════════════════════════════════
# RequestInfo subclass for extension tests
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedRequestInfo(RequestInfo):
    """RequestInfo subclass with extra fields for tests."""
    model_config = ConfigDict(frozen=True)
    correlation_id: str | None = None
    tags: dict[str, str] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Construction and initialization
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoCreation:
    """Creating RequestInfo with different argument sets."""

    def test_create_full_http_request(self) -> None:
        """
        RequestInfo with all standard fields — real HTTP POST.

        Protocol-specific fields (correlation_id, tags) via _ExtendedRequestInfo.
        """
        # Arrange & Act — full standard HTTP data
        now = datetime.now(UTC)
        request = RequestInfo(
            trace_id="trace-abc-123",
            request_timestamp=now,
            request_path="/api/v1/orders",
            request_method="POST",
            full_url="https://api.example.com/api/v1/orders",
            client_ip="192.168.1.100",
            protocol="https",
            user_agent="Mozilla/5.0",
        )

        # Assert — all standard fields set
        assert request.trace_id == "trace-abc-123"
        assert request.request_timestamp is now
        assert request.request_path == "/api/v1/orders"
        assert request.request_method == "POST"
        assert request.full_url == "https://api.example.com/api/v1/orders"
        assert request.client_ip == "192.168.1.100"
        assert request.protocol == "https"
        assert request.user_agent == "Mozilla/5.0"

    def test_create_extended_http_request(self) -> None:
        """
        _ExtendedRequestInfo with extra fields — correlation_id, tags.
        """
        # Arrange & Act — subclass with extra fields
        request = _ExtendedRequestInfo(
            trace_id="trace-abc-123",
            request_path="/api/v1/orders",
            correlation_id="corr-xyz",
            tags={"ab_test": "variant_b"},
        )

        # Assert — standard and extra fields
        assert request.trace_id == "trace-abc-123"
        assert request.correlation_id == "corr-xyz"
        assert request.tags == {"ab_test": "variant_b"}

    def test_create_default(self) -> None:
        """
        RequestInfo with no arguments — all fields None.
        """
        # Arrange & Act — no arguments
        request = RequestInfo()

        # Assert — default fields
        assert request.trace_id is None
        assert request.request_timestamp is None
        assert request.request_path is None
        assert request.request_method is None
        assert request.full_url is None
        assert request.client_ip is None
        assert request.protocol is None
        assert request.user_agent is None

    def test_create_partial(self) -> None:
        """
        RequestInfo with partial data — trace_id and path only.
        """
        # Arrange & Act — minimal MCP-style request data
        request = RequestInfo(
            trace_id="mcp-trace-001",
            request_path="orders.create",
            protocol="mcp",
        )

        # Assert — set fields present, rest None
        assert request.trace_id == "mcp-trace-001"
        assert request.request_path == "orders.create"
        assert request.protocol == "mcp"
        assert request.request_method is None
        assert request.client_ip is None


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — dict-like access
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoDictAccess:
    """Dict-like access to RequestInfo fields via BaseSchema."""

    def test_getitem(self) -> None:
        """request["trace_id"] → field value."""
        # Arrange
        request = RequestInfo(trace_id="trace-001")

        # Act & Assert
        assert request["trace_id"] == "trace-001"

    def test_contains(self) -> None:
        """
        "trace_id" in request → True for declared pydantic fields.
        """
        # Arrange
        request = RequestInfo()

        # Act & Assert — declared fields present
        assert "trace_id" in request
        assert "request_path" in request
        assert "nonexistent" not in request

    def test_get_with_default(self) -> None:
        """request.get("nonexistent", "default") → "default"."""
        # Arrange
        request = RequestInfo(trace_id="t1")

        # Act & Assert
        assert request.get("trace_id") == "t1"
        assert request.get("nonexistent", "fallback") == "fallback"

    def test_keys_contains_all_fields(self) -> None:
        """
        keys() returns declared pydantic fields.
        RequestInfo has 8 fields: trace_id, request_timestamp,
        request_path, request_method, full_url, client_ip, protocol,
        user_agent.
        """
        # Arrange
        request = RequestInfo(trace_id="t1")

        # Act
        keys = request.keys()

        # Assert — key fields present
        assert "trace_id" in keys
        assert "request_path" in keys
        assert "client_ip" in keys
        assert "protocol" in keys


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoResolve:
    """Field navigation on RequestInfo via resolve()."""

    def test_resolve_flat_field(self) -> None:
        """resolve("trace_id") — direct access to flat field."""
        # Arrange
        request = RequestInfo(trace_id="trace-abc-123")

        # Act
        result = request.resolve("trace_id")

        # Assert
        assert result == "trace-abc-123"

    def test_resolve_none_field(self) -> None:
        """resolve("client_ip") when client_ip=None → None."""
        # Arrange — client_ip defaults to None
        request = RequestInfo()

        # Act
        result = request.resolve("client_ip")

        # Assert — None from field
        assert result is None

    def test_resolve_extended_nested(self) -> None:
        """
        resolve("correlation_id") on subclass — navigate to subclass field.
        """
        # Arrange — subclass with correlation_id
        request = _ExtendedRequestInfo(correlation_id="corr-xyz")

        # Act
        result = request.resolve("correlation_id")

        # Assert
        assert result == "corr-xyz"

    def test_resolve_extended_tags(self) -> None:
        """
        resolve("tags") on subclass → full tags dict.
        """
        # Arrange — subclass with tags dict
        request = _ExtendedRequestInfo(tags={"ab_test": "control", "feature": "new_ui"})

        # Act
        result = request.resolve("tags")

        # Assert — full dict
        assert result == {"ab_test": "control", "feature": "new_ui"}

    def test_resolve_missing_returns_default(self) -> None:
        """resolve("nonexistent", default="N/A") → "N/A"."""
        # Arrange
        request = RequestInfo()

        # Act
        result = request.resolve("nonexistent", default="N/A")

        # Assert
        assert result == "N/A"

    def test_resolve_timestamp(self) -> None:
        """
        resolve("request_timestamp") → datetime object.
        resolve returns the value as-is without conversion.
        """
        # Arrange
        now = datetime.now(UTC)
        request = RequestInfo(request_timestamp=now)

        # Act
        result = request.resolve("request_timestamp")

        # Assert — same datetime object
        assert result is now
