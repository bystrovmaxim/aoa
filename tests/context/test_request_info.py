# tests/context/test_request_info.py
"""
Тесты RequestInfo — метаданные входящего запроса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RequestInfo — frozen pydantic-модель (наследник BaseSchema), хранящая
метаданные входящего запроса: trace_id для сквозной трассировки, путь
эндпоинта, HTTP-метод, IP клиента, протокол, User-Agent.

Произвольные поля запрещены (extra="forbid"). Расширение — только через
наследование с явно объявленными полями.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - С полным набором полей — реальный HTTP-запрос.
    - Без аргументов — все поля None.
    - С частичными данными — только trace_id и path.

BaseSchema — dict-подобный доступ:
    - __getitem__, __contains__, get, keys.

BaseSchema — resolve:
    - Плоские поля: resolve("trace_id"), resolve("client_ip").
    - Отсутствующие пути: resolve("missing") → default.

Расширение через наследование:
    - Наследник с полями correlation_id, ab_variant, tags.
    - resolve через наследника.
"""

from datetime import UTC, datetime

from pydantic import ConfigDict

from action_machine.context.request_info import RequestInfo

# ═════════════════════════════════════════════════════════════════════════════
# Наследник RequestInfo для тестов расширения
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedRequestInfo(RequestInfo):
    """Наследник RequestInfo с дополнительными полями для тестов."""
    model_config = ConfigDict(frozen=True)
    correlation_id: str | None = None
    tags: dict[str, str] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoCreation:
    """Создание RequestInfo с разными наборами параметров."""

    def test_create_full_http_request(self) -> None:
        """
        RequestInfo с полным набором стандартных полей — реальный HTTP POST.

        Расширение для протокольно-специфичных полей (correlation_id, tags) —
        через наследника _ExtendedRequestInfo.
        """
        # Arrange & Act — полный набор стандартных HTTP-данных
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

        # Assert — все стандартные поля установлены
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
        _ExtendedRequestInfo с дополнительными полями — correlation_id, tags.
        """
        # Arrange & Act — наследник с дополнительными полями
        request = _ExtendedRequestInfo(
            trace_id="trace-abc-123",
            request_path="/api/v1/orders",
            correlation_id="corr-xyz",
            tags={"ab_test": "variant_b"},
        )

        # Assert — стандартные и дополнительные поля
        assert request.trace_id == "trace-abc-123"
        assert request.correlation_id == "corr-xyz"
        assert request.tags == {"ab_test": "variant_b"}

    def test_create_default(self) -> None:
        """
        RequestInfo без аргументов — все поля None.
        """
        # Arrange & Act — без аргументов
        request = RequestInfo()

        # Assert — все поля по умолчанию
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
        RequestInfo с частичными данными — только trace_id и path.
        """
        # Arrange & Act — минимальные данные MCP-запроса
        request = RequestInfo(
            trace_id="mcp-trace-001",
            request_path="orders.create",
            protocol="mcp",
        )

        # Assert — заданные поля установлены, остальные None
        assert request.trace_id == "mcp-trace-001"
        assert request.request_path == "orders.create"
        assert request.protocol == "mcp"
        assert request.request_method is None
        assert request.client_ip is None


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — dict-подобный доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoDictAccess:
    """Dict-подобный доступ к полям RequestInfo через BaseSchema."""

    def test_getitem(self) -> None:
        """request["trace_id"] → значение поля."""
        # Arrange
        request = RequestInfo(trace_id="trace-001")

        # Act & Assert
        assert request["trace_id"] == "trace-001"

    def test_contains(self) -> None:
        """
        "trace_id" in request → True для объявленных pydantic-полей.
        """
        # Arrange
        request = RequestInfo()

        # Act & Assert — объявленные поля присутствуют
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
        keys() возвращает объявленные pydantic-поля.
        RequestInfo имеет 8 полей: trace_id, request_timestamp,
        request_path, request_method, full_url, client_ip, protocol,
        user_agent.
        """
        # Arrange
        request = RequestInfo(trace_id="t1")

        # Act
        keys = request.keys()

        # Assert — ключевые поля присутствуют
        assert "trace_id" in keys
        assert "request_path" in keys
        assert "client_ip" in keys
        assert "protocol" in keys


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoResolve:
    """Навигация по полям RequestInfo через resolve()."""

    def test_resolve_flat_field(self) -> None:
        """resolve("trace_id") — прямой доступ к плоскому полю."""
        # Arrange
        request = RequestInfo(trace_id="trace-abc-123")

        # Act
        result = request.resolve("trace_id")

        # Assert
        assert result == "trace-abc-123"

    def test_resolve_none_field(self) -> None:
        """resolve("client_ip") когда client_ip=None → None."""
        # Arrange — client_ip не задан, по умолчанию None
        request = RequestInfo()

        # Act
        result = request.resolve("client_ip")

        # Assert — None из поля
        assert result is None

    def test_resolve_extended_nested(self) -> None:
        """
        resolve("correlation_id") на наследнике — навигация к полю наследника.
        """
        # Arrange — наследник с полем correlation_id
        request = _ExtendedRequestInfo(correlation_id="corr-xyz")

        # Act
        result = request.resolve("correlation_id")

        # Assert
        assert result == "corr-xyz"

    def test_resolve_extended_tags(self) -> None:
        """
        resolve("tags") на наследнике → весь словарь тегов.
        """
        # Arrange — наследник с dict-полем tags
        request = _ExtendedRequestInfo(tags={"ab_test": "control", "feature": "new_ui"})

        # Act
        result = request.resolve("tags")

        # Assert — словарь целиком
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
        resolve("request_timestamp") → объект datetime.
        resolve возвращает значение любого типа без преобразования.
        """
        # Arrange
        now = datetime.now(UTC)
        request = RequestInfo(request_timestamp=now)

        # Act
        result = request.resolve("request_timestamp")

        # Assert — тот же объект datetime
        assert result is now
