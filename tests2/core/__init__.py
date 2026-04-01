# tests2/core/__init__.py
"""
Core-тесты — полное покрытие ядра ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Тесты всех компонентов ядра системы ActionMachine:

- BaseState — состояние конвейера аспектов. Динамические поля, создание
  из словаря, dict-подобный доступ через ReadableMixin и WritableMixin,
  сериализация через to_dict(), resolve по dot-path.

- BaseParams — входные параметры действия. Pydantic BaseModel с frozen=True.
  Валидация типов, constraints (gt, min_length, pattern), ReadableMixin
  для dict-подобного чтения, JSON Schema через model_json_schema().

- BaseResult — результат действия. Pydantic BaseModel без frozen. Поддержка
  динамических extra-полей через extra="allow", WritableMixin для записи.

- ReadableMixin — миксин для dict-подобного чтения атрибутов объекта.
  Методы keys(), values(), items(), __getitem__, __contains__, get().
  Метод resolve() для навигации по вложенным объектам через dot-path.
  Кеширование результатов resolve в _resolve_cache.

- WritableMixin — миксин для dict-подобной записи атрибутов объекта.
  Методы __setitem__, __delitem__, write() с allowed_keys, update().

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
  зависимостей, направленный ациклический граф на rustworkx, strict-режим
  для обязательности domain в @meta, доменные узлы и рёбра belongs_to.

- Pydantic-интеграция — валидация описаний полей через
  DescribedFieldsGateHost, сбор FieldDescriptionMeta с constraints
  и examples, JSON Schema.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

Все тесты используют доменную модель из tests2/domain/ где возможно.
Намеренно сломанные классы (без @meta, без summary, с циклическими
зависимостями) создаются внутри тестовых файлов, потому что они
не могут быть частью рабочей доменной модели.

Каждый тест структурирован по Arrange–Act–Assert с комментариями,
объясняющими суть сценария на уровне бизнес-смысла.
"""
