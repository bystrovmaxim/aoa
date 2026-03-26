# src/action_machine/dependencies/depends.py
"""
Декоратор @depends — объявление зависимости действия от внешнего сервиса.

Прикрепляет к классу действия информацию о требуемой зависимости.
При выполнении действия машина (ActionProductMachine) читает список зависимостей,
создаёт экземпляры через DependencyFactory и передаёт их в ToolsBox,
откуда аспект получает их через box.resolve(PaymentService).

Ограничения (инварианты):
    - Применяется только к классам, не к функциям, методам или свойствам.
    - Класс должен наследовать DependencyGateHost — миксин, разрешающий @depends.
    - Аргумент klass должен быть классом (type), не экземпляром и не строкой.
    - klass должен быть подклассом верхней границы, заданной в дженерик-параметре
      DependencyGateHost[T]. Для BaseAction (T=object) — любой класс допустим.
      Для будущих хостов (T=BaseResourceManager) — только подклассы.
    - Повторное объявление одной и той же зависимости на одном классе запрещено.
    - Параметр description должен быть строкой.

Наследование:
    При первом применении @depends к подклассу декоратор копирует родительский
    список _depends_info в собственный __dict__. Это гарантирует, что дочерний
    класс наследует зависимости родителя, но добавление новых зависимостей
    не мутирует родительский список.

Пример:
    @depends(PaymentService, description="Сервис обработки платежей")
    @depends(NotificationService, description="Сервис уведомлений")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Обработка платежа")
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

Ошибки:
    TypeError — klass не является классом; klass не подкласс верхней границы;
               декоратор применён не к классу; класс не наследует DependencyGateHost;
               description не строка.
    ValueError — зависимость klass уже объявлена для этого класса.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


def depends(klass: Any, *, description: str = ""):
    """
    Декоратор уровня класса. Объявляет зависимость от внешнего сервиса.

    Аргументы:
        klass: класс зависимости. Должен быть типом (type), не экземпляром.
               Должен быть подклассом верхней границы дженерика DependencyGateHost[T].
        description: описание зависимости для документации и интроспекции.

    Возвращает:
        Декоратор, который добавляет DependencyInfo в cls._depends_info.

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

    def decorator(cls):
        # ── Проверка цели декоратора (выполняется при определении класса) ──

        # Цель — класс, а не функция/метод/свойство
        if not isinstance(cls, type):
            raise TypeError(
                f"@depends можно применять только к классу. "
                f"Получен объект типа {type(cls).__name__}: {cls!r}."
            )

        # Класс содержит миксин DependencyGateHost
        from action_machine.dependencies.dependency_gate_host import DependencyGateHost

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

        # Создаём собственный список зависимостей для этого класса,
        # копируя родительский, чтобы не мутировать его
        if '_depends_info' not in cls.__dict__:
            cls._depends_info = list(getattr(cls, '_depends_info', []))

        # Проверка дубликатов
        if any(info.cls is klass for info in cls._depends_info):
            raise ValueError(
                f"@depends({klass.__name__}) уже объявлен для класса {cls.__name__}. "
                f"Удалите дублирующий декоратор."
            )

        # Регистрация зависимости
        cls._depends_info.append(DependencyInfo(cls=klass, description=description))

        return cls

    return decorator
