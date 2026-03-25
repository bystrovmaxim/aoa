# src/action_machine/Auth/check_roles.py
"""
Декоратор для задания ролевой модели действия.

Декоратор проверяет, что целевой класс наследует RoleGateHost,
который объявляет атрибут _role_info. Если нет — выбрасывает TypeError.
Это гарантирует, что декоратор не добавляет динамических атрибутов —
все поля объявлены в миксине.
"""

from .role_gate import RoleInfo
from .role_gate_host import RoleGateHost


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
        Применяет декоратор к классу, записывая ролевую спецификацию
        в атрибут _role_info, объявленный в RoleGateHost.

        Проверяет, что класс наследует RoleGateHost. Если нет — TypeError.

        :param cls: класс действия.
        :return: тот же класс с обновлённым _role_info.

        :raises TypeError: если класс не наследует RoleGateHost.
        """
        if not issubclass(cls, RoleGateHost):
            raise TypeError(
                f"@CheckRoles can only be applied to classes inheriting RoleGateHost. "
                f"Class {cls.__name__} does not inherit RoleGateHost. "
                f"Ensure the class inherits from BaseAction or RoleGateHost directly."
            )

        # _role_info объявлен в RoleGateHost как ClassVar[RoleInfo | None],
        # поэтому после issubclass-проверки mypy знает о его существовании.
        cls._role_info = RoleInfo(spec=self.spec, description=self.desc)

        return cls
