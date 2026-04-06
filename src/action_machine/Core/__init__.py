# src/action_machine/core/__init__.py
"""
Пакет ядра ActionMachine.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Содержит базовые классы, протоколы, миксины, машины выполнения,
координатор метаданных, исключения и вспомогательные утилиты.
═══════════════════════════════════════════════════════════════════════════════
МАШИНЫ ВЫПОЛНЕНИЯ
═══════════════════════════════════════════════════════════════════════════════
Production-машины (не принимают моки, rollup всегда False):
- **ActionProductMachine** — асинхронная production-машина.
  Публичный метод: ``async def run(context, action, params, connections)``.
  Используется в async-окружениях: FastAPI, aiohttp, asyncio-приложения.
- **SyncActionProductMachine** — синхронная production-машина.
  Публичный метод: ``def run(context, action, params, connections)``.
  Используется в sync-окружениях: CLI-скрипты, Celery, Django без async.
  Внутри вызывает asyncio.run() для выполнения async-конвейера.
Тестовая инфраструктура вынесена в отдельный пакет ``action_machine.testing``:
- **TestBench** — единая immutable точка входа для тестирования.
  Создаёт коллекцию машин, прогоняет действие на каждой, сравнивает
  результаты. Поддерживает моки, fluent API, валидацию state.
- **MockAction** — мок-действие для подстановки в тестах.
- Стабы контекста: UserInfoStub, RuntimeInfoStub, RequestInfoStub, ContextStub.
═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА МАШИН
═══════════════════════════════════════════════════════════════════════════════
    BaseActionMachine (ABC)
        │
        ├── ActionProductMachine              (async, production)
        │       │
        │       └── (используется внутри TestBench)
        │
        └── SyncActionProductMachine          (sync, production)
                │
                └── (используется внутри TestBench)
    TestBench (в пакете testing/)
        ├── создаёт ActionProductMachine
        ├── создаёт SyncActionProductMachine
        ├── прогоняет на обеих
        └── сравнивает результаты
═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТР ROLLUP
═══════════════════════════════════════════════════════════════════════════════
Параметр ``rollup: bool`` присутствует в ``_run_internal()`` всех машин.
- Production-машины: run() всегда передаёт rollup=False внутри.
  Параметр не входит в публичный API production-машин.
- TestBench: терминальные методы (run, run_aspect, run_summary) принимают
  rollup как обязательный параметр без значения по умолчанию.
  Тестировщик явно выбирает режим.
═══════════════════════════════════════════════════════════════════════════════
FROZEN CORE-ТИПЫ
═══════════════════════════════════════════════════════════════════════════════
Все core-типы данных — read-only после создания:
    BaseParams  — pydantic BaseModel, frozen=True. Входные параметры.
    BaseResult  — pydantic BaseModel, frozen=True. Результат действия.
                  Строгая структура: только объявленные поля, без extra.
    BaseState   — обычный класс, frozen (__setattr__/__delattr__ запрещены).
                  Промежуточное состояние конвейера с динамическими полями.
Единственный способ «изменить» любой из них — создать новый экземпляр.
Все core-типы наследуют BaseSchema, обеспечивающую dict-подобный
доступ и dot-path навигацию через resolve().
═══════════════════════════════════════════════════════════════════════════════
ОСТАЛЬНЫЕ КОМПОНЕНТЫ ЯДРА
═══════════════════════════════════════════════════════════════════════════════
- BaseAction — абстрактный базовый класс для всех действий.
  Наследует ActionMetaGateHost, что делает @meta обязательным.
  Оба generic-параметра (P, R) — наследники BaseSchema.
- BaseActionMachine — абстрактная машина с методом run().
- GateCoordinator — центральный реестр метаданных, фабрик и графа.
  Поддерживает strict-режим для обязательности domain в @meta.
  Граф содержит узлы context_field и рёбра requires_context
  для контекстных зависимостей аспектов и обработчиков ошибок.
- ClassMetadata — иммутабельный снимок метаданных класса.
  Содержит поле meta: MetaInfo | None для описания и домена.
- ToolsBox — frozen-контейнер инструментов для аспектов. Не предоставляет
  публичного доступа к Context — аспекты получают данные контекста
  через ContextView при наличии @context_requires.
- BaseSchema — единая базовая схема данных. Наследует pydantic.BaseModel,
  добавляет dict-подобный доступ к полям и dot-path навигацию через
  resolve(). Все core-типы данных наследуют BaseSchema.
- ActionMetaGateHost — маркерный миксин, обозначающий обязательность
  декоратора @meta для действий. Наследуется BaseAction.
- ResourceMetaGateHost — маркерный миксин, обозначающий обязательность
  декоратора @meta для ресурсных менеджеров. Наследуется BaseResourceManager.
- meta — декоратор для объявления описания и доменной принадлежности класса.
- Исключения: AuthorizationError, ValidationFieldError, HandleError,
  TransactionError, CyclicDependencyError, ContextAccessError,
  OnErrorHandlerError, NamingSuffixError, NamingPrefixError и др.
═══════════════════════════════════════════════════════════════════════════════
МЕТАДАННЫЕ
═══════════════════════════════════════════════════════════════════════════════
MetadataBuilder вынесен в отдельный подпакет action_machine.metadata
и НЕ реэкспортируется из core. Импорт:
    from action_machine.metadata import MetadataBuilder
═══════════════════════════════════════════════════════════════════════════════
ДЕКОРАТОР @meta
═══════════════════════════════════════════════════════════════════════════════
Декоратор @meta объявляет обязательное текстовое описание класса и
опциональную привязку к бизнес-домену. Описание хранится в ClassMetadata.meta
(MetaInfo) и попадает в граф координатора.
    from action_machine.core.meta_decorator import meta
    @meta(description="Создание нового заказа", domain=OrdersDomain)
    @check_roles("manager")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...
═══════════════════════════════════════════════════════════════════════════════
STRICT-РЕЖИМ КООРДИНАТОРА
═══════════════════════════════════════════════════════════════════════════════
GateCoordinator принимает параметр strict: bool = False.
Если strict=True — domain обязателен в @meta для Action и ResourceManager.
    coordinator = GateCoordinator(strict=True)
    machine = ActionProductMachine(mode="production", coordinator=coordinator)
"""