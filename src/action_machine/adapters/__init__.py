# src/action_machine/adapters/__init__.py
"""
Пакет адаптеров ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит базовую инфраструктуру адаптеров — компонентов, преобразующих
внешние протоколы (HTTP, MCP, gRPC, CLI) в вызовы
``machine.run(context, action, params, connections)``.

Адаптер — это мост между внешним миром и ядром ActionMachine. Он принимает
запрос в протокольном формате (HTTP-запрос, MCP tool call, gRPC message),
извлекает из него параметры, аутентифицирует пользователя, вызывает
действие через машину и возвращает результат в протокольном формате.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- BaseAdapter[B] — абстрактный generic-класс адаптера. Параметр B —
  тип fluent-builder для конкретного протокола. Определяет контракт:
  route() для регистрации действий, build() для создания протокольного
  приложения. Конкретные адаптеры (FastAPIAdapter, MCPAdapter)
  наследуют BaseAdapter и реализуют _create_builder() и build().

- BaseRouteRecord — абстрактный frozen-датакласс, хранящий конфигурацию
  одного зарегистрированного маршрута. Содержит общие для всех протоколов
  поля: класс действия, типы параметров/результата, модели запроса/ответа,
  мапперы. Протокольно-специфичные поля (HTTP-метод, путь, теги, tool_name)
  определяются в конкретных наследниках (FastAPIRouteRecord, MCPRouteRecord).
  Нельзя инстанцировать напрямую.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Обработка ошибок — ответственность конкретного адаптера. Адаптер
перехватывает исключения ActionMachine (AuthorizationError,
ValidationFieldError, ConnectionValidationError и др.) в except-блоках
и самостоятельно решает, как преобразовать их в протокольный ответ.

Промежуточный слой маппинга ошибок не требуется: адаптер знает свой
протокол, знает исключения ядра и обрабатывает их напрямую.

    Пример для FastAPI:
        except AuthorizationError as exc:
            return JSONResponse(status_code=403, content={"error": str(exc)})
        except ValidationFieldError as exc:
            return JSONResponse(status_code=422, content={"error": str(exc)})
        except Exception as exc:
            return JSONResponse(status_code=500, content={"error": str(exc)})

═══════════════════════════════════════════════════════════════════════════════
ТИПИЗАЦИЯ МАРШРУТОВ
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord — абстрактный, содержит только общие поля. Каждый конкретный
адаптер определяет свой наследник с типизированными протокольно-специфичными
полями. IDE автодополняет конкретные поля, mypy проверяет типы:

    @dataclass(frozen=True)
    class FastAPIRouteRecord(BaseRouteRecord):
        method: str = "POST"
        path: str = "/"
        tags: tuple[str, ...] = ()
        summary: str = ""

    @dataclass(frozen=True)
    class MCPRouteRecord(BaseRouteRecord):
        tool_name: str = ""
        description: str = ""

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТЫ МАППИНГА
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord проверяет два инварианта при создании:

1. Если params_type и request_model — разные классы, params_mapper
   обязателен. Без маппера адаптер не может преобразовать протокольный
   запрос в параметры действия.

2. Если result_type и response_model — разные классы, result_mapper
   обязателен. Без маппера адаптер не может преобразовать результат
   действия в протокольный ответ.

Если типы совпадают (params_type is request_model), маппер не нужен —
адаптер передаёт объект напрямую без преобразования.

═══════════════════════════════════════════════════════════════════════════════
FLUENT-BUILDER ПАТТЕРН
═══════════════════════════════════════════════════════════════════════════════

Каждый конкретный адаптер определяет свой Builder-класс с протокольно-
специфичными методами:

    adapter = FastAPIAdapter(machine=machine, auth_coordinator=auth)

    adapter.route(CreateOrderAction) \\
        .post("/api/v1/orders") \\
        .tags(["orders"]) \\
        .summary("Создание заказа") \\
        .request_model(CreateOrderRequest) \\
        .response_model(CreateOrderResponse) \\
        .params_mapper(lambda req: OrderParams(...)) \\
        .result_mapper(lambda res: CreateOrderResponse(...)) \\
        .register()

    app = adapter.build()

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────┐
    │  Внешний протокол    │   HTTP, MCP, gRPC, CLI
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  ConcreteAdapter[B]  │   FastAPIAdapter, MCPAdapter, ...
    │  extends BaseAdapter │
    │                      │
    │  route(ActionClass)  │──▶ Builder (fluent API)
    │  build()             │──▶ Протокольное приложение
    └──────────┬───────────┘
               │
               │  machine.run(context, action, params, connections)
               ▼
    ┌──────────────────────┐
    │  ActionProductMachine │
    └──────────────────────┘
"""

from .base_adapter import BaseAdapter
from .base_route_record import BaseRouteRecord

__all__ = [
    "BaseAdapter",
    "BaseRouteRecord",
]
