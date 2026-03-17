20_auth_architecture.md

# Архитектура аутентификации и сборки Context

Подсистема аутентификации в ActionEngine спроектирована как независимый слой который формирует полный Context до начала выполнения любого действия. Actions не занимаются аутентификацией — они всегда получают готовый, проверенный и структурированный контекст. Это заложено в архитектуру через явное разделение компонентов: CredentialExtractor, Authenticator, ContextAssembler и AuthCoordinator [1].

---

## Цели архитектуры

Подсистема аутентификации решает четыре задачи.

Первая — извлечь данные об учётных данных из произвольного объекта запроса.

Вторая — проверить подлинность пользователя и определить его роли.

Третья — собрать полные метаданные запроса и окружения.

Четвёртая — создать Context который будет передан ActionMachine.

Таким образом Actions остаются чистыми и независимыми от способов аутентификации и транспорта [1].

---

## Основные компоненты

### CredentialExtractor — извлечение учётных данных

CredentialExtractor принимает произвольный объект запроса, извлекает из него данные аутентификации и нормализует их в единый словарь:

```python
class CredentialExtractor(ABC):

    @abstractmethod
    def extract(self, request_data: Any) -> Dict[str, Any]:
        """Возвращает словарь с учётными данными или пустой словарь."""
```

Реализация полностью протокол-агностична. Extractor может работать с HTTP-объектом, CLI-вызовом, MCP-сообщением или любым другим источником [1].

---

### Authenticator — проверка личности

Authenticator принимает учётные данные от Extractor, проверяет их и создаёт объект UserInfo:

```python
class Authenticator(ABC):

    @abstractmethod
    def authenticate(self, credentials: Any) -> Optional[UserInfo]:
        """Возвращает UserInfo или None если аутентификация не прошла."""
```

Можно реализовать любой метод аутентификации — API keys, JWT, OAuth2, LDAP. Можно комбинировать несколько реализаций.

UserInfo содержит:

```python
@dataclass
class UserInfo:
    user_id: Optional[str]
    roles: List[str]
    extra: Dict[str, Any]
```

---

### ContextAssembler — сборка метаданных запроса

ContextAssembler получает сырой объект запроса, вытаскивает полезные метаданные и возвращает словарь для создания RequestInfo:

```python
class ContextAssembler(ABC):

    @abstractmethod
    def assemble(self, request_data: Any) -> Dict[str, Any]:
        """Извлекает метаданные запроса."""
```

Assembler полностью независим от протокола. Он может работать с HTTP-объектом, CLI-данными или MCP-payload [1].

---

### AuthCoordinator — ядро аутентификации

AuthCoordinator — это оркестратор трёх стратегий. Он последовательно вызывает Extractor, Authenticator и Assembler и формирует полный Context:

```python
class AuthCoordinator:

    def __init__(self, extractor, authenticator, assembler):
        self.extractor = extractor
        self.authenticator = authenticator
        self.assembler = assembler

    def process(self, request_data) -> Optional[Context]:
        credentials = self.extractor.extract(request_data)
        if not credentials:
            return None

        user_info = self.authenticator.authenticate(credentials)
        if not user_info:
            return None

        metadata = self.assembler.assemble(request_data)
        req_info = RequestInfo(**metadata)
        return Context(user=user_info, request=req_info, environment=None)
```

Если что-то пошло не так — нет credentials или invalid credentials — возвращается None [1].

---

## Context — единый объект окружения

Context состоит из трёх частей.

### UserInfo — данные пользователя

```python
@dataclass
class UserInfo:
    user_id: Optional[str]
    roles: List[str]
    extra: Dict[str, Any]
```

Используется для ролевой модели, плагинов, метрик и аудита.

### RequestInfo — данные запроса

```python
@dataclass
class RequestInfo:
    trace_id: Optional[str]
    timestamp: Optional[str]
    path: Optional[str]
    method: Optional[str]
    full_url: Optional[str]
    client_ip: Optional[str]
    protocol: Optional[str]
    user_agent: Optional[str]
    extra: Dict[str, Any]
    tags: Dict[str, str]
```

### EnvironmentInfo — данные среды выполнения

```python
@dataclass
class EnvironmentInfo:
    hostname: Optional[str]
    service_name: Optional[str]
    service_version: Optional[str]
    environment: Optional[str]
    container_id: Optional[str]
    pod_name: Optional[str]
    extra: Dict[str, Any]
```

EnvironmentInfo обычно создаётся один раз при старте приложения и затем передаётся в каждый Context.

---

## Context не виден Actions

ActionMachine передаёт Context только в механизм проверки ролей и в плагины. Actions физически не имеют доступа к Context [1].

Это специальное архитектурное решение которое:

Оставляет Actions чистыми и независимыми от транспорта. Исключает расслоение логики на основе данных запроса. Предотвращает превращение Context в God-object.

---

## Принцип чистого входа

Действие получает только Params и deps. Всё остальное уже обработано до его запуска.

Полный поток:

Первый шаг — Entry point принимает запрос через HTTP, MCP или CLI.

Второй шаг — AuthCoordinator.process формирует Context.

Третий шаг — ActionMachine.run получает Action и Params.

Четвёртый шаг — Плагины получают Context и все события.

Пятый шаг — Action выполняет только чистую бизнес-логику.

---

## Как использовать без привязки к транспорту

Архитектура полностью протокол-независима. Для любого входящего запроса достаточно создать свои реализации трёх компонентов:

```python
coordinator = AuthCoordinator(
    extractor=MyCLICredentialExtractor(),
    authenticator=MyFileAuthenticator(),
    assembler=MyCLIAssembler(),
)

context = coordinator.process(request_obj)

if context is None:
    print("Аутентификация не прошла")
else:
    machine = ActionProductMachine(context)
    result = await machine.run(MyAction(), MyParams(...))
```

Этот механизм работает для HTTP-сервисов, TCP-протоколов, RPC-вызовов, cron-job событий и сообщений очередей одинаково [1].

---

## Преимущества подхода

Унифицированная аутентификация — разные интерфейсы используют одну систему auth.

Интерфейс-агностичность — Extractor и Assembler работают с чем угодно.

Чистые Actions — никогда не содержат auth-кода.

Богатый Context — в едином объекте объединены данные пользователя, запроса и окружения.

Максимум информации для плагинов — они могут логировать, анализировать, строить трассировки и аудит.

---

## Что изучать дальше

21_fastapi_integration.md — интеграция с FastAPI.

22_mcp_integration.md — интеграция с MCP для LLM-агентов.

14_machine.md — жизненный цикл ActionMachine и проверка ролей.

18_plugins.md — как плагины используют Context.

06_guarantees.md — формальные гарантии архитектуры.
