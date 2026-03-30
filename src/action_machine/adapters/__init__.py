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

- BaseAdapter[R] — абстрактный generic-класс адаптера. Параметр R —
  тип конкретного RouteRecord (наследника BaseRouteRecord). Определяет
  контракт: хранение маршрутов в _routes, построение протокольного
  приложения через build(). Конкретные адаптеры (FastAPIAdapter,
  MCPAdapter) наследуют BaseAdapter, реализуют протокольные методы
  регистрации (post, get, tool) и build().

- BaseRouteRecord — абстрактный frozen-датакласс, хранящий конфигурацию
  одного зарегистрированного маршрута. Содержит общее для всех протоколов
  обязательное поле action_class и опциональные поля маппинга
  (request_model, response_model, params_mapper, result_mapper).
  Протокольно-специфичные поля (HTTP-метод, путь, теги, tool_name)
  определяются в конкретных наследниках (FastAPIRouteRecord,
  MCPRouteRecord). Нельзя инстанцировать напрямую.

- extract_action_types(action_class) — функция извлечения generic-
  параметров P и R из BaseAction[P, R]. Обходит __orig_bases__ в MRO
  класса действия. Вызывается автоматически при создании RouteRecord.

═══════════════════════════════════════════════════════════════════════════════
АВТОИЗВЛЕЧЕНИЕ ТИПОВ
═══════════════════════════════════════════════════════════════════════════════

params_type и result_type ВСЕГДА извлекаются автоматически из generic-
параметров BaseAction[P, R] класса действия. Разработчик никогда не
указывает их вручную. Это единый источник правды: типы определены
в классе действия и не дублируются.

Если протокольные модели (request_model, response_model) совпадают
с params_type/result_type — они не указываются вовсе. Мапперы нужны
только когда протокольные модели отличаются от типов действия.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Обработка ошибок — ответственность конкретного адаптера. Адаптер
перехватывает исключения ActionMachine (AuthorizationError,
ValidationFieldError, ConnectionValidationError и др.) в except-блоках
и самостоятельно решает, как преобразовать их в протокольный ответ.

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

BaseRouteRecord проверяет инварианты при создании:

1. Если request_model указан и отличается от params_type, params_mapper
   обязателен. Без маппера адаптер не может преобразовать протокольный
   запрос в параметры действия.

2. Если response_model указан и отличается от result_type, result_mapper
   обязателен. Без маппера адаптер не может преобразовать результат
   действия в протокольный ответ.

Если request_model не указан (None) или совпадает с params_type —
маппер не нужен, адаптер передаёт объект напрямую.

═══════════════════════════════════════════════════════════════════════════════
API КОНКРЕТНОГО АДАПТЕРА
═══════════════════════════════════════════════════════════════════════════════

Каждый конкретный адаптер определяет свои протокольные методы. Один
вызов метода = один зарегистрированный маршрут. Минимальный вызов
требует только путь и класс действия:

    adapter = FastAPIAdapter(machine=machine, auth_coordinator=auth)

    # Минимум — request_model совпадает с params_type:
    adapter.post("/orders/create", CreateOrderAction)

    # request_model отличается — нужен params_mapper:
    adapter.get("/orders/list", ListOrdersAction,
                request_model=ListOrdersRequest,
                params_mapper=map_list_request)

    # Оба отличаются — нужны оба маппера:
    adapter.get("/orders/{id}", GetOrderAction,
                request_model=GetRequest,
                response_model=GetResponse,
                params_mapper=map_get_request,
                result_mapper=map_get_response)

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
    │  ConcreteAdapter     │   FastAPIAdapter, MCPAdapter, ...
    │  extends BaseAdapter │
    │                      │
    │  post(path, action)  │──▶ Создаёт RouteRecord, добавляет в _routes
    │  get(path, action)   │──▶ Создаёт RouteRecord, добавляет в _routes
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
from .base_route_record import BaseRouteRecord, extract_action_types

__all__ = [
    "BaseAdapter",
    "BaseRouteRecord",
    "extract_action_types",
]
