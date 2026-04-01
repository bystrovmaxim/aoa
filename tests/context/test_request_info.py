# tests/context/test_request_info.py
"""
Тесты RequestInfo — метаданные входящего запроса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RequestInfo — dataclass с ReadableMixin, хранящий метаданные входящего
запроса: trace_id для сквозной трассировки, путь эндпоинта, HTTP-метод,
IP клиента, протокол, User-Agent и произвольные дополнительные данные.

RequestInfo заполняется:
- ContextAssembler.assemble() — извлекает метаданные из HTTP-запроса
  (FastAPI Request) или MCP tool call.
- Напрямую в тестах — через конструктор RequestInfo(...).
- NoAuthCoordinator — создаёт пустой RequestInfo() с дефолтами.

Используется в шаблонах логирования через {%context.request.trace_id},
{%context.request.request_path} и т.д.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - С полным набором полей — реальный HTTP-запрос.
    - Без аргументов — все поля None/пустые (анонимный контекст).
    - С частичными данными — только trace_id и path.

ReadableMixin — dict-подобный доступ:
    - __getitem__, __contains__, get, keys.

ReadableMixin — resolve:
    - Плоские поля: resolve("trace_id"), resolve("client_ip").
    - Вложенные через extra: resolve("extra.correlation_id").
    - Теги: resolve("tags") → словарь.

Поле extra:
    - Протокольно-специфичные данные (correlation_id, grpc_metadata).
    - Пустой extra по умолчанию.

Поле tags:
    - Произвольные теги для маркировки (A/B-тестирование, feature flags).
    - Пустой tags по умолчанию.
"""

from datetime import UTC, datetime

from action_machine.context.request_info import RequestInfo

# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoCreation:
    """Создание RequestInfo с разными наборами параметров."""

    def test_create_full_http_request(self) -> None:
        """
        RequestInfo с полным набором полей — реальный HTTP POST запрос.

        ContextAssembler извлекает все доступные метаданные из
        FastAPI Request: trace_id из заголовка X-Request-ID, путь,
        метод, IP из X-Forwarded-For, протокол, User-Agent.
        """
        # Arrange & Act — полный набор данных реального HTTP-запроса
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
            extra={"correlation_id": "corr-xyz"},
            tags={"ab_test": "variant_b"},
        )

        # Assert — все поля установлены
        assert request.trace_id == "trace-abc-123"
        assert request.request_timestamp is now
        assert request.request_path == "/api/v1/orders"
        assert request.request_method == "POST"
        assert request.full_url == "https://api.example.com/api/v1/orders"
        assert request.client_ip == "192.168.1.100"
        assert request.protocol == "https"
        assert request.user_agent == "Mozilla/5.0"
        assert request.extra == {"correlation_id": "corr-xyz"}
        assert request.tags == {"ab_test": "variant_b"}

    def test_create_default(self) -> None:
        """
        RequestInfo без аргументов — пустой контекст запроса.

        NoAuthCoordinator создаёт Context с RequestInfo() —
        все поля None, extra и tags — пустые словари.
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
        assert request.extra == {}
        assert request.tags == {}

    def test_create_partial(self) -> None:
        """
        RequestInfo с частичными данными — только trace_id и path.

        Типичная ситуация для MCP-запросов, где нет HTTP-метода,
        IP и User-Agent, но есть trace_id и имя tool.
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

    def test_extra_is_independent_dict(self) -> None:
        """
        Каждый экземпляр RequestInfo имеет свой словарь extra.

        Dataclass field(default_factory=dict) гарантирует независимость.
        """
        # Arrange — два экземпляра без явного extra
        r1 = RequestInfo()
        r2 = RequestInfo()

        # Act — модификация extra одного экземпляра
        r1.extra["key"] = "value"

        # Assert — второй экземпляр не затронут
        assert r1.extra == {"key": "value"}
        assert r2.extra == {}

    def test_tags_is_independent_dict(self) -> None:
        """
        Каждый экземпляр RequestInfo имеет свой словарь tags.
        """
        # Arrange — два экземпляра
        r1 = RequestInfo()
        r2 = RequestInfo()

        # Act — модификация tags
        r1.tags["env"] = "prod"

        # Assert — независимость
        assert r1.tags == {"env": "prod"}
        assert r2.tags == {}


# ═════════════════════════════════════════════════════════════════════════════
# ReadableMixin — dict-подобный доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoDictAccess:
    """Dict-подобный доступ к полям RequestInfo через ReadableMixin."""

    def test_getitem(self) -> None:
        """
        request["trace_id"] → значение поля.
        """
        # Arrange
        request = RequestInfo(trace_id="trace-001")

        # Act & Assert
        assert request["trace_id"] == "trace-001"

    def test_contains(self) -> None:
        """
        "trace_id" in request → True для существующих атрибутов dataclass.

        Все поля dataclass существуют как атрибуты (даже если значение None),
        поэтому hasattr возвращает True.
        """
        # Arrange
        request = RequestInfo()

        # Act & Assert — поля dataclass всегда существуют
        assert "trace_id" in request
        assert "request_path" in request
        assert "extra" in request
        assert "nonexistent" not in request

    def test_get_with_default(self) -> None:
        """
        request.get("nonexistent", "default") → "default".
        """
        # Arrange
        request = RequestInfo(trace_id="t1")

        # Act & Assert
        assert request.get("trace_id") == "t1"
        assert request.get("nonexistent", "fallback") == "fallback"

    def test_keys_contains_all_dataclass_fields(self) -> None:
        """
        keys() возвращает все публичные поля dataclass.

        RequestInfo имеет 10 полей: trace_id, request_timestamp,
        request_path, request_method, full_url, client_ip, protocol,
        user_agent, extra, tags.
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
        assert "extra" in keys
        assert "tags" in keys


# ═════════════════════════════════════════════════════════════════════════════
# ReadableMixin — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoResolve:
    """Навигация по полям RequestInfo через resolve()."""

    def test_resolve_flat_field(self) -> None:
        """
        resolve("trace_id") — прямой доступ к плоскому полю.
        """
        # Arrange
        request = RequestInfo(trace_id="trace-abc-123")

        # Act
        result = request.resolve("trace_id")

        # Assert
        assert result == "trace-abc-123"

    def test_resolve_none_field(self) -> None:
        """
        resolve("client_ip") когда client_ip=None → возвращает None.

        None — валидное значение, поле существует в dataclass.
        """
        # Arrange — client_ip не задан, по умолчанию None
        request = RequestInfo()

        # Act
        result = request.resolve("client_ip")

        # Assert — None из атрибута
        assert result is None

    def test_resolve_extra_nested(self) -> None:
        """
        resolve("extra.correlation_id") — навигация через extra-словарь.
        """
        # Arrange
        request = RequestInfo(extra={"correlation_id": "corr-xyz"})

        # Act
        result = request.resolve("extra.correlation_id")

        # Assert
        assert result == "corr-xyz"

    def test_resolve_tags(self) -> None:
        """
        resolve("tags") → весь словарь тегов.
        """
        # Arrange
        request = RequestInfo(tags={"ab_test": "control", "feature": "new_ui"})

        # Act
        result = request.resolve("tags")

        # Assert — словарь целиком
        assert result == {"ab_test": "control", "feature": "new_ui"}

    def test_resolve_missing_returns_default(self) -> None:
        """
        resolve("nonexistent", default="N/A") → "N/A".
        """
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
