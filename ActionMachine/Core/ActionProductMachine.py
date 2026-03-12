# ActionMachine/Core/ActionProductMachine.py
from typing import TypeVar, Any, Dict, List, Optional, Tuple, Type, cast, Callable
import inspect
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.DependencyFactory import DependencyFactory
from ActionMachine.Context.Context import Context
from ActionMachine.Core.AspectMethod import AspectMethod
from ActionMachine.Core.BaseActionMachine import BaseActionMachine
from ActionMachine.Core.Exceptions import ValidationFieldException, AuthorizationException
from ActionMachine.Auth.CheckRoles import CheckRoles

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)


class ActionProductMachine(BaseActionMachine):
    def __init__(self, context: Context) -> None:
        self._context = context
        self._aspect_cache: Dict[Type[Any], Tuple[List[Tuple[AspectMethod, str]], AspectMethod]] = {}
        self._factory_cache: Dict[Type[Any], DependencyFactory] = {}

    def _get_aspects(self, action_class: Type[Any]) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        if action_class not in self._aspect_cache:
            aspects, summary = self._collect_aspects(action_class)
            self._aspect_cache[action_class] = (aspects, summary)
        return self._aspect_cache[action_class]

    def _collect_aspects(self, action_class: Type[Any]) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        aspects: List[Tuple[AspectMethod, str]] = []
        summary_method: Optional[AspectMethod] = None

        for name, method in inspect.getmembers(action_class, predicate=inspect.isfunction):
            if method.__qualname__.split('.')[0] != action_class.__name__:
                continue
            if not hasattr(method, '_is_aspect') or not method._is_aspect:
                continue

            asp_method = cast(AspectMethod, method)
            if asp_method._aspect_type == 'regular':
                aspects.append((asp_method, asp_method._aspect_description))
            elif asp_method._aspect_type == 'summary':
                if summary_method is not None:
                    raise TypeError(f"Класс {action_class.__name__} имеет более одного summary_aspect")
                summary_method = asp_method
            else:
                raise TypeError(f"Неизвестный тип аспекта: {asp_method._aspect_type}")

        if summary_method is None:
            raise TypeError(f"Класс {action_class.__name__} не имеет summary_aspect")

        aspects.sort(key=lambda item: item[0].__code__.co_firstlineno)
        return aspects, summary_method

    def _get_factory(self, action_class: Type[Any]) -> DependencyFactory:
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, '_dependencies', [])
            self._factory_cache[action_class] = DependencyFactory(self, deps_info)
        return self._factory_cache[action_class]

    def _apply_checkers(self, method: Callable[..., Any], result: Dict[str, Any]) -> None:
        checkers = getattr(method, '_result_checkers', [])
        for checker in checkers:
            checker.check(result)

    def _check_action_roles(self, action: BaseAction[P, R]) -> None:
        """Проверяет, что действие имеет ролевую спецификацию и что текущий пользователь её удовлетворяет."""
        role_spec = getattr(action.__class__, '_role_spec', None)
        if role_spec is None:
            raise TypeError(
                f"Действие {action.__class__.__name__} не имеет декоратора CheckRoles. "
                "Укажите явно CheckRoles.NONE если действие доступно без аутентификации."
            )

        user_roles = self._context.user.roles

        if role_spec == CheckRoles.NONE:
            return
        if role_spec == CheckRoles.ANY:
            if not user_roles:
                raise AuthorizationException(
                    "Требуется аутентификация: пользователь должен иметь хотя бы одну роль"
                )
            return
        if isinstance(role_spec, list):
            if any(role in user_roles for role in role_spec):
                return
            raise AuthorizationException(
                f"Доступ запрещён. Требуется одна из ролей: {role_spec}, роли пользователя: {user_roles}"
            )
        if role_spec in user_roles:
            return
        raise AuthorizationException(
            f"Доступ запрещён. Требуется роль: '{role_spec}', роли пользователя: {user_roles}"
        )

    def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        factory: DependencyFactory
    ) -> Dict[str, Any]:
        """Выполняет цепочку регулярных аспектов, возвращая итоговое состояние."""
        action_class = action.__class__
        aspects, _ = self._get_aspects(action_class)  # summary нам пока не нужен
        state: Dict[str, Any] = {}

        for method, description in aspects:
            new_state = method(action, params, state, factory)
            if not isinstance(new_state, dict):
                raise TypeError(f"Аспект {method.__qualname__} должен возвращать dict, получен {type(new_state).__name__}")

            self._apply_checkers(method, new_state)

            checkers = getattr(method, '_result_checkers', [])
            if checkers:
                allowed_fields = {ch.field_name for ch in checkers}
                extra_fields = set(new_state.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldException(
                        f"Аспект {method.__qualname__} вернул лишние поля: {extra_fields}. "
                        f"Разрешены только: {allowed_fields}"
                    )

            state = new_state

        return state

    def run(self, action: BaseAction[P, R], params: P) -> R:
        # 1. Проверка ролей
        self._check_action_roles(action)

        # 2. Получение фабрики зависимостей
        action_class = action.__class__
        factory = self._get_factory(action_class)

        # 3. Выполнение регулярных аспектов
        state = self._execute_regular_aspects(action, params, factory)

        # 4. Выполнение summary-аспекта
        _, summary_method = self._get_aspects(action_class)
        result = summary_method(action, params, state, factory)
        return cast(R, result)