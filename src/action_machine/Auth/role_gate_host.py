# src/action_machine/auth/role_gate_host.py
"""
Модуль: RoleGateHost — маркерный миксин для декоратора @check_roles.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RoleGateHost — миксин-маркер, который разрешает применение декоратора
@check_roles к классу. Декоратор при применении проверяет:

    if not issubclass(cls, RoleGateHost):
        raise TypeError("Класс должен наследовать RoleGateHost")

Без наследования от RoleGateHost декоратор @check_roles выбросит TypeError.
Это защита от случайного применения ролевых ограничений к классам,
которые не являются действиями (Action).

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleGateHost,                   ← маркер: разрешает @check_roles
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,
        ConnectionGateHost,
    ): ...

    @check_roles("admin")
    class AdminAction(BaseAction[P, R]):
        ...

    # Декоратор @check_roles проверяет:
    #   issubclass(AdminAction, RoleGateHost) → True → OK
    #   Записывает: cls._role_info = {"spec": "admin"}

    # MetadataBuilder.build(AdminAction) читает:
    #   cls._role_info → RoleMeta(spec="admin")

    # ActionProductMachine:
    #   metadata = coordinator.get(AdminAction)
    #   metadata.role.spec → "admin"
"""

from typing import Any, ClassVar


class RoleGateHost:
    """
    Маркерный миксин, разрешающий использование декоратора @check_roles.

    Класс, НЕ наследующий RoleGateHost, не может быть целью @check_roles —
    декоратор выбросит TypeError при попытке применения.

    Миксин не содержит логики, полей или методов. Его единственная функция —
    служить проверочным маркером для issubclass().

    Атрибуты уровня класса (создаются динамически декоратором):
        _role_info : dict | None
            Словарь {"spec": str | list[str]}, записываемый
            декоратором @check_roles. Читается MetadataBuilder при сборке
            ClassMetadata.role (RoleMeta).
    """

    # Аннотация для mypy (создается декоратором)
    _role_info: ClassVar[dict[str, Any]]
