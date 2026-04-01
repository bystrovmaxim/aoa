# src/action_machine/auth/check_roles.py
"""
Декоратор @check_roles — объявление требований к ролям для выполнения действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @check_roles — часть грамматики намерений ActionMachine. Объявляет,
какие роли пользователя необходимы для выполнения действия. При запуске
машина (ActionProductMachine) читает роли из ClassMetadata и сравнивает
с ролями пользователя в контексте. Если роли не совпадают — действие
отклоняется с AuthorizationError.

═══════════════════════════════════════════════════════════════════════════════
СПЕЦИАЛЬНЫЕ ЗНАЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

Специальные значения определены на уровне модуля ``auth/constants.py``
и реэкспортируются через ``auth/__init__.py``:

    ROLE_NONE — действие не требует аутентификации. Любой пользователь
                (включая анонимного) может выполнить действие.
    ROLE_ANY  — действие требует аутентификации, но любая роль подходит.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к классам, не к функциям, методам или свойствам.
- Класс должен наследовать RoleGateHost — миксин, разрешающий @check_roles.
- Аргумент spec должен быть строкой, списком строк, ROLE_NONE или ROLE_ANY.
- Пустой список ролей запрещён — это скорее всего ошибка.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @check_roles("admin")
        │
        ▼  Декоратор записывает в cls._role_info
    {"spec": "admin"}
        │
        ▼  MetadataBuilder → collectors.collect_role(cls)
    ClassMetadata.role = RoleMeta(spec="admin")
        │
        ▼  ActionProductMachine._check_action_roles(...)
    Сравнивает spec с context.user.roles, используя ROLE_NONE/ROLE_ANY

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import check_roles, ROLE_NONE, ROLE_ANY

    @check_roles("admin")
    class DeleteUserAction(BaseAction[DeleteParams, DeleteResult]):
        ...

    @check_roles(["user", "manager"])
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @check_roles(ROLE_ANY)
    class ProfileAction(BaseAction[ProfileParams, ProfileResult]):
        ...

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — декоратор применён не к классу; класс не наследует RoleGateHost;
               spec имеет неверный тип.
    ValueError — передан пустой список ролей; элементы списка не строки.
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.role_gate_host import RoleGateHost


def check_roles(spec: str | list[str]) -> Any:
    """
    Декоратор уровня класса. Объявляет ролевые требования для действия.

    Записывает словарь ``{"spec": spec}`` в атрибут ``cls._role_info``
    целевого класса. MetadataBuilder читает этот словарь при сборке
    ClassMetadata.role (RoleMeta).

    Аргументы:
        spec: требуемые роли. Допустимые значения:
              - строка: одна роль ("admin") или спецзначение (ROLE_NONE, ROLE_ANY).
              - список строк: несколько ролей (["user", "manager"]).

    Возвращает:
        Декоратор, который записывает _role_info в класс и возвращает
        класс без изменений.

    Исключения:
        TypeError: spec не строка и не список; декоратор применён не к классу;
                  класс не наследует RoleGateHost.
        ValueError: пустой список; элементы списка не строки.

    Пример:
        @check_roles("admin")
        class AdminAction(BaseAction[P, R]):
            ...

        @check_roles(ROLE_NONE)
        class PublicAction(BaseAction[P, R]):
            ...
    """
    # ── Валидация spec ──
    if isinstance(spec, str):
        validated_spec: str | list[str] = spec
    elif isinstance(spec, list):
        if len(spec) == 0:
            raise ValueError(
                "@check_roles: передан пустой список ролей. "
                "Укажите хотя бы одну роль или используйте ROLE_NONE."
            )
        for i, item in enumerate(spec):
            if not isinstance(item, str):
                raise ValueError(
                    f"@check_roles: элемент списка ролей [{i}] должен быть строкой, "
                    f"получен {type(item).__name__}: {item!r}."
                )
        validated_spec = spec
    else:
        raise TypeError(
            f"@check_roles ожидает строку или список строк, "
            f"получен {type(spec).__name__}: {spec!r}."
        )

    def decorator(cls: Any) -> Any:
        """
        Внутренний декоратор, применяемый к классу.

        Проверяет:
        1. cls — класс (type).
        2. cls наследует RoleGateHost.

        Затем записывает _role_info в cls.
        """
        if not isinstance(cls, type):
            raise TypeError(
                f"@check_roles можно применять только к классу. "
                f"Получен объект типа {type(cls).__name__}: {cls!r}."
            )

        if not issubclass(cls, RoleGateHost):
            raise TypeError(
                f"@check_roles применён к классу {cls.__name__}, "
                f"который не наследует RoleGateHost. "
                f"Добавьте RoleGateHost в цепочку наследования."
            )

        cls._role_info = {
            "spec": validated_spec,
        }

        return cls

    return decorator
