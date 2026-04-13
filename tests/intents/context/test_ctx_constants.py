# tests/intents/context/test_ctx_constants.py
"""
Тесты констант Ctx — проверка соответствия строковых путей
реальным полям UserInfo, RequestInfo, RuntimeInfo.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Константы Ctx — строки dot-path, соответствующие реальным полям
компонентов контекста. Используются в декораторе @context_requires
для декларации доступа к полям контекста из аспектов и обработчиков
ошибок.

Каждая константа строго соответствует реальному полю класса:
    Ctx.User.user_id    == "user.user_id"     → UserInfo.user_id
    Ctx.Request.trace_id == "request.trace_id" → RequestInfo.trace_id
    Ctx.Runtime.hostname == "runtime.hostname" → RuntimeInfo.hostname

UserInfo, RequestInfo, RuntimeInfo не имеют полей extra и tags
(extra="forbid"). Расширение — только через наследование с явно
объявленными полями. Для кастомных полей наследников используются
строковые пути напрямую:

    @context_requires(Ctx.User.user_id, "user.billing_plan")

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Ctx.User:
    - user_id, roles — соответствие реальным полям UserInfo.
    - Все константы — строки с префиксом "user.".

Ctx.Request:
    - trace_id, request_timestamp, request_path, request_method,
      full_url, client_ip, protocol, user_agent — соответствие
      реальным полям RequestInfo.
    - Все константы — строки с префиксом "request.".

Ctx.Runtime:
    - hostname, service_name, service_version, container_id, pod_name —
      соответствие реальным полям RuntimeInfo.
    - Все константы — строки с префиксом "runtime.".

Структура Ctx:
    - Три группы: User, Request, Runtime.
    - Константы совместимы с frozenset и строковыми путями.
"""

from action_machine.intents.context.ctx_constants import Ctx

# ═════════════════════════════════════════════════════════════════════════════
# Ctx.User — поля UserInfo
# ═════════════════════════════════════════════════════════════════════════════


class TestUserFields:
    """Константы Ctx.User соответствуют полям UserInfo."""

    def test_user_id_path(self) -> None:
        """Ctx.User.user_id → "user.user_id" (UserInfo.user_id)."""
        # Arrange — константа Ctx.User.user_id
        # Act / Assert — значение совпадает с dot-path навигации Context
        assert Ctx.User.user_id == "user.user_id"

    def test_roles_path(self) -> None:
        """Ctx.User.roles → "user.roles" (UserInfo.roles)."""
        # Arrange — константа Ctx.User.roles
        # Act / Assert — значение совпадает с dot-path навигации Context
        assert Ctx.User.roles == "user.roles"

    def test_all_are_strings(self) -> None:
        """Все константы Ctx.User имеют тип str."""
        # Arrange — все константы Ctx.User
        fields = [Ctx.User.user_id, Ctx.User.roles]

        # Act / Assert — каждая константа имеет тип str
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_user_prefix(self) -> None:
        """Все константы Ctx.User начинаются с "user."."""
        # Arrange — все константы Ctx.User
        fields = [Ctx.User.user_id, Ctx.User.roles]

        # Act / Assert — каждая константа начинается с "user."
        for field in fields:
            assert field.startswith("user.")


# ═════════════════════════════════════════════════════════════════════════════
# Ctx.Request — поля RequestInfo
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestFields:
    """Константы Ctx.Request соответствуют полям RequestInfo."""

    def test_trace_id_path(self) -> None:
        """Ctx.Request.trace_id → "request.trace_id"."""
        # Arrange / Act / Assert — соответствие реальному полю RequestInfo
        assert Ctx.Request.trace_id == "request.trace_id"

    def test_request_timestamp_path(self) -> None:
        """Ctx.Request.request_timestamp → "request.request_timestamp"."""
        # Arrange / Act / Assert
        assert Ctx.Request.request_timestamp == "request.request_timestamp"

    def test_request_path_path(self) -> None:
        """Ctx.Request.request_path → "request.request_path"."""
        # Arrange / Act / Assert
        assert Ctx.Request.request_path == "request.request_path"

    def test_request_method_path(self) -> None:
        """Ctx.Request.request_method → "request.request_method"."""
        # Arrange / Act / Assert
        assert Ctx.Request.request_method == "request.request_method"

    def test_full_url_path(self) -> None:
        """Ctx.Request.full_url → "request.full_url"."""
        # Arrange / Act / Assert
        assert Ctx.Request.full_url == "request.full_url"

    def test_client_ip_path(self) -> None:
        """Ctx.Request.client_ip → "request.client_ip"."""
        # Arrange / Act / Assert
        assert Ctx.Request.client_ip == "request.client_ip"

    def test_protocol_path(self) -> None:
        """Ctx.Request.protocol → "request.protocol"."""
        # Arrange / Act / Assert
        assert Ctx.Request.protocol == "request.protocol"

    def test_user_agent_path(self) -> None:
        """Ctx.Request.user_agent → "request.user_agent"."""
        # Arrange / Act / Assert
        assert Ctx.Request.user_agent == "request.user_agent"

    def test_all_are_strings(self) -> None:
        """Все константы Ctx.Request имеют тип str."""
        # Arrange — все константы Ctx.Request
        fields = [
            Ctx.Request.trace_id, Ctx.Request.request_timestamp,
            Ctx.Request.request_path, Ctx.Request.request_method,
            Ctx.Request.full_url, Ctx.Request.client_ip,
            Ctx.Request.protocol, Ctx.Request.user_agent,
        ]

        # Act / Assert — каждая константа имеет тип str
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_request_prefix(self) -> None:
        """Все константы Ctx.Request начинаются с "request."."""
        # Arrange — все константы Ctx.Request
        fields = [
            Ctx.Request.trace_id, Ctx.Request.request_timestamp,
            Ctx.Request.request_path, Ctx.Request.request_method,
            Ctx.Request.full_url, Ctx.Request.client_ip,
            Ctx.Request.protocol, Ctx.Request.user_agent,
        ]

        # Act / Assert — каждая константа начинается с "request."
        for field in fields:
            assert field.startswith("request.")


# ═════════════════════════════════════════════════════════════════════════════
# Ctx.Runtime — поля RuntimeInfo
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeFields:
    """Константы Ctx.Runtime соответствуют полям RuntimeInfo."""

    def test_hostname_path(self) -> None:
        """Ctx.Runtime.hostname → "runtime.hostname"."""
        # Arrange / Act / Assert — соответствие реальному полю RuntimeInfo
        assert Ctx.Runtime.hostname == "runtime.hostname"

    def test_service_name_path(self) -> None:
        """Ctx.Runtime.service_name → "runtime.service_name"."""
        # Arrange / Act / Assert
        assert Ctx.Runtime.service_name == "runtime.service_name"

    def test_service_version_path(self) -> None:
        """Ctx.Runtime.service_version → "runtime.service_version"."""
        # Arrange / Act / Assert
        assert Ctx.Runtime.service_version == "runtime.service_version"

    def test_container_id_path(self) -> None:
        """Ctx.Runtime.container_id → "runtime.container_id"."""
        # Arrange / Act / Assert
        assert Ctx.Runtime.container_id == "runtime.container_id"

    def test_pod_name_path(self) -> None:
        """Ctx.Runtime.pod_name → "runtime.pod_name"."""
        # Arrange / Act / Assert
        assert Ctx.Runtime.pod_name == "runtime.pod_name"

    def test_all_are_strings(self) -> None:
        """Все константы Ctx.Runtime имеют тип str."""
        # Arrange — все константы Ctx.Runtime
        fields = [
            Ctx.Runtime.hostname, Ctx.Runtime.service_name,
            Ctx.Runtime.service_version, Ctx.Runtime.container_id,
            Ctx.Runtime.pod_name,
        ]

        # Act / Assert — каждая константа имеет тип str
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_runtime_prefix(self) -> None:
        """Все константы Ctx.Runtime начинаются с "runtime."."""
        # Arrange — все константы Ctx.Runtime
        fields = [
            Ctx.Runtime.hostname, Ctx.Runtime.service_name,
            Ctx.Runtime.service_version, Ctx.Runtime.container_id,
            Ctx.Runtime.pod_name,
        ]

        # Act / Assert — каждая константа начинается с "runtime."
        for field in fields:
            assert field.startswith("runtime.")


# ═════════════════════════════════════════════════════════════════════════════
# Верхнеуровневая структура Ctx
# ═════════════════════════════════════════════════════════════════════════════


class TestCtxStructure:
    """Верхнеуровневая структура Ctx содержит три группы полей."""

    def test_user_group_exists(self) -> None:
        """Ctx.User доступен как атрибут."""
        # Arrange / Act / Assert — Ctx.User доступен как атрибут
        assert hasattr(Ctx, "User")

    def test_request_group_exists(self) -> None:
        """Ctx.Request доступен как атрибут."""
        # Arrange / Act / Assert — Ctx.Request доступен как атрибут
        assert hasattr(Ctx, "Request")

    def test_runtime_group_exists(self) -> None:
        """Ctx.Runtime доступен как атрибут."""
        # Arrange / Act / Assert — Ctx.Runtime доступен как атрибут
        assert hasattr(Ctx, "Runtime")

    def test_constants_usable_as_plain_strings(self) -> None:
        """
        Константы Ctx совместимы со строковыми путями в frozenset.

        Можно смешивать константы и строки для кастомных полей
        наследников: @context_requires(Ctx.User.user_id, "user.billing_plan").
        """
        # Arrange — константа Ctx смешивается со строковым путём
        keys = [Ctx.User.user_id, "user.billing_plan"]

        # Act / Assert — оба элемента — строки, пригодные для frozenset
        result = frozenset(keys)
        assert len(result) == 2
        assert "user.user_id" in result
        assert "user.billing_plan" in result
