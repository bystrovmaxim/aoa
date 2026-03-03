# kanban_assistant

Асистент, который собирает данные из трекинговых систем и отвечает по ним на вопросы по метрикам канбан

kanban_assistant/                # Корень проекта
├── ActionEngine/                # Базовый движок действий
│   ├── BaseSimpleAction.py      # Базовый класс действия с аспектами
│   ├── BaseFieldChecker.py      # Абстрактный чекер полей
│   ├── StringFieldChecker.py    # Чекер строк
│   ├── IntFieldChecker.py       # Чекер целых чисел
│   ├── FloatFieldChecker.py     # Чекер чисел с плавающей точкой
│   ├── BoolFieldChecker.py      # Чекер булевых значений
│   ├── DateFieldChecker.py      # Чекер дат
│   ├── CheckRoles.py            # Декоратор для проверки ролей
│   ├── Context.py               # Контекст выполнения (пользователь, роли)
│   ├── Exceptions.py            # Исключения (авторизация, валидация, обработка)
│   └── __init__.py              # Экспорт основных классов
│
├── YouTrackMCP/                  # Действия для YouTrack
│   ├── FetchIssuesToCsvAction.py # Конкретное действие
│   ├── YouTrackMCPServer.py      # Фасад для вызова действий (статический интерфейс)
│   └── __init__.py               # Экспорт фасада
│
├── Utils/                         # Вспомогательные скрипты
│   ├── TestFetchUserStoriesAction.py   # Тест действия
│   ├── get_card_type_values.py         # Получение значений enum-поля
│   └── test.py                          # Тестовый запрос задачи
│
├── Dockerfile                     # Сборка образа
├── .dockerignore                  # Исключения для сборки
├── requirements.txt               # Зависимости (requests, pandas, ...)
├── .gitignore                      # Игнорируемые файлы
├── .env.example                    # Пример переменных окружения
└── docker-compose.yml              # Запуск контейнеров (n8n, cloudpub, python-runner)