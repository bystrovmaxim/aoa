# src/action_machine/Auth/role_gate.py
"""
RoleGate – шлюз для управления ролевой спецификацией действия.

Хранит информацию о ролях, заданную декоратором @CheckRoles.
Действие может иметь только одну спецификацию ролей (строка или список строк).

После завершения сборки (в __init_subclass__ действия) шлюз замораживается,
и любые попытки регистрации или удаления вызывают RuntimeError.
"""

from dataclasses import dataclass
from typing import Any

from action_machine.Core.base_gate import BaseGate

# Спецификация роли может быть строкой (одна роль) или списком строк
RoleSpec = str | list[str]


@dataclass(frozen=True)
class RoleInfo:
    """
    Неизменяемая информация о ролевой спецификации.

    Атрибуты:
        spec: спецификация ролей (строка или список строк).
        description: описание ролевого требования (для документации).
    """
    spec: RoleSpec
    description: str | None


class RoleGate(BaseGate[RoleInfo]):
    """
    Шлюз для управления ролевой спецификацией.

    Внутреннее хранение:
        _role: RoleInfo | None – единственная зарегистрированная спецификация.
        _frozen: bool – флаг, указывающий, что шлюз заморожен.
    """

    def __init__(self) -> None:
        """Инициализирует пустой шлюз ролей."""
        self._role: RoleInfo | None = None
        self._frozen: bool = False

    def _check_frozen(self) -> None:
        """Проверяет, не заморожен ли шлюз. Если заморожен – выбрасывает RuntimeError."""
        if self._frozen:
            raise RuntimeError("RoleGate is frozen, cannot modify")

    def register(self, _component: RoleInfo, **metadata: Any) -> RoleInfo:
        """
        Регистрирует спецификацию ролей.

        Если спецификация уже зарегистрирована, выбрасывает ValueError.

        Аргументы:
            _component: информация о ролевой спецификации.
            **metadata: не используется, но оставлен для совместимости с BaseGate.

        Возвращает:
            Зарегистрированный компонент.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
            ValueError: если спецификация уже зарегистрирована.
        """
        self._check_frozen()
        if self._role is not None:
            raise ValueError("RoleGate already has a registered role specification")
        self._role = _component
        return _component

    def unregister(self, _component: RoleInfo) -> None:
        """
        Удаляет спецификацию, если она совпадает с текущей.

        Аргументы:
            _component: информация о ролевой спецификации для удаления.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
        """
        self._check_frozen()
        if self._role is _component:
            self._role = None

    def get_components(self) -> list[RoleInfo]:
        """
        Возвращает список с единственной спецификацией (если есть), иначе пустой список.

        Возвращаемый список является копией, чтобы предотвратить внешние модификации.

        Возвращает:
            Список с RoleInfo или пустой список.
        """
        return [self._role] if self._role is not None else []

    # -------------------- Дополнительные методы для удобства --------------------

    def get_role_spec(self) -> RoleSpec | None:
        """
        Возвращает спецификацию ролей (строку или список строк).

        Если спецификация является списком, возвращается его копия, чтобы
        предотвратить внешние модификации.

        Возвращает:
            Спецификацию или None, если не зарегистрирована.
        """
        if self._role is None:
            return None
        spec = self._role.spec
        if isinstance(spec, list):
            return spec.copy()
        return spec

    def get_description(self) -> str | None:
        """
        Возвращает описание ролевого требования.

        Возвращает:
            Описание или None.
        """
        return self._role.description if self._role else None

    def has_role(self) -> bool:
        """
        Проверяет, зарегистрирована ли спецификация ролей.

        Возвращает:
            True если спецификация есть, иначе False.
        """
        return self._role is not None

    def freeze(self) -> None:
        """
        Замораживает шлюз, запрещая дальнейшие изменения.

        Вызывается после завершения сбора ролевой спецификации в __init_subclass__.
        """
        self._frozen = True