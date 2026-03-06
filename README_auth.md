Ниже — **чёткая, простая и понятная документация**, ориентированная на людей, которые **не знают ActionEngine**, но должны **понять, как работает аутентификация и авторизация в проекте**.  

Я **не описываю весь фреймворк**, а только те классы и механизмы, которые непосредственно участвуют в аутентификации, авторизации и интеграции с API.

Все ссылки на код сопровождаются цитатами вида `[1]`, как по правилам.

---

# Документация  
Аутентификация и авторизация в проекте на ActionEngine

## 1. Зачем вообще нужны аутентификация и авторизация?

В проекте есть множество actions (действий), которые выполняют опасные операции:

- загрузка данных из YouTrack в PostgreSQL,
- удаление снимков (`DeleteSnapshotProgressAction` [1]),
- инициализация таблиц (`InitDatabaseAction` [1]),
- и т. д.

Чтобы никто не смог вызвать эти действия:

- без разрешения,
- без API‑ключа,
- без нужной роли,

вся система использует **два уровня защиты**:

1. **Аутентификация** — проверка, кто пользователь (например, по API‑ключу).  
2. **Авторизация** — проверка, может ли он выполнить конкретное действие.

Оба уровня обязательны.

---

# 2. Аутентификация — определяем личность пользователя

Аутентификация происходит **до выполнения Action**, на уровне API (FastAPI) или MCP сервера.  
Для аутентификации используется **класс Authenticator**.

## 2.1 Authenticator (интерфейс)

Это абстрактный класс — контракт, которому должна соответствовать любая реализация аутентификации.

Цитата [1]:

```
class Authenticator(ABC):
    def authenticate(self, credentials: Any) -> Optional[UserInfo]:
        ...
```

ЧТО ДЕЛАЕТ:

- принимает любые credentials (обычно API‑ключ),
- возвращает **UserInfo** — объект, описывающий пользователя,
- или `None`, если ключ неверный.

Никакой авторизации здесь ещё нет — только «кто ты?».

---

## 2.2 EnvApiKeyAuthenticator — текущая реализация

Это наша реализация аутентификации по API‑ключам из переменных окружения.

Цитата [1]:

```
class EnvApiKeyAuthenticator(Authenticator):
    def authenticate(self, api_key: str) -> Optional[UserInfo]:
        return self.keys.get(api_key)
```

Как работает:

- читает переменные окружения `API_KEY_*`,
- каждая переменная имеет вид `секрет:user_id:роль1,роль2`,
- строит словарь `secret_key → UserInfo` [1],
- при запросе ищет ключ в словаре.

Если ключ найден — пользователь аутентифицирован.

Если нет — возвращается 403.

---

## 2.3 Что такое UserInfo

UserInfo — это **декларация личности пользователя**.

Цитата [1]:

```
@dataclass
class UserInfo:
    user_id: Optional[str]
    roles: List[str]
    extra: Dict[str, Any]
```

Содержит:

- **user_id** — имя/ID пользователя,
- **roles** — список ролей (важно для авторизации),
- **extra** — метаданные (например, имя API‑ключа).

UserInfo участвует в проверке доступа к Actions.

---

# 3. Контекст Context — зачем он нужен

Context передаётся каждому Action.  
В нём лежат:

- user — мы только что аутентифицировали пользователя,
- request — данные запроса (IP, путь, заголовки),
- environment — данные окружения сервиса.

Цитата [1]:

```
class Context:
    user: UserInfo
    request: RequestInfo
    environment: EnvironmentInfo
```

Context нужен для двух вещей:

1. **Action получает данные о пользователе (для авторизации)**  
2. Весь pipeline Action становится чистым и без привязки к API, FastAPI, MCP.

---

# 4. Как создаётся Context  
Для этого используется **ContextFactory**.

Цитата [1]:

```
class ContextFactory(ABC):
    def create_context(self, user_info, request_info) -> Context:
```

Текущая реализация — `DefaultContextFactory` [1].

Она:

- создаёт объект RequestInfo,
- заполняет его данными HTTP/MCP запроса,
- формирует EnvironmentInfo,
- и возвращает Context.

---

# 5. Авторизация — кто что может

Авторизация происходит **внутри Action**, перед основной логикой.

За неё отвечает декоратор:

## 5.1 CheckRoles

Цитата [1]:

```
@CheckRoles(CheckRoles.ANY)
```

Декоратор записывает в класс Action требуемые роли:

```
cls._role_spec = spec
```

Примеры:

- `CheckRoles.NONE` — доступ без ролей (гость)
- `CheckRoles.ANY` — любой аутентифицированный
- `CheckRoles(["admin", "manager"])` — только эти роли
- `CheckRoles("admin")` — одна роль

---

## 5.2 Где выполняется авторизация?

Внутри BaseSimpleAction, в первом шаге pipeline:

Цитата [1]:

```
auth_result = self._permissionAuthorizationAspect(ctx, params)
```

Сам аспект вызывает:

```
self._checkRole(ctx)
```

А `_checkRole` сравнивает:

- требуемые роли → `_role_spec`
- фактические роли → `ctx.user.roles`

Если ролей недостаточно — выбрасывается **AuthorizationException**.

---

# 6. Интеграция в FastAPI

Сейчас FastAPI код **вообще не делает аутентификацию** — он просто вызывает фасад:

```
result = YouTrackEntryPoint.bulk_youtrack_issue_to_postgres(...)
```

Это значит:

- авторизация работает (через CheckRoles)  
- аутентификации нет  
- FastAPI всегда вызывает actions от имени технического пользователя `system` [1].

Например в `bulk_youtrack_issue_to_csv` [1]:

```
user_info = UserInfo(user_id="system", roles=["user"])
```

Чтобы включить реальную аутентификацию:

1. Добавить зависимость `get_current_context`  
2. В ней:
   - достать API‑ключ из заголовка,
   - передать в Authenticator,
   - создать Context через ContextFactory,
   - передать Context в действия.

Примерный код такой (его нет в проекте, но он нужен):

```
authenticator = EnvApiKeyAuthenticator()
context_factory = DefaultContextFactory()

def get_current_context(request):
    api_key = request.headers.get("X-API-Key")
    user_info = authenticator.authenticate(api_key)
    if not user_info:
        raise HTTPException(403)
    request_info = {...}
    return context_factory.create_context(user_info, request_info)
```

Тогда endpoint будет выглядеть так:

```
@app.post("/bulk")
def bulk(ctx: Context = Depends(get_current_context)):
    return YouTrackEntryPoint.bulk(..., ctx=ctx)
```

---

# 7. Интеграция в MCP сервер

В MCP сервере логика похожа:  
эти строки вызывают действие:

Цитата [1]:

```
result = Facade.bulk_youtrack_issue_to_postgres(...)
```

Аутентификации нет.

Чтобы добавить:

- MCP API передаёт api_key в аргументах инструмента,
- обработчик должен вызвать Authenticator,
- создать Context,
- вызвать Action через фасад.

Шаблон:

```
api_key = arguments.pop("api_key")
user_info = authenticator.authenticate(api_key)
ctx = context_factory.create_context(user_info, request_info)
result = Facade.bulk(..., ctx=ctx)
```

---

# 8. Добавление нового способа аутентификации

Добавить новый способ — очень просто:

1. Создать класс, наследующий `Authenticator`.
2. Реализовать метод `authenticate(credentials)`.

Например, JWT‑аутентификация:

```
class JwtAuthenticator(Authenticator):
    def authenticate(self, token):
        payload = jwt.decode(token, secret)
        return UserInfo(user_id=..., roles=...)
```

Чтобы активировать:

- заменить EnvApiKeyAuthenticator на JwtAuthenticator,
- или объединить их в CompositeAuthenticator (вариант легко пишется).

---

# 9. Итог: как вся цепочка работает

1. HTTP или MCP получает запрос.
2. API‑ключ → передаём в Authenticator.
3. Authenticator возвращает UserInfo.
4. ContextFactory создаёт Context с данными пользователя и запроса.
5. Action получает Context.
6. BaseSimpleAction.run:
   - проверяет роли (CheckRoles)
   - проверяет параметры (чекеры)
   - выполняет основную логику
   - возвращает результат.

Аутентификация полностью происходит в API‑слое.  
Авторизация — внутри Action.