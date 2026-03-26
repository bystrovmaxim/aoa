# src/action_machine/dependencies/depends.py
"""
Декоратор @depends — объявление зависимости действия от внешнего сервиса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Прикрепляет к классу действия информацию о требуемой зависимости.
При выполнении действия машина (ActionProductMachine) читает список зависимостей,
создаёт экземпляры через DependencyFactory и передаёт их в ToolsBox,
откуда аспект получает их через box.resolve(PaymentService).

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к классам, не к функциям, методам или свойствам.
- Класс должен наследовать DependencyGateHost — миксин, разрешающий @depends.
- Аргумент klass должен быть классом (type), не экземпляром и не строкой.
- klass должен быть подклассом верхней границы, заданной в дженерик-параметре
  DependencyGateHost[T]. Для BaseAction (T=object) — любой класс допустим.
  Для будущих хостов (T=BaseResourceManager) — только подклассы.
- Повторное объявление одной и той же зависимости на одном классе запрещено.
- Параметр description должен быть строкой.

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
        ▼  MetadataBuilder._collect_dependencies(cls)
    ClassMetadata.dependencies = (DependencyInfo(...), ...)
        │
        ▼  ActionProductMachine._get_factory(action)
    DependencyGate → DependencyFactory
        │
        ▼  ToolsBox.resolve(PaymentService)
    Возвращает экземпляр PaymentService

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    @depends(PaymentService, description="Сервис обработки платежей")
    @depends(NotificationService, description="Сервис уведомлений")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Обработка платежа")
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — klass не является классом; klass не подкласс верхней границы;
               декоратор применён не к классу; класс не наследует DependencyGateHost;
               description не строка.
    ValueError — зависимость klass уже объявлена для этого класса.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.dependencies.dependency_gate_host import DependencyGateHost


@dataclass(frozen=True)
class DependencyInfo:
    """
    Неизменяемая запись об одной зависимости действия.

    Создаётся декоратором @depends и сохраняется в cls._depends_info.
    После заморозки шлюза доступна только для чтения.

    Атрибуты:
        cls: класс зависимости (например, PaymentService).
             Используется DependencyFactory для создания экземпляра.
        description: человекочитаемое описание назначения зависимости.
                     Используется для интроспекции и документации.
    """
    cls: type
    description: str = ""


def depends(klass: Any, *, description: str = "") -> Callable[[type], type]:
    """
    Декоратор уровня класса. Объявляет зависимость от внешнего сервиса.

    Записывает DependencyInfo в атрибут cls._depends_info целевого класса.
    При первом применении к подклассу копирует родительский список,
    чтобы не мутировать его.

    Аргументы:
        klass: класс зависимости. Должен быть типом (type), не экземпляром.
               Должен быть подклассом верхней границы дженерика DependencyGateHost[T].
        description: описание зависимости для документации и интроспекции.
                     По умолчанию пустая строка.

    Возвращает:
        Декоратор, который добавляет DependencyInfo в cls._depends_info
        и возвращает класс без изменений.

    Исключения:
        TypeError:
            - klass не является классом (type).
            - klass не подкласс верхней границы (bound).
            - description не является строкой.
            - Декоратор применён не к классу.
            - Класс не наследует DependencyGateHost.
        ValueError:
            - Зависимость klass уже объявлена для этого класса.
    """
    # ── Проверка аргументов декоратора (выполняется при вызове @depends(...)) ──

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
        1. cls — класс (type), не функция/метод/свойство.
        2. cls наследует DependencyGateHost.
        3. klass — подкласс верхней границы дженерика.
        4. Дубликатов нет.

        Затем добавляет DependencyInfo в cls._depends_info.
        """
        # ── Проверка цели декоратора (выполняется при определении класса) ──

        # Цель — класс, а не функция/метод/свойство
        if not isinstance(cls, type):
            raise TypeError(
                f"@depends можно применять только к классу. "
                f"Получен объект типа {type(cls).__name__}: {cls!r}."
            )

        if not issubclass(cls, DependencyGateHost):
            raise TypeError(
                f"@depends({klass.__name__}) применён к классу {cls.__name__}, "
                f"который не наследует DependencyGateHost. "
                f"Добавьте DependencyGateHost в цепочку наследования."
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
        # Копируем родительский, чтобы не мутировать его
        if '_depends_info' not in cls.__dict__:
            cls._depends_info = list(getattr(cls, '_depends_info', []))

        # ── Проверка дубликатов ──
        if any(info.cls is klass for info in cls._depends_info):
            raise ValueError(
                f"@depends({klass.__name__}) уже объявлен для класса {cls.__name__}. "
                f"Удалите дублирующий декоратор."
            )

        # ── Регистрация зависимости ──
        cls._depends_info.append(DependencyInfo(cls=klass, description=description))

        return cls

    return decorator
