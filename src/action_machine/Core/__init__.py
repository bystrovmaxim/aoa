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
ОСТАЛЬНЫЕ КОМПОНЕНТЫ ЯДРА
═══════════════════════════════════════════════════════════════════════════════

- BaseAction — абстрактный базовый класс для всех действий.
  Наследует ActionMetaGateHost, что делает @meta обязательным.
- BaseActionMachine — абстрактная машина с методом run().
- GateCoordinator — центральный реестр метаданных, фабрик и графа.
  Поддерживает strict-режим для обязательности domain в @meta.
- ClassMetadata — иммутабельный снимок метаданных класса.
  Содержит поле meta: MetaInfo | None для описания и домена.
- BaseParams — read-only параметры действия (pydantic, frozen).
- BaseResult — read-write результат действия (pydantic, mutable).
- BaseState — read-write состояние конвейера аспектов.
- ToolsBox — контейнер инструментов для аспектов.
- ReadableMixin — миксин для dict-подобного доступа к атрибутам.
- WritableMixin — миксин для записи атрибутов через dict-интерфейс.
- Протоколы ReadableDataProtocol / WritableDataProtocol.

- ActionMetaGateHost — маркерный миксин, обозначающий обязательность
  декоратора @meta для действий. Наследуется BaseAction.
- ResourceMetaGateHost — маркерный миксин, обозначающий обязательность
  декоратора @meta для ресурсных менеджеров. Наследуется BaseResourceManager.
- meta — декоратор для объявления описания и доменной принадлежности класса.

- Исключения: AuthorizationError, ValidationFieldError, HandleError,
  TransactionError, CyclicDependencyError и др.

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
