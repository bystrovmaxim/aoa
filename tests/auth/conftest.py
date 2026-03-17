"""
Фикстуры и моки для тестирования системы аутентификации.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.Context.user_info import user_info  # ← это класс

# ======================================================================
# МОКИ ДЛЯ ТЕСТОВ AUTH
# ======================================================================


class MockCredentialExtractor:
    """
    Мок экстрактора учётных данных.

    Позволяет задать возвращаемое значение или имитировать ошибку.
    """

    def __init__(self, return_value=None):
        self.return_value = return_value or {}
        self.extract = AsyncMock(return_value=self.return_value)
        self.call_count = 0


class MockAuthenticator:
    """
    Мок аутентификатора.

    Позволяет задать возвращаемого пользователя или имитировать ошибку.
    """

    def __init__(self, return_value=None):
        self.return_value = return_value
        self.authenticate = AsyncMock(return_value=self.return_value)
        self.call_count = 0


class MockContextAssembler:
    """
    Мок сборщика контекста.

    По умолчанию возвращает пустой словарь, как в исходных тестах.
    """

    def __init__(self, return_value=None):
        self.return_value = return_value if return_value is not None else {}
        self.assemble = AsyncMock(return_value=self.return_value)
        self.call_count = 0


# ======================================================================
# ТЕСТОВЫЕ ДЕЙСТВИЯ ДЛЯ ПРОВЕРКИ РОЛЕЙ
# ======================================================================


class SampleActionBase:
    """Базовый класс для тестовых действий."""

    x = 42


# ======================================================================
# ФИКСТУРЫ
# ======================================================================


@pytest.fixture
def user_info_fixture():  # ← ИЗМЕНЕНО: переименовали фикстуру
    """Базовая информация о пользователе."""
    return user_info(user_id="test_user", roles=["user"])  # ← вызываем класс


@pytest.fixture
def admin_info_fixture():  # ← ИЗМЕНЕНО
    """Информация о пользователе с правами админа."""
    return user_info(user_id="admin_user", roles=["user", "admin"])


@pytest.fixture
def guest_info_fixture():  # ← ИЗМЕНЕНО
    """Информация о госте (без ролей)."""
    return user_info(user_id="guest", roles=[])


@pytest.fixture
def mock_extractor():
    """Мок экстрактора с возвратом по умолчанию."""
    return MockCredentialExtractor()


@pytest.fixture
def mock_authenticator(user_info_fixture):  # ← ИЗМЕНЕНО: используем новое имя фикстуры
    """Мок аутентификатора с возвратом пользователя."""
    return MockAuthenticator(return_value=user_info_fixture)


@pytest.fixture
def mock_assembler():
    """Мок сборщика контекста с пустым возвратом."""
    return MockContextAssembler(return_value={})
