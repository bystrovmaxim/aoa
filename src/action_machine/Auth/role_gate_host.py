# src/action_machine/Auth/role_gate_host.py
"""
Модуль: RoleGateHost — маркерный миксин для декоратора @CheckRoles.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RoleGateHost — миксин-маркер, который разрешает применение декоратора
@CheckRoles к классу. Декоратор при применении проверяет:

    if not issubclass(cls, RoleGateHost):
        raise TypeError("Класс должен наследовать RoleGateHost")

Без наследования от RoleGateHost декоратор @CheckRoles выбросит TypeError.
Это защита от случайного применения ролевых ограничений к классам,
которые не являются действиями (Action).

═══════════════════════════════════════════════════════════════════════════════
ЧТО ИЗМЕНИЛОСЬ (рефакторинг «координатор»)
═══════════════════════════════════════════════════════════════════════════════

РАНЬШЕ (до рефакторинга):
    - __init_subclass__ создавал RoleGate, сохранял его в cls._role_gate.
    - Метод get_role_gate() возвращал гейт.
    - Метод get_role_spec() делегировал в гейт.
    - ActionProductMachine обращался к cls.get_role_spec().

ТЕПЕРЬ (после рефакторинга):
    - Миксин — пустой маркер. Никакой логики.
    - Декоратор @CheckRoles записывает _role_info в класс.
    - MetadataBuilder._collect_role(cls) читает _role_info и создаёт
      RoleMeta в ClassMetadata.
    - ActionProductMachine читает metadata.role.spec через координатор.
    - RoleGate, get_role_gate(), get_role_spec() — УДАЛЕНЫ.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleGateHost,                   ← маркер: разрешает @CheckRoles
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,
        ConnectionGateHost,
    ): ...

    @CheckRoles("admin", desc="Только администратор")
    class AdminAction(BaseAction[P, R]):
        ...

    # Декоратор @CheckRoles проверяет:
    #   issubclass(AdminAction, RoleGateHost) → True → OK
    #   Записывает: cls._role_info = {"spec": "admin", "desc": "Только администратор"}

    # MetadataBuilder.build(AdminAction) читает:
    #   cls._role_info → RoleMeta(spec="admin", description="Только администратор")

    # ActionProductMachine:
    #   metadata = coordinator.get(AdminAction)
    #   metadata.role.spec → "admin"
"""

from typing import Any, ClassVar


class RoleGateHost:
    """
    Маркерный миксин, разрешающий использование декоратора @CheckRoles.

    Класс, НЕ наследующий RoleGateHost, не может быть целью @CheckRoles —
    декоратор выбросит TypeError при попытке применения.

    Миксин не содержит логики, полей или методов. Его единственная функция —
    служить проверочным маркером для issubclass().

    Атрибуты уровня класса (создаются динамически декоратором):
        _role_info : dict | None
            Словарь {"spec": str | list[str], "desc": str}, записываемый
            декоратором @CheckRoles. Читается MetadataBuilder при сборке
            ClassMetadata.role (RoleMeta).
            НЕ используется напрямую — только через ClassMetadata.
    """

    # Аннотация для mypy (создается декоратором)
    _role_info: ClassVar[dict[str, Any]]