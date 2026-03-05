# README.md — YouTrack Kanban Assistant

---

## 📋 Описание проекта

**YouTrack Kanban Assistant** — фреймворк для автоматизированного сбора, обработки и хранения ежедневных снимков задач из системы управления проектами **YouTrack**.

Проект реализует паттерн **Action Pipeline** (конвейер аспектов) с встроенной валидацией, авторизацией, управлением транзакциями и поддержкой нескольких форматов хранения данных (PostgreSQL, CSV).

Основной сценарий использования — ежедневное снятие снимков состояния задач (историй и задач разработки) и их сохранение в хранилище для последующего анализа динамики Kanban-доски.

---

## 🏗️ Архитектура

```
kanban_assistant/
├── ActionEngine/          # Ядро фреймворка (actions, checkers, connections)
├── App/                   # Прикладные действия (парсинг, сохранение)
├── MCPServer/             # Серверный слой — оркестрация и фасад
└── Utils/                 # Утилиты и тестовые скрипты
```

### Слои архитектуры

```
[Внешняя система / n8n]
        │
        ▼
[MCPServer / YouTrackMCPServer]   ← тонкий фасад, читает ENV-переменные
        │
        ▼
[Оркестрирующие Action'ы]         ← BulkYouTrackIssueTo*, DeleteSnapshot*, InitDatabase*
        │
        ▼
[App Actions / Savers / Parser]   ← FetchIssues, Parser, PostgresSaver, CSVSaver
        │
        ▼
[ActionEngine Core]               ← BaseSimpleAction, BaseTransactionAction, Checkers, ConnectionManagers
```

---

## ⚙️ ActionEngine — ядро фреймворка

### Конвейер аспектов

Каждое действие реализует конвейер из 5 аспектов, выполняемых строго последовательно:

| # | Аспект | Описание |
|---|--------|----------|
| 1 | `_permissionAuthorizationAspect` | Проверка ролей пользователя |
| 2 | `_validationAspect` | Валидация входных параметров |
| 3 | `_preHandleAspect` | Подготовка данных (открытие соединений и т.д.) |
| 4 | `_handleAspect` | Основная бизнес-логика (**обязателен к переопределению**) |
| 5 | `_postHandleAspect` | Постобработка (фиксация транзакций, очистка) |

При исключении на любом этапе вызывается `_onErrorAspect` (откат транзакций).

После каждого аспекта автоматически применяются **чекеры результата** (`_result_checkers`), навешенные через декораторы.

### Базовые классы действий

| Класс | Описание |
|-------|----------|
| `BaseSimpleAction` | Stateless-действие без транзакции |
| `BaseTransactionAction` | Действие, требующее открытого соединения в `TransactionContext` |

### Контексты выполнения

```python
# Базовый контекст (пользователь + роли)
ctx = Context(user_id="user_1", roles=["admin"])

# Транзакционный контекст (+ открытое соединение)
tx_ctx = TransactionContext(base_ctx=ctx, connection=conn)
```

### Система валидации (Field Checkers)

Чекеры вешаются как **декораторы на классы** (валидация входных параметров) или **на методы** (валидация результата):

```python
@StringFieldChecker("snapshot_date", required=True, not_empty=True)
@IntFieldChecker("page_size", min_value=1, max_value=500)
@InstanceOfChecker("rows", expected_class=list, required=True)
class MyAction(BaseSimpleAction):

    @IntFieldChecker("inserted", min_value=0)   # ← проверка результата метода
    def _handleAspect(self, ctx, params, result):
        ...
```

| Чекер | Что проверяет |
|-------|---------------|
| `StringFieldChecker` | Тип `str`, длина, не пустая строка |
| `IntFieldChecker` | Тип `int`, диапазон значений |
| `FloatFieldChecker` | Тип `int/float`, диапазон значений |
| `BoolFieldChecker` | Тип `bool` |
| `DateFieldChecker` | `datetime` или строка в заданном формате, диапазон дат |
| `InstanceOfChecker` | Проверка `isinstance` для произвольного класса |

### Управление соединениями

```python
# Базовый абстрактный класс
BaseConnectionManager
    ├── PostgresConnectionManager   # psycopg2, ручное управление транзакцией
    └── CsvConnectionManager        # Запись в CSV-файл
```

Жизненный цикл соединения:
```python
mgr = PostgresConnectionManager(db_params)
mgr.open()       # открыть соединение / начать транзакцию
# ... выполнение действий ...
mgr.commit()     # зафиксировать
# или
mgr.rollback()   # откатить при ошибке
```

### Авторизация по ролям

```python
@CheckRoles(CheckRoles.NONE)          # Без ролей (гость)
@CheckRoles(CheckRoles.ANY)           # Любая роль (аутентифицированный)
@CheckRoles(["admin", "manager"])     # Одна из перечисленных ролей
@CheckRoles("admin")                  # Конкретная роль
```

### Декоратор типа соединения

```python
@requires_connection_type(psycopg2.extensions.connection)
class MyTransactionAction(BaseTransactionAction):
    ...
```

---

## 🗄️ Структура базы данных

Схема: `youtrack`

### Таблица `user_tech_stories`

Хранит снимки **пользовательских и технических историй**.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `key` | TEXT | Идентификатор задачи (PK) |
| `snapshot_date` | DATE | Дата снимка (PK) |
| `title` | TEXT | Заголовок |
| `description` | TEXT | Описание |
| `created` / `updated` | TIMESTAMP | Даты создания/обновления |
| `date_resolved` | TIMESTAMP | Дата закрытия |
| `parent_key` | TEXT | Родительская задача |
| `assignee_*` | TEXT | Исполнитель (логин, имя, полное имя) |
| `type` / `status` | TEXT | Тип и статус карточки |
| `plan_start` / `plan_finish` | DATE | Плановые даты |
| `fact_forecast_start` / `fact_forecast_finish` | DATE | Прогнозные даты |
| `customer` | TEXT | Приёмщик |
| `sprints` | TEXT | Связанные спринты |
| `imported_at` | TIMESTAMP | Дата импорта |

### Таблица `taskitems`

Хранит снимки **задач разработки** (разработка, аналитика, инциденты, работа вместо системы).

Аналогична `user_tech_stories`, дополнительно содержит:

| Колонка | Тип | Описание |
|---------|-----|----------|
| `tester_*` | TEXT | Тестировщик (логин, имя, полное имя) |
| `story_points` | NUMERIC | Story Points |
| `priority` | TEXT | Приоритет |
| `subcomponent` | TEXT | Подкомпонент |

Обе таблицы имеют **составной первичный ключ** `(key, snapshot_date)` и индекс по `snapshot_date`.

---

## 🔄 Основные сценарии использования

### 1. Инициализация базы данных

```python
from MCPServer import YouTrackMCPServer

result = YouTrackMCPServer.init_database()
# {"success": True, "result": {"schema": "youtrack", "tables_created": [...]}, "errors": []}
```

### 2. Загрузка задач из YouTrack в PostgreSQL

```python
from datetime import date

result = YouTrackMCPServer.bulk_youtrack_issue_to_postgres(
    project_id="MY_PROJECT",
    page_size=100,
    snapshot_date=date.today()
)
```

**Что происходит внутри:**
1. Открывается соединение с PostgreSQL
2. Удаляются существующие записи за указанную дату
3. Постранично загружаются задачи из YouTrack API
4. Парсятся и разделяются по типам карточек
5. Истории сохраняются в `user_tech_stories`, задачи — в `taskitems`
6. Транзакция фиксируется; при ошибке — откатывается

### 3. Загрузка задач из YouTrack в CSV

```python
result = YouTrackMCPServer.bulk_youtrack_issue_to_csv(
    user_stories_file="/data/stories.csv",
    tasks_file="/data/tasks.csv",
    page_size=100,
    project_id="MY_PROJECT"
)
```

### 4. Удаление снимка за дату

```python
result = YouTrackMCPServer.delete_snapshot(
    snapshot_date=date.today(),
    tables=["user_tech_stories", "taskitems"],
    schema="youtrack"
)
```

---

## 🧩 Типы карточек YouTrack

| Группа | Типы | Таблица |
|--------|------|---------|
| Истории | `Пользовательская история`, `Техническая история` | `user_tech_stories` |
| Задачи | `Разработка`, `Аналитика и проектирование`, `Решение инцидентов`, `Работа вместо системы` | `taskitems` |

---

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- PostgreSQL 13+
- Доступ к YouTrack API

### Установка зависимостей

```bash
pip install psycopg2-binary requests python-dotenv
```

### Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# YouTrack
YOUTRACK_URL=https://your-instance.youtrack.cloud
YOUTRACK_TOKEN=perm:your-token-here

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=kanban
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### Инициализация и первый запуск

```bash
# Инициализация таблиц БД
python Utils/test_init_db.py

# Загрузка снимка в PostgreSQL
python Utils/test_youtrack_issue_to_postgres.py

# Загрузка в CSV
python Utils/test_youtrack_issue_to_csv.py

# Удаление снимка
python Utils/test_delete_snapshot.py
```

---

## 📁 Описание модулей

### `ActionEngine/`

| Файл | Описание |
|------|----------|
| `BaseSimpleAction.py` | Базовый класс для stateless-действий |
| `BaseTransactionAction.py` | Базовый класс для транзакционных действий |
| `BaseConnectionManager.py` | Абстрактный менеджер соединений |
| `PostgresConnectionManager.py` | Менеджер соединений PostgreSQL |
| `CsvConnectionManager.py` | Менеджер соединений CSV |
| `BaseFieldChecker.py` | Абстрактный базовый класс чекеров |
| `StringFieldChecker.py` | Чекер строковых полей |
| `IntFieldChecker.py` | Чекер целочисленных полей |
| `FloatFieldChecker.py` | Чекер числовых полей с плавающей точкой |
| `BoolFieldChecker.py` | Чекер булевых полей |
| `DateFieldChecker.py` | Чекер полей даты/времени |
| `InstanceOfChecker.py` | Чекер типа экземпляра |
| `Context.py` | Контекст выполнения запроса |
| `TransactionContext.py` | Транзакционный контекст |
| `CheckRoles.py` | Декоратор проверки ролей |
| `requires_connection_type.py` | Декоратор типа соединения |
| `Exceptions.py` | Иерархия исключений |

### `App/`

| Файл | Описание |
|------|----------|
| `FetchIssuesFromYouTrackAction.py` | Постраничная загрузка задач из YouTrack API |
| `YouTrackIssuesParser.py` | Парсинг и группировка задач по типам |
| `YouTrackStoriyIssuesPostgresSaver.py` | Сохранение историй в PostgreSQL |
| `YouTrackTasksIssuesPostgresSaver.py` | Сохранение задач в PostgreSQL |
| `YouTrackIssuesCSVSaver.py` | Сохранение задач в CSV |
| `InitDatabaseAction.py` | Создание схемы и таблиц |
| `DeleteSnapshotPostgressAction.py` | Удаление записей за дату |
| `IYouTrackIssuesSaver.py` | Маркерный интерфейс сохранятелей |

### `MCPServer/`

| Файл | Описание |
|------|----------|
| `YouTrackMCPServer.py` | Главный фасад — точка входа для внешних систем |
| `BulkYouTrackIssueToPostgresAction.py` | Оркестрация загрузки в PostgreSQL |
| `BulkYouTrackIssueToCsvAction.py` | Оркестрация загрузки в CSV |
| `InitDatabaseServerAction.py` | Серверное действие инициализации БД |
| `DeleteSnapshotServerAction.py` | Серверное действие удаления снимка |

---

## 🔒 Исключения

| Исключение | Описание |
|-----------|----------|
| `AuthorizationException` | Недостаточно прав доступа |
| `ValidationFieldException` | Ошибка валидации входного параметра |
| `HandleException` | Ошибка бизнес-логики |
| `ConnectionAlreadyOpenError` | Попытка повторно открыть соединение |
| `ConnectionNotOpenError` | Операция без открытого соединения |
| `TransactionException` | Базовое исключение транзакций |

---

## 🔧 Расширение системы

### Добавить новый тип сохранятеля

```python
from ActionEngine.BaseTransactionAction import BaseTransactionAction
from App.IYouTrackIssuesSaver import IYouTrackIssuesSaver

class MyCustomSaver(BaseTransactionAction, IYouTrackIssuesSaver):
    def _handleAspect(self, ctx, params, result):
        # Ваша логика сохранения
        ...
        return {"inserted": len(params["rows"])}
```

### Добавить новый чекер поля

```python
from ActionEngine.BaseFieldChecker import BaseFieldChecker
from ActionEngine.Exceptions import ValidationFieldException

class EmailFieldChecker(BaseFieldChecker):
    def _check_type_and_constraints(self, value):
        if not isinstance(value, str) or "@" not in value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть корректным email"
            )
```

---

## 📄 Лицензия

MIT License

---

> Проект разработан для интеграции с n8n и внешними системами автоматизации через тонкий фасад `YouTrackMCPServer`.