# src/action_machine/Auth/check_roles.py
"""
Декоратор @CheckRoles — объявление требований к ролям для выполнения действия.

Назначение:
    Декоратор @CheckRoles — часть грамматики намерений ActionMachine. Он объявляет,
    какие роли пользователя необходимы для выполнения действия. При запуске
    машина (ActionProductMachine) читает роли из шлюза и сравнивает с ролями
    пользователя в контексте. Если роли не совпадают — действие отклоняется.

Специальные значения:
    CheckRoles.NONE — действие не требует аутентификации. Любой пользователь
                      (включая анонимного) может выполнить действие.
    CheckRoles.ANY  — действие требует аутентификации, но любая роль подходит.

Ограничения (инварианты):
    - Применяется только к классам, не к функциям, методам или свойствам.
    - Класс должен наследовать RoleGateHost — миксин, разрешающий @CheckRoles.
    - Первый аргумент (spec) должен быть строкой, списком строк,
      CheckRoles.NONE или CheckRoles.ANY.
    - Пустой список ролей запрещён — это скорее всего ошибка.
    - Параметр desc должен быть строкой.

Пример:
    @CheckRoles("admin", desc="Только для администраторов")
    class DeleteUserAction(BaseAction[DeleteParams, DeleteResult]):
        ...

    @CheckRoles(["user", "manager"], desc="Для пользователей и менеджеров")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

Ошибки:
    TypeError — декоратор применён не к классу; класс не наследует RoleGateHost;
               spec имеет неверный тип; desc не строка.
    ValueError — передан пустой список ролей; элементы списка не строки.
"""

from __future__ import annotations

from typing import Any


class CheckRoles:
    """
    Декоратор и контейнер констант для объявления ролевых требований.

    Используется как декоратор класса:
        @CheckRoles("admin")
        @CheckRoles(["user", "manager"])
        @CheckRoles(CheckRoles.NONE)
        @CheckRoles(CheckRoles.ANY)

    Константы:
        NONE: str — маркер "аутентификация не требуется".
        ANY: str  — маркер "любая роль подходит".
    """

    NONE: str = "__NONE__"
    ANY: str = "__ANY__"

    def __init__(self, spec: str | list[str], *, desc: str = "") -> None:
        """
        Инициализирует декоратор с указанной спецификацией ролей.

        Аргументы:
            spec: требуемые роли. Допустимые значения:
                  - строка: одна роль ("admin") или спецзначение (NONE, ANY).
                  - список строк: несколько ролей (["user", "manager"]).
            desc: человекочитаемое описание для документации и интроспекции.

        Исключения:
            TypeError: spec не строка и не список; desc не строка.
            ValueError: пустой список; элементы списка не строки.
        """
        # ── Проверка desc ──
        if not isinstance(desc, str):
            raise TypeError(
                f"@CheckRoles: параметр desc должен быть строкой, "
                f"получен {type(desc).__name__}."
            )

        # ── Проверка и нормализация spec ──
        if isinstance(spec, str):
            self._spec: str | list[str] = spec
        elif isinstance(spec, list):
            if len(spec) == 0:
                raise ValueError(
                    "@CheckRoles: передан пустой список ролей. "
                    "Укажите хотя бы одну роль или используйте CheckRoles.NONE."
                )
            for i, item in enumerate(spec):
                if not isinstance(item, str):
                    raise ValueError(
                        f"@CheckRoles: элемент списка ролей [{i}] должен быть строкой, "
                        f"получен {type(item).__name__}: {item!r}."
                    )
            self._spec = spec
        else:
            raise TypeError(
                f"@CheckRoles ожидает строку или список строк, "
                f"получен {type(spec).__name__}: {spec!r}."
            )

        self._desc: str = desc

    def __call__(self, cls: Any) -> Any:
        """
        Применяет декоратор к классу.

        Аргументы:
            cls: класс, к которому применяется декоратор.

        Возвращает:
            Тот же класс с прикреплённой информацией о ролях в cls._role_info.

        Исключения:
            TypeError:
                - cls не является классом (type).
                - cls не наследует RoleGateHost.
        """
        # ── Проверка: цель — класс ──
        if not isinstance(cls, type):
            raise TypeError(
                f"@CheckRoles можно применять только к классу. "
                f"Получен объект типа {type(cls).__name__}: {cls!r}."
            )

        # ── Проверка: класс содержит миксин RoleGateHost ──
        from action_machine.Auth.role_gate_host import RoleGateHost

        if not issubclass(cls, RoleGateHost):
            raise TypeError(
                f"@CheckRoles применён к классу {cls.__name__}, "
                f"который не наследует RoleGateHost. "
                f"Добавьте RoleGateHost в цепочку наследования."
            )

        # ── Сохранение информации о ролях ──
        cls._role_info = {
            "spec": self._spec,
            "desc": self._desc,
        }

        return cls

    @property
    def spec(self) -> str | list[str]:
        """Возвращает спецификацию ролей."""
        return self._spec

    @property
    def desc(self) -> str:
        """Возвращает описание."""
        return self._desc
