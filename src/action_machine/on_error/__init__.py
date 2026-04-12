# src/action_machine/on_error/__init__.py
"""
Пакет обработки ошибок аспектов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит механизм обработки неперехваченных исключений в аспектах Action
с возможностью подмены результата. Когда regular- или summary-аспект
бросает исключение, машина ищет подходящий обработчик @on_error
по типу исключения и вызывает его.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- OnErrorIntent — маркерный миксин, обозначающий поддержку декоратора
  @on_error. Наследуется BaseAction. Класс без OnErrorIntent в MRO
  не может содержать методы с @on_error — MetadataBuilder выбросит
  TypeError при сборке метаданных.

- on_error — декоратор уровня метода. Принимает один тип исключения
  или кортеж типов и обязательное описание (description). Записывает
  метаданные в атрибут method._on_error_meta. Typed-снимок формирует
  OnErrorIntentInspector; чтение снимка — ``get_snapshot(cls, \"error_handler\")``.

═══════════════════════════════════════════════════════════════════════════════
МЕХАНИЗМ РАБОТЫ
═══════════════════════════════════════════════════════════════════════════════

    1. Аспект бросает исключение (например, ValueError).
    2. ActionProductMachine останавливает конвейер аспектов.
    3. Машина проходит по error_handlers сверху вниз (в порядке объявления).
    4. Первый обработчик, чей exception_types совпадает (isinstance),
       вызывается с параметрами (self, params, state, box, connections, error).
    5. Если обработчик возвращает Result — ошибка обработана, Result подменяет
       результат действия.
    6. Если обработчик бросает исключение — оно оборачивается
       в OnErrorHandlerError и пробрасывается наружу.
    7. Если ни один обработчик не подошёл — исходное исключение
       летит дальше как необработанное.

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

- Обработчики НЕ наследуются от родительского Action.
- Имя метода обязано заканчиваться на "_on_error".
- Description обязателен (непустая строка).
- Сигнатура: (self, params, state, box, connections, error) — 6 параметров.
- Метод обязан быть асинхронным (async def).
- Нижестоящий обработчик не может перехватывать типы, совпадающие
  или дочерние к типам вышестоящего (защита от мёртвого кода).
- State не модифицируется обработчиком.
- Rollup не влияет на обработку ошибок.

═══════════════════════════════════════════════════════════════════════════════
ПОРЯДОК ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Обработчики проверяются в порядке объявления в классе (сверху вниз).
Правильный порядок: сначала специфичные типы, потом общие.

    Допустимо:
        @on_error(ValueError, description="...")     ← специфичный
        @on_error(Exception, description="...")      ← общий fallback

    Недопустимо (TypeError при сборке метаданных):
        @on_error(Exception, description="...")      ← общий перехватит всё
        @on_error(ValueError, description="...")     ← мёртвый код

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.on_error import on_error

    @meta(description="Создание заказа", domain=OrdersDomain)
    @check_roles(NoneRole)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация")
        async def validate_aspect(self, params, state, box, connections):
            ...

        @summary_aspect("Результат")
        async def build_result_summary(self, params, state, box, connections):
            ...

        @on_error(ValueError, description="Ошибка валидации входных данных")
        async def validation_on_error(self, params, state, box, connections, error):
            return OrderResult(order_id="ERR", status="validation_error", total=0)

        @on_error(Exception, description="Непредвиденная ошибка")
        async def fallback_on_error(self, params, state, box, connections, error):
            return OrderResult(order_id="ERR", status="internal_error", total=0)
"""

from .on_error_decorator import on_error
from .on_error_intent import OnErrorIntent

__all__ = [
    "OnErrorIntent",
    "on_error",
]
