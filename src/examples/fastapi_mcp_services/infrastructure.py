# src/examples/fastapi_mcp_services/infrastructure.py
"""
Общая инфраструктура ActionMachine для FastAPI и MCP сервисов.

Координатор и машина создаются один раз и используются обоими адаптерами.
Это гарантирует, что оба транспорта работают с одним графом метаданных,
одним кешем фабрик и одними настройками.
"""

from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.gate_coordinator import GateCoordinator

coordinator = GateCoordinator()
machine = ActionProductMachine(mode="production", coordinator=coordinator)
