```markdown
# Kanban Assistant

Kanban Assistant — это фреймворк для создания бизнес-действий (сообщений) с декларативной валидацией, проверкой прав и поддержкой транзакций. В качестве примера реализован модуль для работы с YouTrack: выгрузка задач в CSV. Вся логика упакована в Docker-образ, автоматически собирается через CI/CD и может вызываться из n8n.

---

## 📁 Структура проекта

```
kanban_assistant/
├── ActionEngine/                # Ядро фреймворка
│   ├── BaseConnectionManager.py      # Абстрактный менеджер соединений (open/commit/rollback)
│   ├── BaseFieldChecker.py           # Базовый чекер для полей (работает и на класс, и на метод)
│   ├── BaseSimpleAction.py           # Базовое действие без транзакции (stateless, 5 аспектов)
│   ├── BaseTransactionAction.py       # Базовое действие, выполняемое внутри открытой транзакции
│   ├── BoolFieldChecker.py            # Чекер булевых значений
│   ├── CheckRoles.py                  # Декоратор для указания ролей
│   ├── Context.py                     # Контекст выполнения (пользователь, роли)
│   ├── CsvConnectionManager.py         # Конкретный менеджер соединения для CSV-файлов
│   ├── DateFieldChecker.py             # Чекер дат
│   ├── Exceptions.py                   # Доменные исключения (все сообщения на русском)
│   ├── FloatFieldChecker.py            # Чекер чисел с плавающей точкой
│   ├── InstanceOfChecker.py             # Чекер для проверки, что значение является экземпляром указанного класса
│   ├── IntFieldChecker.py               # Чекер целых чисел
│   ├── StringFieldChecker.py            # Чекер строк
│   ├── TransactionContext.py            # Расширенный контекст с соединением
│   ├── requires_connection_type.py      # Декоратор для указания требуемого типа соединения
│   └── __init__.py                      # Экспорт основных классов
│
├── YouTrackMCP/                   # Реализация для YouTrack
│   ├── BaseYouTrackIssuesSaver.py      # Базовый класс для сохранятелей с двумя стратегиями
│   ├── FetchIssuesFromYouTrackAction.py # Загрузчик задач по страницам
│   ├── YouTrackIssuesCSVSaver.py       # Сохранятель в CSV (наследник BaseYouTrackIssuesSaver)
│   ├── YouTrackMCPServer.py            # Фасад для внешних вызовов
│   └── __init__.py                      # Экспорт фасада
│
├── Utils/                         # Вспомогательные скрипты
│   ├── test.py                    # Тест выгрузки с фильтрацией по типам
│   └── terst2.py                  # Скрипт для отладки одной задачи с полным JSON
│
├── Dockerfile                      # Сборка образа
├── requirements.txt                # Зависимости (requests, pandas)
├── .gitignore                      # Игнорируемые файлы (venv, __pycache__, .env)
├── .env.example                     # Пример переменных окружения
└── README.md                       # Этот файл
```

---

## 🧠 Архитектура (ActionEngine)

### Базовые классы

- **`BaseSimpleAction`** – действие без управления транзакцией. Реализует конвейер из пяти аспектов, вызываемых в строгом порядке:
  1. `_permissionAuthorizationAspect` – проверка прав (ролей).
  2. `_validationAspect` – валидация входных параметров.
  3. `_preHandleAspect` – предварительная обработка (подготовка данных).
  4. `_handleAspect` – основная бизнес-логика (обязателен к переопределению).
  5. `_postHandleAspect` – пост-обработка (логирование, уведомления).

  Каждый аспект принимает текущий результат (словарь) и возвращает (возможно, модифицированный) словарь. После выполнения каждого аспекта применяются чекеры результата, привязанные к методу.

- **`BaseTransactionAction`** – действие, выполняемое внутри открытой транзакции. Ожидает, что переданный контекст является `TransactionContext` и содержит поле `connection`. Проверяет тип соединения (если задан декоратор `@requires_connection_type`) и делегирует выполнение родительскому `run()`.

- **`BaseConnectionManager`** – абстрактный менеджер соединений/транзакций. Предоставляет методы `open()`, `commit()`, `rollback()` и свойство `connection`. Конкретные наследники (например, `CsvConnectionManager`) реализуют логику для конкретного типа ресурса.

### Декларативная валидация (чекеры)

Классы-наследники `BaseFieldChecker` (например, `StringFieldChecker`, `IntFieldChecker`) могут применяться как декораторы:

- **На класс** – добавляют проверку входных параметров. Чекеры накапливаются в атрибуте класса `_field_checkers` и проверяются в аспекте `_validationAspect`.
- **На метод аспекта** – добавляют проверку результата, возвращаемого этим аспектом. Чекеры накапливаются в атрибуте метода `_result_checkers` и применяются после выполнения аспекта.

Пример:
```python
@StringFieldChecker("base_url")
@StringFieldChecker("token")
class FetchIssuesFromYouTrackAction(BaseSimpleAction):
    @IntFieldChecker("total_issues", min_value=0)
    def _handleAspect(self, ctx, params, result):
        ...
        return {"total_issues": total}
```

### Проверка ролей

Декоратор `CheckRoles` задаёт требования к ролям пользователя:
- `CheckRoles.NONE` – доступ без роли (гость).
- `CheckRoles.ANY` – требуется любая роль (аутентифицированный).
- `CheckRoles(["admin", "manager"])` – список допустимых ролей.

### Контекст выполнения

- **`Context`** – содержит `user_id` и `roles`.
- **`TransactionContext`** – расширенный контекст, добавляет поле `connection`. Конструктор копирует все поля из базового контекста и добавляет соединение.

### Обработка ошибок

Все бизнес-исключения наследуются от `Exception` и имеют русскоязычные сообщения. Основные:
- `AuthorizationException`
- `ValidationFieldException`
- `HandleException`
- `TransactionException` (базовое для ошибок транзакций)
  - `ConnectionAlreadyOpenError`
  - `ConnectionNotOpenError`

Исключения не перехватываются внутри действия – они всплывают наружу, где фасад преобразует их в единый формат ответа.

---

## 🚀 Реализация для YouTrack (YouTrackMCP)

### Основные классы

- **`BaseYouTrackIssuesSaver`** – абстрактный класс, наследующий `BaseTransactionAction`. Содержит методы для чтения полей задачи (`_get_field`, `_get_custom_field_display`, `_get_user_field`, `_get_sprint_field`) и две стратегии извлечения данных:
  - `_user_story_strategy` – для пользовательских и технических историй.
  - `_task_item_strategy` – для задач (разработка, аналитика, решение инцидентов, работа вместо системы).

  В `_preHandleAspect` происходит фильтрация входящих задач по типу карточки (через `_get_custom_field_display(issue, "_Тип карточки")`), вызов соответствующей стратегии и подготовка списка плоских строк для записи.

- **`YouTrackIssuesCSVSaver`** – конкретный сохранятель, наследующий `BaseYouTrackIssuesSaver`. В конструкторе принимает список стратегий (`strategy`), которые будут обрабатываться. Реализует `_handleAspect`, который записывает подготовленные строки в CSV через соединение из контекста (должно быть `CsvConnectionManager`).

- **`FetchIssuesFromYouTrackAction`** – загрузчик задач по страницам. На вход принимает список кортежей `(context, saver)`, где каждый `saver` – экземпляр `YouTrackIssuesCSVSaver`. Для каждой страницы задач создаёт подпараметры `{"issues": page_issues, "first_page": ...}` и вызывает `saver.run(context, sub_params)` для каждого элемента списка.

- **`YouTrackMCPServer`** – фасад для внешних вызовов. Предоставляет статический метод `bulk_youtrack_issue_to_csv`, который:
  - читает `YOUTRACK_URL` и `YOUTRACK_TOKEN` из переменных окружения;
  - создаёт менеджеры соединений (`CsvConnectionManager`) для каждого указанного файла;
  - создаёт транзакционные контексты и соответствующие saver’ы с нужными стратегиями;
  - передаёт список saver’ов в `FetchIssuesFromYouTrackAction` и запускает его;
  - фиксирует или откатывает транзакции и возвращает стандартный словарь `{"success": bool, "result": Any, "errors": List[str]}`.

### Логика фильтрации и сохранения

В `BaseYouTrackIssuesSaver._preHandleAspect`:
- Из каждой задачи извлекается тип карточки (поле `_Тип карточки`).
- Если тип входит в `self.get_strategy()`, вызывается соответствующая стратегия.
- Стратегия возвращает плоский словарь с колонками (например, `id`, `summary`, `Логин исполнителя`, `_Тип карточки`, `Единый спринт` и т.д.).
- Все строки собираются, формируются общий набор заголовков и список строк.
- Результат возвращается в виде `{"headers": headers, "rows": rows}` для передачи в `_handleAspect`.

В `YouTrackIssuesCSVSaver._handleAspect` полученные `headers` и `rows` записываются в CSV через `ctx.connection.write_rows`.

### Получение родительской задачи

Для получения родителя (например, `OPD_IPPM-771` для задачи `OPD_IPPM-1012`) в `FetchIssuesFromYouTrackAction._fetch_page` добавлено поле `links(direction,linkType(name),issues(idReadable,summary))`. В `BaseYouTrackIssuesSaver._get_parent_id` происходит поиск связи с типом `Subtask` и направлением `INWARD`, откуда извлекается `idReadable` первой задачи.

---

## 🔧 Установка и запуск

1. **Клонируйте репозиторий**:
   ```bash
   git clone <url>
   cd kanban_assistant
   ```

2. **Создайте и активируйте виртуальное окружение**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Создайте файл `.env`** на основе `.env.example`:
   ```
   YOUTRACK_URL=https://youtrack.brusnika.tech
   YOUTRACK_TOKEN=ваш_перманентный_токен
   ```

5. **Запустите тестовый скрипт**:
   ```bash
   python Utils/test.py
   ```
   Он выгрузит пользовательские истории в `/tmp/user_stories.csv` и задачи в `/tmp/tasks.csv`.

---

## 🐳 Docker и CI/CD

- **`Dockerfile`** собирает образ на базе `python:3.12-slim`, копирует исходный код и устанавливает зависимости.
- **CI/CD** (например, в GitVerse) при пуше в ветку `master` собирает образ и публикует его в реестре.
- **Локальный запуск через Docker Compose** (опционально) может поднимать n8n, туннель cloudpub и контейнер с Python-кодом.

---

## 📌 Пример использования в n8n

После сборки и запуска контейнера с образом можно вызывать фасад через `docker exec`:

```bash
docker exec python-runner python -c "
from YouTrackMCP import YouTrackMCPServer
result = YouTrackMCPServer.bulk_youtrack_issue_to_csv(
    user_stories_file='/tmp/user_stories.csv',
    tasks_file='/tmp/tasks.csv',
    page_size=100,
    project_id='OPD_IPPM'
)
print(result)
"
```

Фасад вернёт JSON вида:
```json
{
  "success": true,
  "result": {"total_issues": 772, "pages": 8},
  "errors": []
}
```

---

## 🧩 Заключение

Проект предоставляет гибкую и расширяемую архитектуру для создания бизнес-действий с единообразным интерфейсом. Основные преимущества:

- ✅ Декларативная валидация – требования к параметрам видны прямо у класса/метода.
- ✅ Stateless-действия – результат передаётся по цепочке аспектов, что упрощает тестирование.
- ✅ Поддержка транзакций – чёткое разделение управления соединением и бизнес-логики.
- ✅ Единый фасад – внешние системы получают стандартизированный JSON-ответ.
- ✅ Русскоязычные ошибки – все сообщения об исключениях на русском для удобства команды.

Новые действия добавляются просто: создаётся класс в `YouTrackMCP/`, описываются чекеры и роли, реализуется `_handleAspect`, и в фасад добавляется соответствующий статический метод. Вся инфраструктура (сборка образа, CI/CD, запуск в Docker) уже готова.
```