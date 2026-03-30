# src/action_machine/core/__init__.py
"""
Пакет ядра ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит базовые классы, протоколы, миксины, машины выполнения,
координатор метаданных, исключения и вспомогательные утилиты.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- BaseAction — абстрактный базовый класс для всех действий.
  Наследует ActionMetaGateHost, что делает @meta обязательным.
- BaseActionMachine — абстрактная машина с методами run() и sync_run().
- ActionProductMachine — production-реализация машины действий.
  Принимает GateCoordinator как параметр конструктора.
- ActionTestMachine — тестовая машина с поддержкой моков.
- GateCoordinator — центральный реестр метаданных, фабрик и графа.
  Поддерживает strict-режим для обязательности domain в @meta.
- ClassMetadata — иммутабельный снимок метаданных класса.
  Содержит поле meta: MetaInfo | None для описания и домена.
- BaseParams — read-only параметры действия.
- BaseResult — read-write результат действия.
- BaseState — read-write состояние конвейера аспектов.
- ToolsBox — контейнер инструментов для аспектов.
- MockAction — мок-действие для тестов.
- ReadableMixin — миксин для dict-подобного доступа к атрибутам.
- WritableMixin — миксин для записи атрибутов через dict-интерфейс.
- Протоколы ReadableDataProtocol / WritableDataProtocol.

- ActionMetaGateHost — маркерный миксин, обозначающий обязательность
  декоратора @meta для действий. Наследуется BaseAction.
- ResourceMetaGateHost — маркерный миксин, обозначающий обязательность
  декоратора @meta для ресурсных менеджеров. Наследуется BaseResourceManager.
- meta — декоратор для объявления описания и доменной принадлежности класса.
  Применяется к действиям и ресурсным менеджерам.

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
    @CheckRoles("manager")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @meta(description="Менеджер соединений с PostgreSQL")
    class PostgresManager(BaseResourceManager):
        ...

Каждое действие (BaseAction с аспектами) и каждый ресурсный менеджер
(BaseResourceManager) обязаны иметь @meta. Без него MetadataBuilder
выбросит TypeError при сборке метаданных.

═══════════════════════════════════════════════════════════════════════════════
STRICT-РЕЖИМ КООРДИНАТОРА
═══════════════════════════════════════════════════════════════════════════════

GateCoordinator принимает параметр strict: bool = False.
Если strict=True — domain обязателен в @meta для Action и ResourceManager.
description проверяется всегда (MetadataBuilder).

    coordinator = GateCoordinator(strict=True)
    machine = ActionProductMachine(mode="production", coordinator=coordinator)
"""
