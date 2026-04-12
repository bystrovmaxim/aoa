# src/action_machine/dependencies/depends.py
"""
Декоратор @depends — объявление зависимости действия от внешнего сервиса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Прикрепляет к классу действия информацию о требуемой зависимости.
При выполнении действия машина (ActionProductMachine) читает список зависимостей
из facet-снимка ``depends`` координатора, создаёт DependencyFactory и передаёт в ToolsBox,
откуда аспект получает зависимость через box.resolve(PaymentService).

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к классам, не к функциям, методам или свойствам.
- Класс должен наследовать DependencyIntent — миксин, разрешающий @depends.
- Аргумент klass должен быть классом (type), не экземпляром и не строкой.
- klass должен быть подклассом верхней границы, заданной в дженерик-параметре
  DependencyIntent[T]. Для BaseAction (T=object) — любой класс допустим.
- Повторное объявление одной и той же зависимости на одном классе запрещено.
- Параметр description должен быть строкой.
- Параметр factory (опциональный) должен быть callable или None.

═══════════════════════════════════════════════════════════════════════════════
НАСЛЕДОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

При первом применении @depends к подклассу декоратор копирует родительский
список _depends_info в собственный __dict__. Это гарантирует, что дочерний
класс наследует зависимости родителя, но добавление новых зависимостей
не мутирует родительский список.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @depends(PaymentService, description="Сервис оплаты")
        │
        ▼  Декоратор записывает в cls._depends_info
    DependencyInfo(cls=PaymentService, description="Сервис оплаты")
        │
        ▼  DependencyIntentInspector reads _depends_info
    Снимок: ``coordinator.get_snapshot(cls, \"depends\")`` → зависимости …
        │
        ▼  ``cached_dependency_factory(coordinator, cls)``
    ``DependencyFactory`` из снимка ``depends``
        │
        ▼  ToolsBox.resolve(PaymentService)
    factory.resolve(PaymentService) → PaymentService()

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Базовое использование:
    @depends(PaymentService, description="Сервис обработки платежей")
    @depends(NotificationService, description="Сервис уведомлений")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Обработка платежа")
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

    # Синглтон через lambda:
    _shared_payment = PaymentService(gateway="production")

    @depends(PaymentService, factory=lambda: _shared_payment, description="Синглтон")
    class OrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    # Параметризованная фабрика:
    @depends(BankClient, factory=lambda env: BankClient(env), description="Банк")
    class PayAction(BaseAction[PayParams, PayResult]):

        @regular_aspect("Оплата")
        async def pay(self, params, state, box, connections):
            client = box.resolve(BankClient, "production")
            ...

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — klass не является классом; klass не подкласс верхней границы;
               декоратор применён не к классу; класс не наследует DependencyIntent;
               description не строка.
    ValueError — зависимость klass уже объявлена для этого класса.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.dependencies.dependency_factory import DependencyInfo
from action_machine.dependencies.dependency_intent import DependencyIntent


def depends(
    klass: Any,
    *,
    factory: Callable[..., Any] | None = None,
    description: str = "",
) -> Callable[[type], type]:
    """
    Декоратор уровня класса. Объявляет зависимость от внешнего сервиса.

    Записывает DependencyInfo в атрибут cls._depends_info целевого класса.
    При первом применении к подклассу копирует родительский список,
    чтобы не мутировать его.

    Аргументы:
        klass: класс зависимости. Должен быть типом (type).
               Должен быть подклассом верхней границы DependencyIntent[T].
        factory: опциональная фабрика для создания экземпляра.
                 Если None — используется конструктор по умолчанию.
                 Для синглтонов: factory=lambda: shared_instance.
                 Для параметризованных: factory=lambda env: BankClient(env).
        description: описание зависимости для документации и интроспекции.

    Возвращает:
        Декоратор, который добавляет DependencyInfo в cls._depends_info.

    Исключения:
        TypeError:
            - klass не является классом (type).
            - klass не подкласс верхней границы (bound).
            - description не является строкой.
            - Декоратор применён не к классу.
            - Класс не наследует DependencyIntent.
        ValueError:
            - Зависимость klass уже объявлена для этого класса.
    """
    # ── Проверка аргументов декоратора ──

    if not isinstance(klass, type):
        raise TypeError(
            f"@depends ожидает класс, получен {type(klass).__name__}: {klass!r}. "
            f"Передайте класс, а не экземпляр или строку."
        )

    if not isinstance(description, str):
        raise TypeError(
            f"@depends: параметр description должен быть строкой, "
            f"получен {type(description).__name__}."
        )

    def decorator(cls: type) -> type:
        """
        Внутренний декоратор, применяемый к целевому классу.

        Проверяет:
        1. cls — класс (type).
        2. cls наследует DependencyIntent.
        3. klass — подкласс верхней границы дженерика.
        4. Дубликатов нет.

        Затем добавляет DependencyInfo в cls._depends_info.
        """
        # ── Проверка цели ──
        if not isinstance(cls, type):
            raise TypeError(
                f"@depends можно применять только к классу. "
                f"Получен объект типа {type(cls).__name__}: {cls!r}."
            )

        if not issubclass(cls, DependencyIntent):
            raise TypeError(
                f"@depends({klass.__name__}) применён к классу {cls.__name__}, "
                f"который не наследует DependencyIntent. "
                f"Добавьте DependencyIntent в цепочку наследования."
            )

        # ── Проверка верхней границы дженерика ──
        bound = cls.get_depends_bound()
        if not issubclass(klass, bound):
            raise TypeError(
                f"@depends({klass.__name__}): класс {klass.__name__} "
                f"не является подклассом {bound.__name__}. "
                f"Для {cls.__name__} разрешены только подклассы {bound.__name__}."
            )

        # ── Создание собственного списка зависимостей ──
        if '_depends_info' not in cls.__dict__:
            cls._depends_info = list(getattr(cls, '_depends_info', []))

        # ── Проверка дубликатов ──
        if any(info.cls is klass for info in cls._depends_info):
            raise ValueError(
                f"@depends({klass.__name__}) уже объявлен для класса {cls.__name__}. "
                f"Удалите дублирующий декоратор."
            )

        # ── Регистрация зависимости ──
        cls._depends_info.append(
            DependencyInfo(cls=klass, factory=factory, description=description)
        )

        return cls

    return decorator
