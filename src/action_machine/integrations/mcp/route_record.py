# src/action_machine/integrations/mcp/route_record.py
"""
McpRouteRecord — frozen-датакласс маршрута для MCP-адаптера.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

McpRouteRecord — конкретный наследник BaseRouteRecord с MCP-специфичными
полями. Хранит полную конфигурацию одного MCP tool: имя инструмента,
описание, класс действия, модели маппинга. Используется McpAdapter
при build() для генерации MCP tools на MCP-сервере.

═══════════════════════════════════════════════════════════════════════════════
MCP-СПЕЦИФИЧНЫЕ ПОЛЯ
═══════════════════════════════════════════════════════════════════════════════

    tool_name : str
        Имя MCP tool, видимое AI-агенту. Непустая строка.
        Рекомендуемый формат: ``domain.action`` — например,
        ``orders.create``, ``orders.get``, ``system.ping``.
        Агент использует это имя для вызова инструмента.
        По умолчанию пустая строка (валидация требует непустое значение).

    description : str
        Описание tool для AI-агента. Отображается в списке доступных
        инструментов. Агент использует описание для принятия решения
        о вызове tool. Если пустая строка — McpAdapter подставит
        description из ``@meta`` действия.
        По умолчанию пустая строка.

═══════════════════════════════════════════════════════════════════════════════
НАСЛЕДОВАНИЕ ОТ BaseRouteRecord
═══════════════════════════════════════════════════════════════════════════════

Наследует от BaseRouteRecord все общие поля: action_class, request_model,
response_model, params_mapper, response_mapper. Наследует все инварианты:

- action_class должен быть подклассом BaseAction.
- params_type и result_type извлекаются автоматически из BaseAction[P, R].
- Если request_model указан и отличается от params_type — params_mapper
  обязателен.
- Если response_model указан и отличается от result_type — response_mapper
  обязателен.

В ``__post_init__`` выполняются MCP-специфичные проверки:

- tool_name непустой (после strip).

═══════════════════════════════════════════════════════════════════════════════
КОНВЕНЦИЯ ИМЕНОВАНИЯ МАППЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый маппер назван по тому, что он ВОЗВРАЩАЕТ:

    params_mapper   → возвращает params   (преобразует request → params)
    response_mapper → возвращает response (преобразует result  → response)

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР СОЗДАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Минимум:
    record = McpRouteRecord(
        action_class=CreateOrderAction,
        tool_name="orders.create",
    )

    # Полный набор:
    record = McpRouteRecord(
        action_class=CreateOrderAction,
        request_model=CreateOrderRequest,
        response_model=CreateOrderResponse,
        params_mapper=map_request_to_params,
        response_mapper=map_result_to_response,
        tool_name="orders.create",
        description="Создание нового заказа в системе",
    )
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.adapters.base_route_record import BaseRouteRecord


@dataclass(frozen=True)
class McpRouteRecord(BaseRouteRecord):
    """
    Frozen-датакласс маршрута для MCP-адаптера.

    Наследует BaseRouteRecord (action_class, request_model, response_model,
    params_mapper, response_mapper) и добавляет MCP-специфичные поля.

    Frozen — после создания ни одно поле изменить нельзя.

    Validation в ``__post_init__``:
    - Вызывает ``super().__post_init__()`` для проверки инвариантов
      BaseRouteRecord (action_class, маппинг, извлечение P и R).
    - Checks tool_name: непустой после strip.

    Атрибуты (MCP-специфичные поля):
        tool_name : str
            Имя MCP tool. Непустая строка. По умолчанию "".

        description : str
            Описание tool для AI-агента. По умолчанию "".
    """

    # ── MCP-специфичные поля ───────────────────────────────────────────

    tool_name: str = ""
    description: str = ""

    # ── Validation ──────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Checks MCP-специфичные инварианты после создания экземпляра.

        Порядок:

        1. Вызов ``super().__post_init__()`` — проверка инвариантов
           BaseRouteRecord (action_class, маппинг, извлечение P и R,
           запрет прямого создания BaseRouteRecord).

        2. Проверка tool_name: непустой после strip().

        Raises:
            TypeError: от BaseRouteRecord (action_class не BaseAction,
                       не удалось извлечь P и R).
            ValueError: от BaseRouteRecord (маппер отсутствует при
                        различающихся типах); tool_name пустой.
        """
        # ── 1. Инварианты BaseRouteRecord ──
        super().__post_init__()

        # ── 2. Проверка tool_name ──
        if not self.tool_name or not self.tool_name.strip():
            raise ValueError(
                "tool_name не может быть пустой строкой. "
                "Укажите имя инструмента, например 'orders.create'."
            )
