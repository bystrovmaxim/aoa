22_mcp_integration.md

# Интеграция ActionEngine с MCP

MCP — Model Context Protocol — это протокол для взаимодействия LLM-агентов с внешними инструментами и сервисами. Интеграция ActionEngine с MCP позволяет использовать Actions как инструменты для языковых моделей. Каждое действие становится вызываемым инструментом с типизированными входными данными и предсказуемым результатом [1].

---

## Основная идея

Actions в AOA идеально подходят для MCP по одной причине: каждое действие имеет строгий контракт через Params и Result, единственную точку входа через machine.run и полную независимость от транспорта [1].

MCP — это просто ещё один транспортный слой. Он передаёт команду агента в систему, система выполняет действие и возвращает результат. Actions не знают что их вызывает агент, а не HTTP-запрос.

---

## Поток данных

Полный поток выглядит так:

Первый шаг. LLM-агент формирует tool call с именем инструмента и аргументами.

Второй шаг. MCP-сервер получает запрос в структурированном формате.

Третий шаг. MCP CredentialExtractor извлекает учётные данные из payload.

Четвёртый шаг. Authenticator проверяет credentials и создаёт UserInfo.

Пятый шаг. ContextAssembler формирует RequestInfo из MCP-полей.

Шестой шаг. AuthCoordinator собирает полный Context.

Седьмой шаг. ActionProductMachine выполняет действие через полный конвейер аспектов.

Восьмой шаг. Result кодируется обратно в MCP-формат и возвращается агенту [1].

---

## CredentialExtractor для MCP

MCP-запрос приходит как структурированный словарь. Extractor извлекает из него токен или ключ:

```python
from typing import Any, Dict
from ActionMachine.Auth.CredentialExtractor import CredentialExtractor

class MCPCredentialExtractor(CredentialExtractor):

    def extract(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = request_data.get("metadata", {})
        token = metadata.get("auth_token")
        api_key = metadata.get("api_key")

        if api_key:
            return {"api_key": api_key, "auth_type": "api_key"}
        if token:
            return {"token": token, "auth_type": "bearer"}
        return {}
```

Extractor полностью независим от конкретного MCP-клиента. Он работает с любым payload который содержит нужные поля [1].

---

## ContextAssembler для MCP

Assembler извлекает метаданные из MCP-запроса для формирования RequestInfo:

```python
import uuid
from datetime import datetime
from typing import Any, Dict
from ActionMachine.Auth.ContextAssembler import ContextAssembler

class MCPContextAssembler(ContextAssembler):

    def assemble(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = request_data.get("metadata", {})
        return {
            "trace_id": metadata.get("request_id", str(uuid.uuid4())),
            "timestamp": datetime.utcnow().isoformat(),
            "path": request_data.get("tool", "unknown"),
            "method": "MCP_TOOL_CALL",
            "full_url": None,
            "client_ip": None,
            "protocol": "mcp",
            "user_agent": metadata.get("agent_name"),
            "extra": {"session": metadata.get("session")},
            "tags": {}
        }
```

---

## Authenticator для MCP

Authenticator работает так же как и для HTTP. Логика проверки не зависит от транспорта:

```python
from typing import Any, Dict, Optional
from ActionMachine.Auth.Authenticator import Authenticator
from ActionMachine.Context.UserInfo import UserInfo

VALID_AGENT_KEYS = {
    "agent_key_001": {"user_id": "agent_1", "roles": ["agent", "user"]},
    "agent_key_002": {"user_id": "agent_2", "roles": ["agent"]},
}

class MCPAuthenticator(Authenticator):

    def authenticate(self, credentials: Dict[str, Any]) -> Optional[UserInfo]:
        if credentials.get("auth_type") == "api_key":
            key = credentials.get("api_key")
            user_data = VALID_AGENT_KEYS.get(key)
            if user_data:
                return UserInfo(
                    user_id=user_data["user_id"],
                    roles=user_data["roles"],
                    extra={"auth_method": "mcp_api_key"}
                )
        return None
```

---

## Сборка AuthCoordinator для MCP

Три компонента объединяются в координатор:

```python
from ActionMachine.Auth.AuthCoordinator import AuthCoordinator

mcp_coordinator = AuthCoordinator(
    extractor=MCPCredentialExtractor(),
    authenticator=MCPAuthenticator(),
    assembler=MCPContextAssembler()
)
```

---

## Реестр инструментов

Actions регистрируются как MCP-инструменты через словарь. Каждый ключ — это имя инструмента которое LLM использует при вызове:

```python
from dataclasses import asdict

TOOL_REGISTRY = {
    "create_order": (CreateOrderAction, CreateOrderAction.Params),
    "calculate_discount": (CalculateDiscountAction, CalculateDiscountAction.Params),
    "get_user_info": (GetUserInfoAction, GetUserInfoAction.Params),
    "send_notification": (SendNotificationAction, SendNotificationAction.Params),
}
```

---

## Обработчик MCP-запроса

Центральная функция принимает MCP-запрос, формирует Context и запускает нужное действие:

```python
from ActionMachine.Core.ActionProductMachine import ActionProductMachine
from ActionMachine.Context.Context import Context

async def handle_mcp_tool_call(request_data: dict) -> dict:
    tool_name = request_data.get("tool")
    arguments = request_data.get("arguments", {})

    if tool_name not in TOOL_REGISTRY:
        return {
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(TOOL_REGISTRY.keys())
        }

    ctx = mcp_coordinator.process(request_data)
    if ctx is None:
        return {"error": "Authentication failed"}

    action_class, params_class = TOOL_REGISTRY[tool_name]

    try:
        params = params_class(**arguments)
        machine = ActionProductMachine(context=ctx)
        result = await machine.run(action_class(), params)
        return {"success": True, "result": asdict(result)}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": "Internal error"}
```

---

## Пример полного MCP-запроса

Запрос от LLM-агента:

```python
mcp_request = {
    "tool": "create_order",
    "arguments": {
        "user_id": 42,
        "product_id": 10,
        "quantity": 2
    },
    "metadata": {
        "request_id": "req_abc_123",
        "api_key": "agent_key_001",
        "agent_name": "OrderBot/1.0",
        "session": "AGENT-SESSION-42"
    }
}

response = await handle_mcp_tool_call(mcp_request)
```

Ответ который получает агент:

```python
{
    "success": True,
    "result": {
        "order_id": 1001,
        "total": 200.0,
        "status": "created"
    }
}
```

---

## Автоматическая генерация схемы инструментов

Поскольку каждый Action имеет строго типизированный Params как frozen dataclass, можно автоматически генерировать JSON Schema для MCP:

```python
import dataclasses
from typing import get_type_hints

def generate_tool_schema(action_class, params_class) -> dict:
    hints = get_type_hints(params_class)
    fields = dataclasses.fields(params_class)

    properties = {}
    required = []

    for field in fields:
        field_type = hints.get(field.name, str)
        type_map = {int: "integer", float: "number", str: "string", bool: "boolean"}
        properties[field.name] = {
            "type": type_map.get(field_type, "string"),
            "description": field.name
        }
        if field.default is dataclasses.MISSING:
            required.append(field.name)

    return {
        "name": action_class.__name__.replace("Action", "").lower(),
        "description": f"Execute {action_class.__name__}",
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }


def get_all_tool_schemas() -> list:
    return [
        generate_tool_schema(action_class, params_class)
        for action_class, params_class in TOOL_REGISTRY.values()
    ]
```

Теперь LLM получает полное описание всех доступных инструментов автоматически при каждом изменении Actions.

---

## Тестирование MCP-интеграции

Тесты не зависят от реального MCP-протокола. Actions тестируются через ActionTestMachine как обычно:

```python
import pytest
from ActionMachine.Core.ActionTestMachine import ActionTestMachine
from ActionMachine.Context.Context import Context
from ActionMachine.Context.UserInfo import UserInfo

@pytest.mark.asyncio
async def test_create_order_via_mcp():
    ctx = Context(
        user=UserInfo(
            user_id="agent_1",
            roles=["agent", "user"],
            extra={"auth_method": "mcp_api_key"}
        )
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
        CreateOrderAction.Params(user_id=42, product_id=10, quantity=2)
    )

    assert result.order_id is not None
    assert result.total > 0
```

Бизнес-логика тестируется без MCP-протокола, без агентов, без внешних зависимостей [1].

---

## Преимущества интеграции

Первое — Actions полностью независимы от протокола. Один и тот же Action работает через HTTP, MCP и CLI без изменений.

Второе — строгая типизация Params даёт LLM точную схему аргументов. Агент знает что передавать.

Третье — CheckRoles работает одинаково для HTTP и MCP. Агент не получит доступ к тому что ему не разрешено [1].

Четвёртое — плагины видят все события вызовов через MCP. Аудит и трассировка работают автоматически.

Пятое — тестирование не требует реального MCP-клиента или LLM.

---

## Сравнение с другими транспортами

В AOA смена транспорта требует только замены первого слоя — Extractor, Assembler и точки входа. Вся бизнес-логика остаётся нетронутой [1].

HTTP-запрос проходит через FastAPI Extractor и FastAPI Assembler. MCP-запрос проходит через MCP Extractor и MCP Assembler. CLI-вызов проходит через CLI Extractor и CLI Assembler. Actions и Resources не знают ни о каком из этих транспортов.

---

## Что изучать дальше

23_external_di_integration.md — интеграция с внешними DI-контейнерами.

20_auth_architecture.md — детальное описание AuthCoordinator.

21_fastapi_integration.md — интеграция с FastAPI.

19_testing.md — тестирование без транспорта.

18_plugins.md — плагины для логирования MCP-вызовов.

31_end_to_end_demo.md — полный пример от запроса до результата.
