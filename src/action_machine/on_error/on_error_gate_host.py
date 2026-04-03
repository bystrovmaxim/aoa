# src/action_machine/on_error/on_error_gate_host.py
"""
Модуль: OnErrorGateHost — маркерный миксин для декоратора @on_error.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

OnErrorGateHost — миксин-маркер, обозначающий, что класс поддерживает
декоратор @on_error для объявления обработчиков неперехваченных исключений
в аспектах. Наследуется BaseAction.

Наличие OnErrorGateHost в MRO класса документирует контракт:
«этот класс может содержать методы-обработчики ошибок (@on_error)».

═══════════════════════════════════════════════════════════════════════════════
МЕХАНИЗМ ОБРАБОТКИ ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Когда regular-аспект или summary-аспект бросает исключение,
ActionProductMachine:

1. Останавливает выполнение конвейера аспектов.
2. Проходит по обработчикам @on_error сверху вниз (в порядке объявления).
3. Первый обработчик, чей тип исключения совпадает (isinstance), вызывается
   с параметрами (self, params, state, box, connections, error).
4. Если обработчик возвращает Result — ошибка считается обработанной,
   Result подменяет результат действия.
5. Если обработчик сам бросает исключение — оно оборачивается
   в OnErrorHandlerError с __cause__ и пробрасывается наружу.
6. Если ни один обработчик не подошёл — исходное исключение
   пробрасывается наружу как необработанное.

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

- Обработчики @on_error НЕ наследуются от родительского Action.
  Каждый Action объявляет свои обработчики явно.
- Имя метода с @on_error обязано заканчиваться на "_on_error".
- Метод обязан быть асинхронным (async def).
- Сигнатура: ровно 6 параметров (self, params, state, box, connections, error).
- Нижестоящий обработчик не может ловить типы исключений, совпадающие
  с типами вышестоящего или являющиеся их подклассами.
- State не модифицируется обработчиком — инвариант.
- Rollup не влияет на обработку ошибок.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaGateHost,
        RoleGateHost,
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,
        ConnectionGateHost,
        OnErrorGateHost,                ← маркер: разрешает @on_error
    ): ...

    @meta(description="Создание заказа", domain=OrdersDomain)
    @check_roles(ROLE_NONE)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация")
        async def validate_aspect(self, params, state, box, connections):
            ...

        @summary_aspect("Результат")
        async def build_result_summary(self, params, state, box, connections):
            ...

        @on_error(ValueError, description="Обработка ошибки валидации")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            return OrderResult(order_id="ERR", status="validation_failed", total=0)

    # Декоратор @on_error записывает в метод:
    #   method._on_error_meta = {
    #       "exception_types": (ValueError,),
    #       "description": "Обработка ошибки валидации",
    #   }
    #
    # MetadataBuilder собирает в ClassMetadata.error_handlers:
    #   (OnErrorMeta(method_name="handle_validation_on_error",
    #                exception_types=(ValueError,), description="...",
    #                method_ref=<func>),)
    #
    # ActionProductMachine при ошибке аспекта:
    #   1. Ищет первый подходящий обработчик по isinstance(error, exc_types).
    #   2. Вызывает handler(action, params, state, box, connections, error).
    #   3. Если вернул Result — подменяет результат.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    class PaymentAction(BaseAction[PayParams, PayResult]):

        @regular_aspect("Списание средств")
        async def charge_aspect(self, params, state, box, connections):
            ...

        @summary_aspect("Результат оплаты")
        async def result_summary(self, params, state, box, connections):
            ...

        @on_error(InsufficientFundsError, description="Недостаточно средств")
        async def insufficient_funds_on_error(self, params, state, box, connections, error):
            return PayResult(status="insufficient_funds", txn_id="")

        @on_error(PaymentGatewayError, description="Ошибка платёжного шлюза")
        async def gateway_error_on_error(self, params, state, box, connections, error):
            return PayResult(status="gateway_error", txn_id="")
"""

from typing import Any, ClassVar


class OnErrorGateHost:
    """
    Маркерный миксин, обозначающий поддержку декоратора @on_error.

    Класс, наследующий OnErrorGateHost, может содержать методы,
    декорированные @on_error для обработки неперехваченных исключений
    в аспектах. MetadataBuilder собирает эти методы в
    ClassMetadata.error_handlers (tuple[OnErrorMeta, ...]).

    Миксин не содержит логики, полей или методов. Его функция —
    документировать контракт и обеспечивать единообразие с другими
    гейт-миксинами (RoleGateHost, AspectGateHost, CheckerGateHost и др.).

    Атрибуты уровня класса (создаются динамически декоратором на методах):
        method._on_error_meta : dict
            Словарь {"exception_types": tuple[type, ...], "description": str},
            записываемый декоратором @on_error в сам метод. Читается
            MetadataBuilder при сборке ClassMetadata.error_handlers.
    """

    _on_error_meta: ClassVar[dict[str, Any]]
