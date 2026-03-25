"""
Декоратор для задания ролевой модели действия.
"""

from typing import Any

from .role_gate import RoleInfo


class CheckRoles:
    """
    Декоратор для задания ролевой модели действия.

    Определяет, какие роли необходимы для выполнения действия.
    Используется как декоратор класса действия.

    Атрибуты:
        NONE (str): Специальное значение, означающее, что действие доступно без аутентификации.
        ANY (str): Специальное значение, означающее, что действие доступно любому аутентифицированному пользователю.
    """

    NONE = "NO_ROLE"
    ANY = "ANY_ROLE"

    def __init__(self, spec: str | list[str], desc: str | None) -> None:
        """
        Инициализирует декоратор.

        :param spec: спецификация ролей:
                     - строка "NO_ROLE" или "ANY_ROLE" для специальных значений,
                     - список строк с конкретными ролями,
                     - строка с конкретной ролью.
        :param desc: описание для документации.
        """
        self.spec = spec
        self.desc = desc

    def __call__(self, cls: type) -> type:
        """
        Применяет декоратор к классу, добавляя атрибуты _role_spec (для обратной совместимости)
        и _role_info (для нового шлюза RoleGate).

        :param cls: класс действия.
        :return: тот же класс с добавленными атрибутами.
        """
        # Старый механизм (будет удалён после полной миграции)
        cls._role_spec = self.spec  # type: ignore

        # Новый механизм – временный атрибут для RoleGateHost
        from .role_gate import RoleInfo
        cls._role_info = RoleInfo(spec=self.spec, description=self.desc)  # type: ignore

        return cls