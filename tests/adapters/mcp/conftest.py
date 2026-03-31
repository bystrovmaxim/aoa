# tests/adapters/mcp/conftest.py
"""
Конфигурация pytest для тестов MCP-адаптера.

Пропускает тесты, требующие библиотеку ``mcp``, если она не установлена.
McpRouteRecord не зависит от ``mcp`` и тестируется всегда.
"""

import pytest

# Проверяем наличие библиотеки mcp один раз при загрузке модуля.
# Тесты, требующие mcp, помечаются через фикстуру require_mcp.
try:
    import mcp  # noqa: F401
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@pytest.fixture(autouse=False)
def require_mcp():
    """Фикстура для пропуска тестов, если библиотека mcp не установлена."""
    if not MCP_AVAILABLE:
        pytest.skip("mcp not installed: pip install action-machine[mcp]")
