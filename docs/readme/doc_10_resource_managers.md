10_resource_managers.md

# Ресурсные менеджеры в AOA

Ресурсные менеджеры — это адаптеры к внешним системам. Они инкапсулируют работу с базами данных, HTTP-API, файловыми хранилищами, очередями, внешними сервисами и любыми другими источниками данных. В парадигме AOA они составляют инфраструктурный слой, а Actions — доменный слой. Действия принимают решения, ресурсы обеспечивают доступ к данным.

---

## Что такое ресурсный менеджер

Ресурсный менеджер — это класс который управляет внешним ресурсом, содержит долгоживущее состояние, реализует конкретный адаптер для порта, не содержит бизнес-логики, обеспечивает минимальную трансформацию данных и предоставляет доменное API бизнес-логике.

Его задача — дать Actions возможность работать с внешним миром безопасно, предсказуемо и независимо от деталей реализации.

---

## Долгоживущее состояние

Главный признак ресурса — состояние которое нельзя пересоздавать каждый раз:

Соединение с БД. HTTP-клиент с авторизацией. Файловый дескриптор. Кэш авторизации. Статистика собираемая в памяти. Внутренние сессии или токены.

Такое состояние должно быть инкапсулировано в ресурсный менеджер, а ActionMachine обеспечит его доставку через DI.

---

## Порты — абстрактные интерфейсы

Перед созданием ресурса нужно определить порт — абстрактный интерфейс описывающий какие операции требуются домену.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class Issue:
    id: str
    title: str
    status: str
    assignee: Optional[str] = None

class IssueTracker(ABC):

    @abstractmethod
    def get_issue(self, issue_id: str) -> Issue: ...

    @abstractmethod
    def create_issue(self, title: str, description: str) -> Issue: ...

    @abstractmethod
    def update_status(self, issue_id: str, status: str) -> Issue: ...
```

Порт определяет контракт. Ресурсный менеджер — конкретную реализацию этого контракта. Action работает с портом и никогда не зависит от конкретного адаптера.

---

## Адаптеры

Адаптер — это реализация порта которая использует реальную внешнюю систему, преобразует форматы данных, ловит инфраструктурные исключения и приводит их к единому виду.

```python
import requests
from ActionMachine.Core.Exceptions import HandleException

class YouTrackIssueTracker(IssueTracker):

    def __init__(self, base_url: str, token: str):
        self._base_url = base_url
        self._headers = {"Authorization": f"Bearer {token}"}

    def get_issue(self, issue_id: str) -> Issue:
        try:
            response = requests.get(
                f"{self._base_url}/api/issues/{issue_id}",
                headers=self._headers
            )
            response.raise_for_status()
            data = response.json()
            return self._map_to_issue(data)
        except Exception as e:
            raise HandleException(f"Ошибка получения задачи: {e}") from e

    def create_issue(self, title: str, description: str) -> Issue:
        try:
            response = requests.post(
                f"{self._base_url}/api/issues",
                headers=self._headers,
                json={"summary": title, "description": description}
            )
            response.raise_for_status()
            return self._map_to_issue(response.json())
        except Exception as e:
            raise HandleException(f"Ошибка создания задачи: {e}") from e

    def update_status(self, issue_id: str, status: str) -> Issue:
        try:
            response = requests.post(
                f"{self._base_url}/api/issues/{issue_id}/fields",
                headers=self._headers,
                json={"state": status}
            )
            response.raise_for_status()
            return self._map_to_issue(response.json())
        except Exception as e:
            raise HandleException(f"Ошибка обновления задачи: {e}") from e

    def _map_to_issue(self, data: dict) -> Issue:
        return Issue(
            id=data["id"],
            title=data.get("summary", ""),
            status=data.get("state", {}).get("name", ""),
            assignee=data.get("assignee", {}).get("login")
        )
```

Внутренние модели API не покидают адаптер. Наружу выходит только доменная модель Issue.

---

## Общие доменные модели

Если несколько адаптеров реализуют один порт — они работают с одной и той же доменной моделью. Это обязательное правило.

JiraTracker, YouTrackTracker и GitHubTracker используют одну модель Issue. Внутренние форматы ответов API у каждого разные, но они преобразуются в единую модель внутри адаптера.

Это гарантирует что Action не зависит от конкретного трекера и может работать с любым из них через один и тот же интерфейс.

---

## Базовые классы ресурсов

ActionEngine предоставляет базовые классы для построения ресурсных менеджеров:

BaseResourceManager — маркерный базовый класс. Содержит абстрактный метод get_wrapper_class() который должен вернуть класс прокси-обёртки для передачи в дочерние действия.

BaseConnectionManager — базовый класс для менеджеров соединений. Определяет контракт жизненного цикла соединения: open, commit, rollback, execute.

```python
from ActionMachine.ResourceManagers.BaseResourceManager import BaseResourceManager

class IssueTrackerBase(BaseResourceManager):

    def get_wrapper_class(self):
        return None  # трекер не передаётся в дочерние действия с транзакциями
```

---

## Структура проекта для ресурсов

Рекомендуемая структура папок:

```
resource_managers/
│
├── issue_trackers/
│   ├── interface.py          — порт IssueTracker
│   ├── models.py             — общие доменные модели
│   ├── youtrack/
│   │   ├── client.py         — HTTP-клиент
│   │   ├── models.py         — внутренние модели API
│   │   └── adapter.py        — адаптер
│   ├── jira/
│   │   └── adapter.py
│   └── github/
│       └── adapter.py
│
├── payment_gateways/
│   ├── interface.py
│   ├── models.py
│   ├── stripe/
│   └── paypal/
│
└── db/
    ├── postgres/
    └── mysql/
```

Каждый домен имеет порт, доменные модели и адаптеры. Адаптеры не знают друг о друге.

---

## Как Actions используют ресурсы

Через декларацию @depends:

```python
from ActionMachine.Core.AspectMethod import depends, summary_aspect
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Auth.CheckRoles import CheckRoles

@depends(IssueTracker)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному")
class CreateIssueAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        title: str
        description: str

    @dataclass(frozen=True)
    class Result(BaseResult):
        issue_id: str
        issue_url: str

    @summary_aspect("Создание задачи")
    async def handle(self, params, state, deps):
        tracker = deps.get(IssueTracker)
        issue = tracker.create_issue(params.title, params.description)
        return CreateIssueAction.Result(
            issue_id=issue.id,
            issue_url=f"https://tracker/issue/{issue.id}"
        )
```

Action работает с портом IssueTracker и не знает используется ли YouTrack, Jira или GitHub. Конкретный адаптер подставляется через DI.

---

## Обработка ошибок в ресурсах

Ресурсный менеджер должен ловить все инфраструктурные исключения и оборачивать их в HandleException:

```python
from ActionMachine.Core.Exceptions import HandleException

def create_issue(self, title: str, description: str) -> Issue:
    try:
        response = self._client.post("/issues", json={...})
        response.raise_for_status()
        return self._map(response.json())
    except ConnectionError as e:
        raise HandleException(f"Сервис недоступен: {e}") from e
    except TimeoutError as e:
        raise HandleException(f"Таймаут запроса: {e}") from e
    except Exception as e:
        raise HandleException(f"Неожиданная ошибка: {e}") from e
```

Action не должен знать про ConnectionError, TimeoutError и другие инфраструктурные исключения. Он работает только с HandleException или доменными исключениями.

---

## Когда ресурс — правильный выбор

Выбирай ресурсный менеджер если:

Класс содержит долгоживущее состояние — соединение, сессию, кэш. Состояние нельзя безопасно пересоздавать при каждом вызове. Логика транспортная — выполнить SQL, вызвать API, записать в файл. Внутри нет бизнес-правил, только маппинг данных и транспорт.

---

## Когда ресурс — неправильный выбор

Не делай ресурс если:

Класс создаётся каждый раз заново. Не хранит состояния между вызовами. Выполняет бизнес-логику — рассчитывает, принимает решения, валидирует. Логика зависит только от входных данных а не от внешних систем.

В этом случае это Action, а не Resource.

---

## Тестирование ресурсов

В тестах ресурс подменяется через ActionTestMachine:

```python
class FakeIssueTracker(IssueTracker):

    def __init__(self):
        self.created_issues = []

    def get_issue(self, issue_id: str) -> Issue:
        return Issue(id=issue_id, title="Test", status="open")

    def create_issue(self, title: str, description: str) -> Issue:
        issue = Issue(id="TEST-1", title=title, status="open")
        self.created_issues.append(issue)
        return issue

    def update_status(self, issue_id: str, status: str) -> Issue:
        return Issue(id=issue_id, title="Test", status=status)


def test_create_issue():
    fake_tracker = FakeIssueTracker()
    machine = ActionTestMachine({IssueTracker: fake_tracker})
    result = machine.run(
        CreateIssueAction(),
        CreateIssueAction.Params(title="Bug", description="Something broken")
    )
    assert result.issue_id == "TEST-1"
    assert len(fake_tracker.created_issues) == 1
```

Тест не требует реального трекера. Fake-объект реализует тот же порт и контролирует поведение.

---

## Легаси-монстр как ресурс

Если в проекте есть тяжёлый класс с внутренним состоянием — первый шаг миграции это упаковать его в адаптер:

```python
class LegacyPaymentSystem:
    # огромный класс, синглтон, хранит состояние
    ...

class LegacyPaymentAdapter(PaymentGateway):

    def __init__(self):
        self._legacy = LegacyPaymentSystem()

    def validate_card(self, token: str, amount: float) -> bool:
        return self._legacy._validate_card(token, amount)

    def charge(self, token: str, amount: float) -> str:
        return self._legacy._charge(token, amount)
```

Теперь монстр спрятан за интерфейсом. Action работает с портом PaymentGateway и не знает о существовании легаси.

---

## Что изучать дальше

11_action_vs_resource.md — детальный алгоритм выбора между action и resource.

12_create_resource_manager.md — пошаговое создание своего менеджера ресурсов.

13_errors_in_resources.md — обработка ошибок в ресурсах.

14_machine.md — как ActionMachine работает с зависимостями.

15_di.md — декларативное внедрение зависимостей.

16_transactions.md — управление транзакциями через connections.

19_testing.md — тестирование Actions с фейковыми ресурсами.

26_migrating_legacy.md — пошаговая миграция легаси-монстров.
