# tests/core/__init__.py
"""
Core-тесты — полное покрытие ядра ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Тесты всех компонентов ядра системы ActionMachine:

- BaseState — состояние конвейера аспектов. Динамические поля, создание
  из словаря, dict-подобный доступ через BaseSchema [2], extra="allow"
  для динамических полей [1], сериализация через to_dict(),
  resolve по dot-path.

- BaseParams — входные параметры действия. Pydantic BaseModel с frozen=True.
  Валидация типов, constraints (gt, min_length, pattern), dict-подобный
  доступ через BaseSchema [2], JSON Schema через model_json_schema().

- BaseResult — результат действия. Pydantic BaseModel с frozen=True [1].
  Строгая структура: только объявленные поля, без extra.
  Dict-подобный доступ через BaseSchema [2].

- BaseSchema — единая базовая схема данных [2]. Наследует pydantic.BaseModel,
  добавляет dict-подобный доступ к полям (keys, values, items, __getitem__,
  __contains__, get) и dot-path навигацию через resolve(). Все core-типы
  данных наследуют BaseSchema.

- BaseAction — абстрактный базовый класс действий. Кеширование полного
  имени класса через get_full_class_name(). Наследование шести
  гейт-хостов (ActionMetaGateHost, RoleGateHost, DependencyGateHost,
  CheckerGateHost, AspectGateHost, ConnectionGateHost).

- ActionProductMachine — асинхронная machine выполнения действий.
  Проверка ролей, валидация connections, конвейер аспектов с чекерами,
  события плагинов, nest_level, логирование через ScopedLogger.

- SyncActionProductMachine — синхронная обёртка над ActionProductMachine.
  Вызывает asyncio.run() внутри run(). Те же проверки и конвейер.

- ToolsBox — контейнер инструментов для аспектов. Резолв зависимостей
  через resolve(), запуск дочерних действий через run(), обёртка
  connections через _wrap_connections(), прокси к ScopedLogger.

- DependencyFactory — stateless-фабрика зависимостей. Создание через
  конструктор или factory-функцию, поддержка *args/**kwargs,
  lambda-синглтоны, проверка rollup для BaseResourceManager.

- GateCoordinator — центральный реестр метаданных, фабрик и графа.
  Ленивая сборка через MetadataBuilder, кеширование, рекурсивный обход
  зависимостей, направленный ациклический граф на rustworkx, инвариант
  domain в @meta при get() для действий с аспектами и ресурсов, доменные узлы.

- Pydantic-интеграция — валидация описаний полей через
  DescribedFieldsGateHost, сбор snapshot описаний полей с constraints
  и examples, JSON Schema.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

Все тесты используют доменную модель из tests/domain/ где возможно.
Намеренно сломанные классы (без @meta, без summary, с циклическими
зависимостями) создаются внутри тестовых файлов, потому что они
не могут быть частью рабочей доменной модели.

Каждый тест структурирован по Arrange–Act–Assert с комментариями,
объясняющими суть сценария на уровне бизнес-смысла.
"""
