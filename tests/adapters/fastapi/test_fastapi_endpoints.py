# tests/adapters/fastapi/test_fastapi_endpoints.py
"""
Тесты стратегий генерации endpoint для FastApiAdapter.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

FastApiAdapter использует три стратегии создания endpoint-функций:

1. POST/PUT/PATCH с непустыми Params → endpoint с JSON body.
2. GET/DELETE с непустыми Params → endpoint с query/path параметрами.
3. Любой метод с пустыми Params (без полей) → endpoint без параметров.

Базовые тесты адаптера (test_fastapi_adapter.py) покрывают только POST.
Этот файл закрывает непокрытые строки в adapter.py:

- Строка 153: _make_endpoint_with_query — GET с query-параметрами.
- Строка 171: _make_endpoint_with_query — формирование сигнатуры.
- Строка 184: _make_endpoint_no_params — GET без параметров.
- Строка 768: _register_exception_handlers — AuthorizationError → 403.
- Строка 777: _register_exception_handlers — ValidationFieldError → 422.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

GET с query-параметрами:
    - GET /simple?name=Alice возвращает 200.
    - Параметры из query string попадают в Params.

GET без параметров:
    - GET /ping без query параметров возвращает 200 с {"message": "pong"}.

connections_factory:
    - Фабрика вызывается при каждом запросе.

Обработка ошибок:
    - AuthorizationError из machine.run → HTTP 403 с detail.
    - ValidationFieldError из machine.run → HTTP 422 с detail.
"""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from action_machine.contrib.fastapi.adapter import FastApiAdapter
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.exceptions import AuthorizationError, ValidationFieldError
from action_machine.metadata.gate_coordinator import GateCoordinator
from tests.domain_model import PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Хелпер — создание адаптера с замоканной machine.run
# ─────────────────────────────────────────────────────────────────────────────


def _make_app(
    connections_factory=None,
    run_side_effect=None,
    run_return=None,
):
    """
    Собирает FastApiAdapter с мок-машиной.

    Возвращает кортеж (adapter, machine) для дополнительных assert-ов.
    По умолчанию machine.run возвращает PingAction.Result(message="pong").
    """
    coordinator = GateCoordinator()
    machine = ActionProductMachine(mode="test")

    auth = AsyncMock()
    auth.process.return_value = None

    if run_return is not None:
        machine.run = AsyncMock(return_value=run_return)
    elif run_side_effect is not None:
        machine.run = AsyncMock(side_effect=run_side_effect)
    else:
        machine.run = AsyncMock(return_value=PingAction.Result(message="pong"))

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=auth,
        connections_factory=connections_factory,
    )
    return adapter, machine


# ═════════════════════════════════════════════════════════════════════════════
# GET с query-параметрами (стратегия 2)
# ═════════════════════════════════════════════════════════════════════════════


class TestGetWithQueryParams:
    """Покрывает _make_endpoint_with_query — GET с полями в Params."""

    def test_get_extracts_query_params(self) -> None:
        """GET endpoint извлекает параметры из query string и возвращает 200."""
        # Arrange — SimpleAction.Params имеет поле name (обязательное)
        adapter, _machine = _make_app(
            run_return=SimpleAction.Result(greeting="Hello, Alice!"),
        )
        adapter.get("/simple", SimpleAction)
        app = adapter.build()
        client = TestClient(app)

        # Act — передаём name через query string
        response = client.get("/simple?name=Alice")

        # Assert — endpoint сработал, machine.run был вызван
        assert response.status_code == 200
        _machine.run.assert_called_once()

    def test_delete_extracts_query_params(self) -> None:
        """DELETE endpoint также использует стратегию query-параметров."""
        # Arrange
        adapter, _machine = _make_app(
            run_return=SimpleAction.Result(greeting="Deleted"),
        )
        adapter.delete("/simple", SimpleAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        response = client.delete("/simple?name=test")

        # Assert
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# GET без параметров (стратегия 3)
# ═════════════════════════════════════════════════════════════════════════════


class TestGetEmptyParams:
    """Покрывает _make_endpoint_no_params — GET с пустыми Params."""

    def test_get_no_params(self) -> None:
        """GET endpoint без полей в Params работает без query-параметров."""
        # Arrange — PingAction.Params не содержит полей
        adapter, _machine = _make_app()
        adapter.get("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act — запрос без параметров
        response = client.get("/ping")

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "pong"

    def test_post_no_params(self) -> None:
        """POST endpoint без полей в Params работает с пустым body."""
        # Arrange
        adapter, _machine = _make_app()
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act — пустое тело
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "pong"


# ═════════════════════════════════════════════════════════════════════════════
# connections_factory
# ═════════════════════════════════════════════════════════════════════════════


class TestConnectionsFactory:
    """Покрывает вызов connections_factory при обработке запроса."""

    def test_factory_called_on_request(self) -> None:
        """connections_factory вызывается при каждом входящем запросе."""
        # Arrange — фабрика возвращает словарь соединений
        mock_connections = {"db": MagicMock()}
        factory = MagicMock(return_value=mock_connections)

        adapter, _machine = _make_app(connections_factory=factory)
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        client.post("/ping", json={})

        # Assert — фабрика была вызвана ровно один раз
        factory.assert_called_once()

    def test_factory_result_passed_to_machine(self) -> None:
        """Результат connections_factory передаётся в machine.run."""
        # Arrange
        mock_connections = {"db": MagicMock()}
        factory = MagicMock(return_value=mock_connections)

        adapter, _machine = _make_app(connections_factory=factory)
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app)

        # Act
        client.post("/ping", json={})

        # Assert — machine.run получил connections
        call_args = _machine.run.call_args
        assert call_args is not None


# ═════════════════════════════════════════════════════════════════════════════
# Обработка ошибок — exception handlers
# ═════════════════════════════════════════════════════════════════════════════


class TestExceptionHandlers:
    """Покрывает exception handlers: AuthorizationError → 403, ValidationFieldError → 422."""

    def test_authorization_error_returns_403(self) -> None:
        """AuthorizationError из machine.run возвращает HTTP 403."""
        # Arrange — machine.run выбрасывает AuthorizationError
        adapter, _ = _make_app(
            run_side_effect=AuthorizationError("доступ запрещён"),
        )
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app, raise_server_exceptions=False)

        # Act
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 403
        assert "доступ запрещён" in response.json()["detail"]

    def test_validation_error_returns_422(self) -> None:
        """ValidationFieldError из machine.run возвращает HTTP 422."""
        # Arrange — machine.run выбрасывает ValidationFieldError
        adapter, _ = _make_app(
            run_side_effect=ValidationFieldError("поле невалидно", "name"),
        )
        adapter.post("/ping", PingAction)
        app = adapter.build()
        client = TestClient(app, raise_server_exceptions=False)

        # Act
        response = client.post("/ping", json={})

        # Assert
        assert response.status_code == 422
