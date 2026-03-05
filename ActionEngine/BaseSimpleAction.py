# Файл: ActionEngine/BaseSimpleAction.py
"""
Базовый класс для всех действий (stateless).

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Callable, List
from .Context import Context
from .CheckRoles import CheckRoles
from .Exceptions import AuthorizationException, ValidationFieldException


class BaseSimpleAction(ABC):
    """
    Базовый класс для всех действий.

    Реализует конвейер из пяти аспектов, которые вызываются в порядке:
    1. _permissionAuthorizationAspect — проверка прав доступа.
    2. _validationAspect — валидация входных параметров.
    3. _preHandleAspect — предварительная обработка (подготовка данных).
    4. _handleAspect — основная бизнес-логика (обязателен к переопределению).
    5. _postHandleAspect — пост-обработка (опционально).

    Каждый аспект получает на вход текущий результат (словарь) и возвращает
    (возможно, модифицированный) словарь. После выполнения каждого аспекта
    применяются чекеры результата, привязанные к этому методу.
    """

    def _getRoleSpec(self):
        """Возвращает спецификацию ролей, заданную декоратором CheckRoles."""
        return getattr(self.__class__, "_role_spec", CheckRoles.NONE)

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
                raise AuthorizationException(
                    "Требуется аутентификация: пользователь должен иметь хотя бы одну роль"
                )
            return
        if isinstance(spec, list):
            if any(role in user_roles for role in spec):
                return
            raise AuthorizationException(
                f"Доступ запрещён. Требуется одна из ролей: {spec}, роли пользователя: {user_roles}"
            )
        if spec in user_roles:
            return
        raise AuthorizationException(
            f"Доступ запрещён. Требуется роль: '{spec}', роли пользователя: {user_roles}"
        )

    def _apply_checkers(self, checkers: List, data: Dict[str, Any], context_info: str) -> None:
        """Применяет список чекеров к словарю data."""
        for checker in checkers:
            try:
                checker.check(data)
            except ValidationFieldException as e:
                new_msg = f"{context_info}: {e}"
                raise ValidationFieldException(new_msg, field=e.field) from e

    def _checkParams(self, ctx: Context, params: Dict[str, Any]) -> None:
        """Проверяет входные параметры с помощью чекеров, собранных с класса."""
        checkers = getattr(self.__class__, "_field_checkers", [])
        self._apply_checkers(checkers, params, "При проверке входных параметров")

    def _checkResults(self, method: Callable, result: Dict[str, Any]) -> None:
        """Проверяет результат выполнения метода с помощью чекеров, привязанных к этому методу."""
        checkers = getattr(method, '_result_checkers', [])
        method_name = method.__name__
        self._apply_checkers(checkers, result, f"При проверке результата метода {method_name}")

    def _permissionAuthorizationAspect(self, ctx: Context, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Аспект авторизации. Проверяет права доступа.
        По умолчанию возвращает пустой словарь.
        """
        self._checkRole(ctx)
        return {}

    def _validationAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Аспект валидации. Проверяет входные параметры.
        По умолчанию возвращает переданный result без изменений.
        """
        self._checkParams(ctx, params)
        return result

    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Аспект предварительной обработки.
        Может быть переопределён для подготовки данных перед основной логикой.
        По умолчанию возвращает result без изменений.
        """
        return result

    @abstractmethod
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Аспект основной бизнес-логики.
        Должен быть переопределён в наследнике. Получает текущий result и возвращает (возможно, модифицированный) словарь.
        """
        pass

    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Аспект пост-обработки. Может модифицировать result.
        По умолчанию возвращает result без изменений.
        """
        return result

    def run(self, ctx: Context, params: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(ctx, Context):
            raise TypeError(f"Ожидался объект Context, получен {type(ctx).__name__}")
        if not isinstance(params, dict):
            raise TypeError(f"Параметры должны быть словарём, получен {type(params).__name__}")

        result: Dict[str, Any] = {}

        try:
            # Аспект авторизации
            auth_result = self._permissionAuthorizationAspect(ctx, params)
            if not isinstance(auth_result, dict):
                raise TypeError(f"Аспект {self._permissionAuthorizationAspect.__name__} должен возвращать dict")
            self._checkResults(self._permissionAuthorizationAspect, auth_result)
            result.update(auth_result)

            # Аспект валидации
            validation_result = self._validationAspect(ctx, params, result)
            if not isinstance(validation_result, dict):
                raise TypeError(f"Аспект {self._validationAspect.__name__} должен возвращать dict")
            self._checkResults(self._validationAspect, validation_result)
            result.update(validation_result)

            # Аспект предварительной обработки
            pre_result = self._preHandleAspect(ctx, params, result)
            if not isinstance(pre_result, dict):
                raise TypeError(f"Аспект {self._preHandleAspect.__name__} должен возвращать dict")
            self._checkResults(self._preHandleAspect, pre_result)
            result.update(pre_result)

            # Основной аспект
            handle_result = self._handleAspect(ctx, params, result)
            if not isinstance(handle_result, dict):
                raise TypeError(f"Аспект {self._handleAspect.__name__} должен возвращать dict")
            self._checkResults(self._handleAspect, handle_result)
            result.update(handle_result)

            # Пост-обработка
            post_result = self._postHandleAspect(ctx, params, result)
            if not isinstance(post_result, dict):
                raise TypeError(f"Аспект {self._postHandleAspect.__name__} должен возвращать dict")
            self._checkResults(self._postHandleAspect, post_result)
            result.update(post_result)

            return result
        except Exception as e:
            # Вызываем аспект ошибки и пробрасываем исключение дальше
            self._onErrorAspect(ctx, params, result, e)
            raise
    
    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        """
        Аспект, вызываемый при возникновении исключения в ходе выполнения run().
        Позволяет выполнить очистку (например, откат транзакций) перед пробросом ошибки.
        По умолчанию ничего не делает.
        """
        pass