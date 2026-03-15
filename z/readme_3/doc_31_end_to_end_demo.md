31_end_to_end_demo.md

# Полный пример от HTTP до результата

Этот документ показывает полный путь данных в системе построенной на ActionEngine. От входящего HTTP-запроса до финального результата — каждый слой виден, понятен и тестируем. Все концепции AOA работают вместе в одном файле [1].

---

## Что показывает этот пример

Полный цикл включает:

HTTP-запрос принимается FastAPI. AuthCoordinator формирует Context из заголовков запроса. ActionMachine запускает Action через полный конвейер аспектов. Action использует ресурсный менеджер через DI. Result сериализуется и возвращается клиенту.

---

## Структура файла

```
http_full_cycle_demo.py
├── Resource (FileStorage + CsvConnectionManager)
├── Port (StoragePort)
├── Adapter (StorageAdapter)
├── Action (SaveDataAction)
├── Auth (Extractor, Authenticator, Assembler, Coordinator)
└── FastAPI endpoint
```

---

## Шаг 1. Ресурс — адаптер к внешней системе

```python
from ActionMachine.ResourceManagers.CsvConnectionManager import CsvConnectionManager
from ActionMachine.Core.Exceptions import HandleException

class FileStorage:
    def __init__(self, conn: CsvConnectionManager):
        self.conn = conn

    def save_record(self, row: dict) -> None:
        try:
            self.conn.open()
            self.conn.write_rows(list(row.keys()), [list(row.values())])
            self.conn.commit()
        except Exception as e:
            raise HandleException(f"Ошибка записи: {e}") from e
```

FileStorage инкапсулирует работу с CSV. Ошибки оборачиваются в HandleException. Action не знает что именно происходит внутри [1].

---

## Шаг 2. Порт и адаптер

```python
from abc import ABC, abstractmethod

class StoragePort(ABC):

    @abstractmethod
    def save(self, row: dict) -> None: ...


class StorageAdapter(StoragePort):

    def __init__(self):
        self._manager = CsvConnectionManager("logs/demo.csv")

    def save(self, row: dict) -> None:
        FileStorage(self._manager).save_record(row)
```

Action зависит от StoragePort а не от StorageAdapter. Это позволяет подменять реализацию в тестах без изменения бизнес-логики [1].

---

## Шаг 3. Action

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

@dataclass(frozen=True)
class SaveParams(BaseParams):
    user_id: str
    data: str

@dataclass(frozen=True)
class SaveResult(BaseResult):
    ok: bool

@depends(StorageAdapter)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class SaveDataAction(BaseAction):

    @aspect("Подготовка записи")
    async def prepare(self, params, state, deps):
        state["row"] = {
            "user_id": params.user_id,
            "data": params.data
        }
        return state

    @summary_aspect("Сохранение данных")
    async def handle(self, params, state, deps):
        storage = deps.get(StorageAdapter)
        storage.save(state["row"])
        return SaveResult(ok=True)
```

Два аспекта. Первый готовит данные. Второй сохраняет через ресурс. Action не знает про HTTP, про CSV, про путь к файлу [1].

---

## Шаг 4. Аутентификация

```python
from ActionMachine.Auth.CredentialExtractor import CredentialExtractor
from ActionMachine.Auth.Authenticator import Authenticator
from ActionMachine.Auth.ContextAssembler import ContextAssembler
from ActionMachine.Auth.AuthCoordinator import AuthCoordinator
from ActionMachine.Context.UserInfo import UserInfo

class SimpleExtractor(CredentialExtractor):

    def extract(self, request) -> dict:
        user = request.headers.get("X-User")
        return {"user": user} if user else {}


class SimpleAuthenticator(Authenticator):

    def authenticate(self, credentials) -> UserInfo | None:
        user = credentials.get("user")
        if not user:
            return None
        return UserInfo(
            user_id=user,
            roles=["user"],
            extra={"auth_method": "header"}
        )


class SimpleAssembler(ContextAssembler):

    def assemble(self, request) -> dict:
        return {
            "trace_id": request.headers.get("X-Trace-ID", "no-trace"),
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "protocol": "http",
            "user_agent": request.headers.get("User-Agent"),
            "extra": {},
            "tags": {}
        }


coordinator = AuthCoordinator(
    extractor=SimpleExtractor(),
    authenticator=SimpleAuthenticator(),
    assembler=SimpleAssembler()
)
```

Три компонента собираются в координатор. Каждый отвечает за свою задачу — извлечение, проверку, сборку метаданных. Результат — готовый Context [1].

---

## Шаг 5. FastAPI endpoint

```python
from fastapi import FastAPI, Request, HTTPException
from ActionMachine.Core.ActionProductMachine import ActionProductMachine

app = FastAPI()

@app.post("/save")
async def save_endpoint(request: Request):
    ctx = coordinator.process(request)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()

    params = SaveParams(
        user_id=ctx.user.user_id,
        data=body.get("data", "")
    )

    machine = ActionProductMachine(context=ctx)
    result = await machine.run(SaveDataAction(), params)

    return {
        "ok": result.ok,
        "user_id": ctx.user.user_id,
        "trace_id": ctx.request.trace_id
    }
```

Action не видит Request. Он получает только Params. Context не доступен внутри аспектов — только плагинам и машине [1].

---

## Шаг 6. Тест без FastAPI

Бизнес-логика тестируется без поднятия веб-сервера:

```python
import pytest
from ActionMachine.Core.ActionTestMachine import ActionTestMachine
from ActionMachine.Context.Context import Context
from ActionMachine.Context.UserInfo import UserInfo

class FakeStorageAdapter(StoragePort):

    def __init__(self):
        self.saved = []

    def save(self, row: dict) -> None:
        self.saved.append(row)


@pytest.mark.asyncio
async def test_save_data_action():
    fake_storage = FakeStorageAdapter()

    ctx = Context(
        user=UserInfo(user_id="user_42", roles=["user"], extra={})
    )

    machine = ActionTestMachine(
        {StorageAdapter: fake_storage},
        context=ctx
    )

    result = await machine.run(
        SaveDataAction(),
        SaveParams(user_id="user_42", data="hello")
    )

    assert result.ok is True
    assert len(fake_storage.saved) == 1
    assert fake_storage.saved[0]["user_id"] == "user_42"
    assert fake_storage.saved[0]["data"] == "hello"
```

Тест проверяет бизнес-логику. Нет реального файла. Нет HTTP. Нет сервера. Только чистая логика [1].

---

## Что происходит в этом примере по слоям

Первый слой — транспорт. FastAPI принимает запрос. AuthCoordinator собирает Context. Params формируются из тела запроса и данных пользователя.

Второй слой — машина. ActionMachine проверяет роли. Вызывает аспекты по порядку. Управляет DI через DependencyFactory.

Третий слой — бизнес-логика. Аспект prepare готовит словарь. Аспект handle сохраняет через ресурс. Summary возвращает Result.

Четвёртый слой — инфраструктура. StorageAdapter вызывает FileStorage. FileStorage использует CsvConnectionManager. Ошибки оборачиваются в HandleException.

---

## Итог

Этот пример показывает что AOA — это не теория. Это рабочая архитектура где каждый слой делает свою задачу, не зная о других слоях [1].

Action не знает про HTTP. HTTP не знает про бизнес-правила. Ресурс не знает про роли. Машина не знает что именно сохраняется.

Каждый слой заменяем. Каждый слой тестируем. Каждый слой читается как документация.

Это и есть AOA.