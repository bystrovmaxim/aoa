# src/examples/fastapi_mcp_services/infrastructure.py
"""
Общая инфраструктура ActionMachine для FastAPI и MCP сервисов.

Координатор, машина и провайдер аутентификации создаются один раз
и используются обоими адаптерами. Это гарантирует, что оба транспорта
работают с одним графом метаданных и одними настройками.

NoAuthCoordinator явно декларирует, что этот пример не требует
аутентификации. Для production скопируйте не вслепую: подключите свой
AuthCoordinator с реальными CredentialExtractor, Authenticator и
ContextAssembler. NoAuthCoordinator оставляйте только если API намеренно
открытый.
"""

from action_machine.auth import NoAuthCoordinator
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.metadata.gate_coordinator import GateCoordinator

coordinator = GateCoordinator()
machine = ActionProductMachine(mode="production")
auth = NoAuthCoordinator()
