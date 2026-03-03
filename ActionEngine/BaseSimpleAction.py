# Файл: ActionEngine/BaseSimpleAction.py
"""
Базовый класс для всех действий (stateless).

Требования:
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from .Context import Context
from .CheckRoles import CheckRoles
from .Exceptions import AuthorizationException, ValidationFieldException

class BaseSimpleAction(ABC):
    """
    Базовый класс для всех действий.

    Реализует конвейер из четырёх аспектов, которые вызываются в порядке:
    1. _permissionAuthorizationAspect — проверка прав доступа.
    2. _validationAspect — валидация входных параметров.
    3. _handleAspect — основная бизнес-логика (обязателен к переопределению).
    4. _postHandleAspect — пост-обработка (опционально).

    Каждый аспект принимает текущий результат (result) и возвращает новый.
    Это позволяет передавать данные между аспектами без использования полей класса.
    """

    def _getRoleSpec(self):
        """
        Возвращает спецификацию ролей, заданную декоратором CheckRoles.
        Если декоратор не применён, возвращает CheckRoles.NONE.
        """
        return getattr(self.__class__, "_role_spec", CheckRoles.NONE)

    def _getFieldCheckers(self):
        """
        Возвращает список чекеров полей, заданных декораторами вида StringFieldChecker и т.п.
        """
        return getattr(self.__class__, "_field_checkers", [])

    def _checkRole(self, ctx: Context) -> None:
        """
        Проверяет, соответствует ли роль пользователя требуемой спецификации.
        При несоответствии выбрасывает AuthorizationException.
        """
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

        # spec — строка (одна роль)
        if spec in user_roles:
            return
        raise AuthorizationException(f"Доступ запрещён. Требуется роль: '{spec}', роли пользователя: {user_roles}")

    def _checkParams(self, ctx: Context, params: Dict[str, Any]) -> None:
        """
        Проверяет параметры с помощью зарегистрированных чекеров.
        Если какой-то параметр не проходит проверку, выбрасывает ValidationFieldException.
        Также проверяет, нет ли лишних параметров, не описанных чекерами.
        """
        checkers = self._getFieldCheckers()
        for checker in checkers:
            checker.check(params)

        expected_fields = {c.field_name for c in checkers}
        extra = set(params.keys()) - expected_fields
        if extra:
            raise ValidationFieldException(f"Неожиданные параметры: {', '.join(extra)}")

    def _permissionAuthorizationAspect(self, ctx: Context, params: Dict[str, Any], result: Any) -> Any:
        """
        Аспект авторизации.
        Проверяет права доступа и возвращает result (обычно без изменений).
        Может быть переопределён для сложной логики, но обычно достаточно базовой проверки ролей.
        """
        self._checkRole(ctx)
        return result

    def _validationAspect(self, ctx: Context, params: Dict[str, Any], result: Any) -> Any:
        """
        Аспект валидации.
        Проверяет параметры и возвращает result (обычно без изменений).
        """
        self._checkParams(ctx, params)
        return result

    @abstractmethod
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Any) -> Any:
        """
        Аспект основной бизнес-логики.
        Должен быть переопределён в наследнике. Принимает текущий result и возвращает новый.
        """
        pass

    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Any) -> Any:
        """
        Аспект пост-обработки.
        Может модифицировать результат или выполнить дополнительные действия (логирование, уведомления).
        По умолчанию возвращает result без изменений.
        """
        return result

    def run(self, ctx: Context, params: Dict[str, Any]) -> Any:
        """
        Публичный метод запуска действия.
        Последовательно вызывает аспекты, начиная с result=None.
        Возвращает результат последнего аспекта.
        """
        result = None
        result = self._permissionAuthorizationAspect(ctx, params, result)
        result = self._validationAspect(ctx, params, result)
        result = self._handleAspect(ctx, params, result)
        result = self._postHandleAspect(ctx, params, result)
        return result