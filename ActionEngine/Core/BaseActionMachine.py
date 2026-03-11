# ============================================================
# ActionEngine Core (минимум для работы тестов)
# ============================================================
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Dict, List, Optional, Tuple, Callable, Type, Protocol, runtime_checkable, cast
import inspect

# ---------- Контекст ----------
class Context:
    """Глобальный контекст выполнения (пользователь, запрос, окружение)."""
    pass

# ---------- Базовые классы ----------
class BaseParams(ABC):
    """Входные параметры действия (иммутабельны)."""
    pass

class BaseResult(ABC):
    """Результат выполнения действия."""
    pass

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)

# ---------- Протокол для аспект-методов ----------
@runtime_checkable
class AspectMethod(Protocol):
    """Протокол, описывающий методы, помеченные декораторами aspect/summary_aspect."""
    _is_aspect: bool
    _aspect_description: str
    _aspect_type: str  # 'regular' или 'summary'
    __code__: Any
    __qualname__: str
    __call__: Callable[..., Any]

# ---------- Декораторы аспектов ----------
def aspect(description: str) -> Callable[[Callable], AspectMethod]:
    """Декоратор для обычных аспектов."""
    def decorator(method: Callable) -> AspectMethod:
        method._is_aspect = True          # type: ignore
        method._aspect_description = description  # type: ignore
        method._aspect_type = 'regular'    # type: ignore
        return method                     # type: ignore
    return decorator

def summary_aspect(description: str) -> Callable[[Callable], AspectMethod]:
    """Декоратор для главного аспекта (должен быть ровно один)."""
    def decorator(method: Callable) -> AspectMethod:
        method._is_aspect = True          # type: ignore
        method._aspect_description = description  # type: ignore
        method._aspect_type = 'summary'    # type: ignore
        return method                     # type: ignore
    return decorator

# ---------- Декоратор зависимостей ----------
def depends(klass: Type, *, description: str = "", factory: Optional[Callable[[], Any]] = None):
    """
    Декоратор для объявления зависимости действия от любого класса.
    Аргументы:
        klass: класс зависимости (может быть Action, сервис, репозиторий и т.д.)
        description: описание зависимости (для документации).
        factory: опциональная фабрика для создания экземпляра.
                 Если не указана, используется конструктор по умолчанию.
    """
    def decorator(cls):
        if not hasattr(cls, '_dependencies'):
            cls._dependencies = []
        cls._dependencies.append({
            'class': klass,
            'description': description,
            'factory': factory
        })
        return cls
    return decorator

# ---------- Базовое действие ----------
class BaseAction(Generic[P, R], ABC):
    """
    Базовый класс для всех действий.
    Наследники определяют свои аспекты с помощью декораторов.
    Действия не имеют состояния – все данные передаются через params и data.
    """
    pass

# ---------- Фабрика зависимостей ----------
class DependencyFactory:
    """
    Фабрика, предоставляющая доступ к зависимостям, объявленным через @depends.
    Экземпляр создаётся машиной для каждого действия и кэшируется.
    """
    def __init__(self, machine: 'BaseActionMachine', deps_info: List[Dict]):
        self._machine = machine
        self._deps = {info['class']: info for info in deps_info}

    def get(self, klass: Type) -> Any:
        """Возвращает экземпляр зависимости (создаёт при необходимости)."""
        if klass not in self._deps:
            raise ValueError(f"Dependency {klass.__name__} not declared in @depends")
        info = self._deps[klass]
        if info['factory']:
            return info['factory']()
        # Простейшее создание через конструктор без аргументов
        return klass()

    def run_action(self, action_class: Type['BaseAction'], params: BaseParams) -> BaseResult:
        """Удобный метод для создания и запуска дочернего действия через машину."""
        instance = self.get(action_class)
        # Используем машину, которая создала эту фабрику, для выполнения действия
        return self._machine.run(instance, params)   # type: ignore

# ---------- Базовая машина действий ----------
class BaseActionMachine(ABC):
    def __init__(self, context: Context):
        self._context = context
        self._aspect_cache: Dict[Type, Tuple[List[Tuple[AspectMethod, str]], AspectMethod]] = {}
        self._factory_cache: Dict[Type, DependencyFactory] = {}

    def _get_aspects(self, action_class: Type) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        """Возвращает (список обычных аспектов, summary-аспект) для класса действия."""
        if action_class not in self._aspect_cache:
            aspects, summary = self._collect_aspects(action_class)
            self._aspect_cache[action_class] = (aspects, summary)
        return self._aspect_cache[action_class]

    def _collect_aspects(self, action_class: Type) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
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

    def _get_factory(self, action_class: Type) -> DependencyFactory:
        """Возвращает (и кэширует) фабрику зависимостей для класса действия."""
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, '_dependencies', [])
            self._factory_cache[action_class] = DependencyFactory(self, deps_info)
        return self._factory_cache[action_class]

    def run(self, action: BaseAction[P, R], params: P) -> R:
        """Запускает действие, вызывая аспекты в нужном порядке."""
        action_class = action.__class__
        aspects, summary_method = self._get_aspects(action_class)
        factory = self._get_factory(action_class)

        data: Dict[str, Any] = {}

        for method, description in aspects:
            data = method(action, params, data, factory)

        result = summary_method(action, params, data, factory)
        return result


# ============================================================
# Тестовые утилиты
# ============================================================

class MockAction(BaseAction):
    """
    Универсальный мок для действий.
    При вызове run возвращает предопределённый результат или вызывает переданную функцию.
    """
    def __init__(self, result: Optional[BaseResult] = None, side_effect: Optional[Callable] = None):
        self.result = result
        self.side_effect = side_effect
        self.call_count: int = 0
        self.last_params: Optional[BaseParams] = None

    def run(self, params: BaseParams) -> BaseResult:
        self.call_count += 1
        self.last_params = params
        if self.side_effect:
            return self.side_effect(params)
        if self.result is None:
            raise ValueError("MockAction: neither result nor side_effect provided")
        return self.result


class ActionTestMachine(BaseActionMachine):
    """
    Тестовая машина с удобным API для подмены зависимостей.
    Принимает в конструкторе словарь моков: {класс: значение}
    Значение может быть:
      - экземпляром действия (будет использован как есть)
      - результатом (будет обёрнут в MockAction)
      - функцией (будет использована как side_effect для MockAction)
      - любым другим объектом (будет возвращён как есть)
    """
    def __init__(self, mocks: Optional[Dict[Type, Any]] = None, context: Optional[Context] = None):
        super().__init__(context or Context())
        self._mocks = mocks or {}
        # Маппинг оригинальный класс → подготовленный мок
        self._prepared_mocks: Dict[Type, Any] = {}
        for cls, val in self._mocks.items():
            self._prepared_mocks[cls] = self._prepare_mock(val)

    def _prepare_mock(self, value):
        """Преобразует переданное значение в объект, пригодный для использования."""
        if isinstance(value, MockAction):
            return value
        if isinstance(value, BaseAction):
            return value
        if callable(value):
            return MockAction(side_effect=value)
        if isinstance(value, BaseResult):
            return MockAction(result=value)
        return value

    def run(self, action: BaseAction[P, R], params: P) -> R:
        """
        Переопределяем run: если action — это MockAction,
        вызываем его напрямую, минуя аспектный конвейер.
        """
        if isinstance(action, MockAction):
            return action.run(params)  # type: ignore
        return super().run(action, params)

    def _build_factory(self, action_class: Type) -> DependencyFactory:
        deps_info = getattr(action_class, '_dependencies', [])
        prepared = self._prepared_mocks

        class TestDependencyFactory(DependencyFactory):
            def __init__(self, machine, deps_info, prepared_mocks):
                super().__init__(machine, deps_info)
                self._prepared_mocks = prepared_mocks

            def get(self, klass: Type) -> Any:
                if klass in self._prepared_mocks:
                    return self._prepared_mocks[klass]
                return super().get(klass)

        return TestDependencyFactory(self, deps_info, prepared)

    def _get_factory(self, action_class: Type) -> DependencyFactory:
        if action_class not in self._factory_cache:
            self._factory_cache[action_class] = self._build_factory(action_class)
        return self._factory_cache[action_class]

    def build_factory(self, action_class: Type) -> DependencyFactory:
        """Возвращает фабрику для использования в тестировании отдельных аспектов."""
        return self._get_factory(action_class)


# ============================================================
# Примеры действий и сервисов для тестирования
# ============================================================

# Сервисы (реальные, но для тестов мы будем подменять)
class EmailService:
    def send(self, to: str, msg: str):
        print(f"Sending email to {to}: {msg}")

class SmsService:
    def send(self, to: str, msg: str):
        print(f"Sending SMS to {to}: {msg}")

# Простое действие, использующее сервисы
@depends(EmailService, description="Сервис email")
@depends(SmsService, description="Сервис SMS")
class NotificationAction(BaseAction['NotificationAction.Params', 'NotificationAction.Result']):
    class Params(BaseParams):
        def __init__(self, channel: str, message: str, recipient: str):
            self.channel = channel
            self.message = message
            self.recipient = recipient

    class Result(BaseResult):
        def __init__(self, success: bool):
            self.success = success

    @aspect("Выбор канала")
    def choose_channel(self, params: Params, data: Dict[str, Any], deps: DependencyFactory) -> Dict[str, Any]:
        if params.channel == 'email':
            data['service'] = deps.get(EmailService)
        elif params.channel == 'sms':
            data['service'] = deps.get(SmsService)
        else:
            raise ValueError("Unknown channel")
        return data

    @summary_aspect("Отправка")
    def send(self, params: Params, data: Dict[str, Any], deps: DependencyFactory) -> Result:
        service = data['service']
        service.send(params.recipient, params.message)
        return NotificationAction.Result(True)

# Дочернее действие для тестирования родительского
class ChildAction(BaseAction['ChildAction.Params', 'ChildAction.Result']):
    class Params(BaseParams):
        def __init__(self, value: int):
            self.value = value

    class Result(BaseResult):
        def __init__(self, doubled: int):
            self.doubled = doubled

    @summary_aspect("Удвоить")
    def handle(self, params: Params, data: Dict[str, Any], deps: DependencyFactory) -> Result:
        return ChildAction.Result(params.value * 2)

# Родительское действие, использующее дочернее
@depends(ChildAction, description="Дочернее действие")
class ParentAction(BaseAction['ParentAction.Params', 'ParentAction.Result']):
    class Params(BaseParams):
        def __init__(self, num: int):
            self.num = num

    class Result(BaseResult):
        def __init__(self, result: int):
            self.result = result

    @summary_aspect("Родитель")
    def handle(self, params: Params, data: Dict[str, Any], deps: DependencyFactory) -> Result:
        child_result = deps.run_action(ChildAction, ChildAction.Params(params.num))
        # для mypy уточняем тип
        assert isinstance(child_result, ChildAction.Result)
        return ParentAction.Result(child_result.doubled + 10)


# ============================================================
# Примеры тестов (можно запустить с pytest)
# ============================================================
import pytest  # type: ignore

# ---------- Тесты для аспектов (с использованием build_factory) ----------

def test_choose_channel_aspect():
    # Создаём тестовую машину с моками для сервисов
    fake_email = object()
    fake_sms = object()
    machine = ActionTestMachine({
        EmailService: fake_email,
        SmsService: fake_sms
    })
    # Теперь build_factory требует класс действия
    factory = machine.build_factory(NotificationAction)

    action = NotificationAction()
    params = NotificationAction.Params(channel='email', message='hi', recipient='a@b.c')
    data = {}
    result_data = action.choose_channel(params, data, factory)

    assert result_data['service'] is fake_email

    # Тест для SMS
    params2 = NotificationAction.Params(channel='sms', message='hi', recipient='123')
    data2 = {}
    result_data2 = action.choose_channel(params2, data2, factory)
    assert result_data2['service'] is fake_sms

def test_choose_channel_aspect_unknown():
    fake_email = object()
    machine = ActionTestMachine({EmailService: fake_email})
    factory = machine.build_factory(NotificationAction)
    action = NotificationAction()
    params = NotificationAction.Params(channel='fax', message='hi', recipient='x')
    with pytest.raises(ValueError, match="Unknown channel"):
        action.choose_channel(params, {}, factory)


# ---------- Тесты для целого действия (с использованием run) ----------

def test_notification_action_with_mock_services():
    # Создаём тестовые объекты-заглушки, которые будут имитировать сервисы
    class FakeEmail:
        def __init__(self):
            self.sent = []

        def send(self, to, msg):
            self.sent.append((to, msg))

    fake_email = FakeEmail()
    fake_sms = FakeEmail()  # для простоты тоже FakeEmail

    machine = ActionTestMachine({
        EmailService: fake_email,
        SmsService: fake_sms
    })

    action = NotificationAction()
    params = NotificationAction.Params(channel='email', message='Hello', recipient='test@ex.com')
    result = machine.run(action, params)

    assert result.success is True
    assert fake_email.sent == [('test@ex.com', 'Hello')]
    assert fake_sms.sent == []


def test_parent_action_with_mock_child():
    # Случай 1: мокаем результат дочернего действия (фиксированный результат)
    machine = ActionTestMachine({
        ChildAction: ChildAction.Result(20)   # результат, который вернёт дочернее действие
    })

    action = ParentAction()
    params = ParentAction.Params(5)
    result = machine.run(action, params)

    assert result.result == 30   # 20 + 10

def test_parent_action_with_side_effect():
    # Случай 2: мокаем дочернее действие с side_effect (функция, зависящая от параметров)
    def child_side_effect(params):
        # params — это ChildAction.Params
        return ChildAction.Result(params.value * 3)  # вместо умножения на 2

    machine = ActionTestMachine({
        ChildAction: child_side_effect
    })

    action = ParentAction()
    params = ParentAction.Params(5)
    result = machine.run(action, params)

    assert result.result == 15 + 10 == 25   # 5*3=15 +10 =25

def test_parent_action_with_real_child():
    # Случай 3: реальное дочернее действие (без моков)
    machine = ActionTestMachine()   # пустые моки, используется реальное поведение
    action = ParentAction()
    params = ParentAction.Params(5)
    result = machine.run(action, params)

    assert result.result == 10 + 10 == 20   # 5*2=10 +10 =20

# ---------- Тест, демонстрирующий, что мок-действие запоминает вызовы ----------

def test_mock_action_call_tracking():
    mock_action = MockAction(result=ChildAction.Result(100))
    machine = ActionTestMachine({ChildAction: mock_action})

    action = ParentAction()
    params = ParentAction.Params(7)
    result = machine.run(action, params)

    assert result.result == 110
    assert mock_action.call_count == 1
    assert isinstance(mock_action.last_params, ChildAction.Params)
    assert mock_action.last_params.value == 7


# ============================================================
# Запуск тестов (если файл выполняется напрямую)
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])