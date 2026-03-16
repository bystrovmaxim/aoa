21_fastapi_integration.md

# Интеграция ActionEngine с FastAPI

ActionEngine спроектирован так, чтобы легко интегрироваться с любым транспортом. FastAPI — один из лучших вариантов благодаря своей типизации и асинхронной природе. Задача интеграции — собрать данные запроса, выполнить аутентификацию, создать Context и вызвать ActionMachine.run [1].

---

## Общая схема интеграции

Поток данных проходит через четыре слоя:

Первый слой — FastAPI принимает HTTP-запрос.

Второй слой — AuthCoordinator извлекает учётные данные, проверяет пользователя и собирает метаданные запроса. Результат — готовый Context.

Третий слой — ActionMachine получает Action, Params и Context. Выполняет конвейер аспектов.

Четвёртый слой — Result сериализуется и возвращается клиенту как HTTP-ответ.

Actions никогда не видят объект Request. Они работают только с Params и deps [1].

---

## Реализация CredentialExtractor для HTTP

Extractor извлекает учётные данные из HTTP-заголовков:

```python
from typing import Any, Dict
from fastapi import Request
from ActionMachine.Auth.CredentialExtractor import CredentialExtractor

class FastAPICredentialExtractor(CredentialExtractor):

    def extract(self, request: Request) -> Dict[str, Any]:
        api_key = request.headers.get("X-API-Key")
        bearer = request.headers.get("Authorization", "").replace("Bearer ", "")
        if api_key:
            return {"api_key": api_key, "auth_type": "api_key"}
        if bearer:
            return {"token": bearer, "auth_type": "bearer"}
        return {}
```

Extractor отвечает только за нормализацию входящих данных. Никакой проверки — только извлечение [1].

---

## Реализация Authenticator

Authenticator принимает credentials и создаёт UserInfo:

```python
from typing import Any, Dict, Optional
from ActionMachine.Auth.Authenticator import Authenticator
from ActionMachine.Context.UserInfo import UserInfo

VALID_API_KEYS = {
    "key_admin_001": {"user_id": "admin_1", "roles": ["admin"]},
    "key_user_001": {"user_id": "user_1", "roles": ["user"]},
}

class APIKeyAuthenticator(Authenticator):

    def authenticate(self, credentials: Dict[str, Any]) -> Optional[UserInfo]:
        if credentials.get("auth_type") == "api_key":
            key = credentials.get("api_key")
            user_data = VALID_API_KEYS.get(key)
            if user_data:
                return UserInfo(
                    user_id=user_data["user_id"],
                    roles=user_data["roles"],
                    extra={"auth_method": "api_key"}
                )
        return None
```

---

## Реализация ContextAssembler для HTTP

Assembler собирает метаданные HTTP-запроса в словарь для RequestInfo:

```python
import uuid
from datetime import datetime
from typing import Any, Dict
from fastapi import Request
from ActionMachine.Auth.ContextAssembler import ContextAssembler

class FastAPIContextAssembler(ContextAssembler):

    def assemble(self, request: Request) -> Dict[str, Any]:
        return {
            "trace_id": request.headers.get("X-Trace-ID", str(uuid.uuid4())),
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "method": request.method,
            "full_url": str(request.url),
            "client_ip": request.client.host if request.client else None,
            "protocol": "http",
            "user_agent": request.headers.get("User-Agent"),
            "extra": {},
            "tags": {}
        }
```

---

## Сборка AuthCoordinator

Все три компонента объединяются в AuthCoordinator:

```python
from ActionMachine.Auth.AuthCoordinator import AuthCoordinator

coordinator = AuthCoordinator(
    extractor=FastAPICredentialExtractor(),
    authenticator=APIKeyAuthenticator(),
    assembler=FastAPIContextAssembler()
)
```

AuthCoordinator.process принимает объект запроса и возвращает готовый Context или None если аутентификация не прошла [1].

---

## FastAPI-зависимость для получения Context

Оборачиваем coordinator в FastAPI Depends:

```python
from fastapi import Depends, HTTPException, Request
from ActionMachine.Context.Context import Context

async def get_context(request: Request) -> Context:
    ctx = coordinator.process(request)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return ctx
```

Теперь любой эндпоинт может получить готовый Context через стандартный механизм FastAPI.

---

## Создание машины и плагинов

ActionProductMachine создаётся для каждого запроса с актуальным Context:

```python
from ActionMachine.Core.ActionProductMachine import ActionProductMachine
from ActionMachine.Context.EnvironmentInfo import EnvironmentInfo
import socket

env_info = EnvironmentInfo(
    hostname=socket.gethostname(),
    service_name="my_service",
    service_version="1.0.0",
    environment="production",
    container_id=None,
    pod_name=None,
    extra={}
)
```

Машина с плагинами:

```python
from ActionMachine.Plugins.Plugin import Plugin

def create_machine(ctx: Context) -> ActionProductMachine:
    return ActionProductMachine(
        context=ctx,
        plugins=[
            ConsoleLoggingPlugin(),
            MetricsPlugin()
        ]
    )
```

---

## Полный пример эндпоинта

Минимальный рабочий эндпоинт который принимает запрос, формирует Context, запускает Action и возвращает Result:

```python
from fastapi import FastAPI, Depends, Request
from dataclasses import asdict

app = FastAPI()

@app.post("/orders")
async def create_order(
    request: Request,
    ctx: Context = Depends(get_context)
):
    body = await request.json()

    params = CreateOrderAction.Params(
        user_id=ctx.user.user_id,
        product_id=body["product_id"],
        quantity=body["quantity"]
    )

    machine = create_machine(ctx)
    result = await machine.run(CreateOrderAction(), params)

    return asdict(result)
```

Action не видит Request. Он видит только Params. Context недоступен внутри аспектов [1].

---

## Обработка ошибок

FastAPI позволяет зарегистрировать обработчики исключений для всех типов ошибок ActionEngine:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from ActionMachine.Core.Exceptions import (
    HandleException,
    AuthorizationException,
    ValidationFieldException
)

app = FastAPI()

@app.exception_handler(AuthorizationException)
async def auth_exception_handler(request: Request, exc: AuthorizationException):
    return JSONResponse(status_code=403, content={"detail": str(exc)})

@app.exception_handler(ValidationFieldException)
async def validation_exception_handler(request: Request, exc: ValidationFieldException):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(HandleException)
async def handle_exception_handler(request: Request, exc: HandleException):
    return JSONResponse(status_code=500, content={"detail": "Internal error"})

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
```

---

## Автоматическая генерация эндпоинтов

Благодаря строгой декларативности AOA можно написать генератор который автоматически создаёт FastAPI-роутеры из Actions. Каждый Action имеет Params как dataclass, Result как dataclass и CheckRoles на классе [1].

Простой пример генератора:

```python
from fastapi import APIRouter
from dataclasses import asdict

def register_action(
    router: APIRouter,
    path: str,
    action_class,
    method: str = "post"
):
    async def endpoint(request: Request, ctx: Context = Depends(get_context)):
        body = await request.json()
        params = action_class.Params(**body)
        machine = create_machine(ctx)
        result = await machine.run(action_class(), params)
        return asdict(result)

    router.add_api_route(path, endpoint, methods=[method.upper()])


router = APIRouter()
register_action(router, "/orders", CreateOrderAction)
register_action(router, "/users", CreateUserAction)
register_action(router, "/payments", ProcessPaymentAction)
app.include_router(router)
```

---

## Тестирование без FastAPI

Одно из главных преимуществ интеграции — тесты не зависят от транспорта. ActionTestMachine запускает те же Actions без поднятия веб-сервера:

```python
import pytest
from ActionMachine.Core.ActionTestMachine import ActionTestMachine
from ActionMachine.Context.Context import Context
from ActionMachine.Context.UserInfo import UserInfo

@pytest.mark.asyncio
async def test_create_order_without_fastapi():
    ctx = Context(
        user=UserInfo(user_id="user_1", roles=["user"], extra={})
    )

    machine = ActionTestMachine(
        {
            ProductRepository: FakeProductRepository(),
            OrderRepository: FakeOrderRepository()
        },
        context=ctx
    )

    result = await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(
            user_id="user_1",
            product_id=10,
            quantity=2
        )
    )

    assert result.order_id is not None
```

Тест проверяет бизнес-логику а не HTTP-слой.

---

## Трёхуровневая архитектура

Интеграция с FastAPI формирует чистую трёхуровневую архитектуру:

Первый уровень — транспорт. FastAPI принимает запрос, извлекает данные, формирует Context через AuthCoordinator. Знает о HTTP. Не знает о бизнес-логике.

Второй уровень — авторизация и Context. AuthCoordinator, CredentialExtractor, Authenticator, ContextAssembler. Формирует единый объект Context независимо от транспорта.

Третий уровень — бизнес-логика. Actions, аспекты, Resources. Ничего не знает о HTTP, заголовках, сессиях, cookies [1].

Это означает что при смене транспорта с FastAPI на gRPC или MCP нужно заменить только первый уровень. Вся бизнес-логика остаётся нетронутой.

---

## Что изучать дальше

22_mcp_integration.md — интеграция с MCP для LLM-агентов.

20_auth_architecture.md — детальное описание AuthCoordinator.

19_testing.md — тестирование без транспорта.

18_plugins.md — плагины для логирования HTTP-запросов.

31_end_to_end_demo.md — полный пример от HTTP до результата.