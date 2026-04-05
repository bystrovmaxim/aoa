# tests/context/test_ctx_constants.py
"""
Тесты констант Ctx — проверка соответствия строковых путей
реальным полям dataclass'ов UserInfo, RequestInfo, RuntimeInfo.
"""

from action_machine.context.ctx_constants import Ctx


class TestUserFields:
    """Константы Ctx.User соответствуют полям UserInfo."""

    def test_user_id_path(self) -> None:
        # Arrange — константа Ctx.User.user_id
        # Act / Assert — значение совпадает с dot-path навигации Context
        assert Ctx.User.user_id == "user.user_id"

    def test_roles_path(self) -> None:
        # Arrange — константа Ctx.User.roles
        # Act / Assert — значение совпадает с dot-path навигации Context
        assert Ctx.User.roles == "user.roles"

    def test_extra_path(self) -> None:
        # Arrange — константа Ctx.User.extra
        # Act / Assert — значение совпадает с dot-path навигации Context
        assert Ctx.User.extra == "user.extra"

    def test_all_are_strings(self) -> None:
        # Arrange — все константы Ctx.User
        fields = [Ctx.User.user_id, Ctx.User.roles, Ctx.User.extra]

        # Act / Assert — каждая константа имеет тип str
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_user_prefix(self) -> None:
        # Arrange — все константы Ctx.User
        fields = [Ctx.User.user_id, Ctx.User.roles, Ctx.User.extra]

        # Act / Assert — каждая константа начинается с "user."
        for field in fields:
            assert field.startswith("user.")


class TestRequestFields:
    """Константы Ctx.Request соответствуют полям RequestInfo."""

    def test_trace_id_path(self) -> None:
        # Arrange / Act / Assert — соответствие реальному полю RequestInfo
        assert Ctx.Request.trace_id == "request.trace_id"

    def test_request_timestamp_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.request_timestamp == "request.request_timestamp"

    def test_request_path_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.request_path == "request.request_path"

    def test_request_method_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.request_method == "request.request_method"

    def test_full_url_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.full_url == "request.full_url"

    def test_client_ip_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.client_ip == "request.client_ip"

    def test_protocol_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.protocol == "request.protocol"

    def test_user_agent_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.user_agent == "request.user_agent"

    def test_extra_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.extra == "request.extra"

    def test_tags_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Request.tags == "request.tags"

    def test_all_are_strings(self) -> None:
        # Arrange — все константы Ctx.Request
        fields = [
            Ctx.Request.trace_id, Ctx.Request.request_timestamp,
            Ctx.Request.request_path, Ctx.Request.request_method,
            Ctx.Request.full_url, Ctx.Request.client_ip,
            Ctx.Request.protocol, Ctx.Request.user_agent,
            Ctx.Request.extra, Ctx.Request.tags,
        ]

        # Act / Assert — каждая константа имеет тип str
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_request_prefix(self) -> None:
        # Arrange — все константы Ctx.Request
        fields = [
            Ctx.Request.trace_id, Ctx.Request.request_timestamp,
            Ctx.Request.request_path, Ctx.Request.request_method,
            Ctx.Request.full_url, Ctx.Request.client_ip,
            Ctx.Request.protocol, Ctx.Request.user_agent,
            Ctx.Request.extra, Ctx.Request.tags,
        ]

        # Act / Assert — каждая константа начинается с "request."
        for field in fields:
            assert field.startswith("request.")


class TestRuntimeFields:
    """Константы Ctx.Runtime соответствуют полям RuntimeInfo."""

    def test_hostname_path(self) -> None:
        # Arrange / Act / Assert — соответствие реальному полю RuntimeInfo
        assert Ctx.Runtime.hostname == "runtime.hostname"

    def test_service_name_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Runtime.service_name == "runtime.service_name"

    def test_service_version_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Runtime.service_version == "runtime.service_version"

    def test_container_id_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Runtime.container_id == "runtime.container_id"

    def test_pod_name_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Runtime.pod_name == "runtime.pod_name"

    def test_extra_path(self) -> None:
        # Arrange / Act / Assert
        assert Ctx.Runtime.extra == "runtime.extra"

    def test_all_are_strings(self) -> None:
        # Arrange — все константы Ctx.Runtime
        fields = [
            Ctx.Runtime.hostname, Ctx.Runtime.service_name,
            Ctx.Runtime.service_version, Ctx.Runtime.container_id,
            Ctx.Runtime.pod_name, Ctx.Runtime.extra,
        ]

        # Act / Assert — каждая константа имеет тип str
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_runtime_prefix(self) -> None:
        # Arrange — все константы Ctx.Runtime
        fields = [
            Ctx.Runtime.hostname, Ctx.Runtime.service_name,
            Ctx.Runtime.service_version, Ctx.Runtime.container_id,
            Ctx.Runtime.pod_name, Ctx.Runtime.extra,
        ]

        # Act / Assert — каждая константа начинается с "runtime."
        for field in fields:
            assert field.startswith("runtime.")


class TestCtxStructure:
    """Верхнеуровневая структура Ctx содержит три группы полей."""

    def test_user_group_exists(self) -> None:
        # Arrange / Act / Assert — Ctx.User доступен как атрибут
        assert hasattr(Ctx, "User")

    def test_request_group_exists(self) -> None:
        # Arrange / Act / Assert — Ctx.Request доступен как атрибут
        assert hasattr(Ctx, "Request")

    def test_runtime_group_exists(self) -> None:
        # Arrange / Act / Assert — Ctx.Runtime доступен как атрибут
        assert hasattr(Ctx, "Runtime")

    def test_constants_usable_as_plain_strings(self) -> None:
        # Arrange — константа Ctx смешивается со строковым путём
        keys = [Ctx.User.user_id, "user.extra.billing_plan"]

        # Act / Assert — оба элемента — строки, пригодные для frozenset
        result = frozenset(keys)
        assert len(result) == 2
        assert "user.user_id" in result
        assert "user.extra.billing_plan" in result
