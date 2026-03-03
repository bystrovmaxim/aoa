# ActionEngine/BaseSimpleAction.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from .Context import Context
from .CheckRoles import CheckRoles
from .Exceptions import AuthorizationException, ValidationFieldException


class BaseSimpleAction(ABC):
    """
    Базовый класс для всех действий. Не перехватывает исключения, они всплывают наружу.
    """

    def _getRoleSpec(self):
        return getattr(self.__class__, "_role_spec", CheckRoles.NONE)

    def _getFieldCheckers(self):
        return getattr(self.__class__, "_field_checkers", [])

    def _checkRole(self, ctx: Context) -> None:
        spec = self._getRoleSpec()
        user_roles = ctx.roles

        if spec == CheckRoles.NONE:
            return

        if spec == CheckRoles.ANY:
            if not user_roles:
                raise AuthorizationException("Требуется аутентификация: пользователь должен иметь хотя бы одну роль")
            return

        if isinstance(spec, list):
            if any(role in user_roles for role in spec):
                return
            raise AuthorizationException(f"Доступ запрещён. Требуется одна из ролей: {spec}, роли пользователя: {user_roles}")

        if spec in user_roles:
            return
        raise AuthorizationException(f"Доступ запрещён. Требуется роль: '{spec}', роли пользователя: {user_roles}")

    def _checkParams(self, ctx: Context, params: Dict[str, Any]) -> None:
        checkers = self._getFieldCheckers()
        for checker in checkers:
            checker.check(params)

        expected_fields = {c.field_name for c in checkers}
        extra = set(params.keys()) - expected_fields
        if extra:
            raise ValidationFieldException(f"Неожиданные параметры: {', '.join(extra)}")

    def _permissionAuthorizationAspect(self, ctx: Context, params: Dict[str, Any]) -> None:
        self._checkRole(ctx)

    def _validationAspect(self, ctx: Context, params: Dict[str, Any]) -> None:
        self._checkParams(ctx, params)

    @abstractmethod
    def _handleAspect(self, ctx: Context, params: Dict[str, Any]) -> None:
        """
        Аспект основной бизнес-логики.
        При успехе должен сохранить результат в self._result.
        При ошибке поднимает HandleException (или другое исключение).
        """
        pass

    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any]) -> None:
        """
        Аспект пост-обработки. По умолчанию ничего не делает.
        """
        pass

    def run(self, ctx: Context, params: Dict[str, Any]) -> Any:
        """
        Запускает выполнение действия, последовательно вызывая аспекты.
        Возвращает результат (то, что сохранено в self._result).
        В случае ошибки выбрасывает исключение.
        """
        self._permissionAuthorizationAspect(ctx, params)
        self._validationAspect(ctx, params)
        self._handleAspect(ctx, params)
        self._postHandleAspect(ctx, params)

        return getattr(self, "_result", None)