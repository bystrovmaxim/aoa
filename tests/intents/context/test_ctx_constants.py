# tests/intents/context/test_ctx_constants.py
"""
Tests for Ctx constants — string paths match UserInfo, RequestInfo, RuntimeInfo fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ctx constants are dot-path strings matching real fields on context components.
They are used with @context_requires to declare context field access from
aspects and error handlers.

Each constant maps to a real class field:
    Ctx.User.user_id    == "user.user_id"     → UserInfo.user_id
    Ctx.Request.trace_id == "request.trace_id" → RequestInfo.trace_id
    Ctx.Runtime.hostname == "runtime.hostname" → RuntimeInfo.hostname

UserInfo, RequestInfo, RuntimeInfo have no extra/tags (extra="forbid").
Extend only via subclasses with explicit fields. For subclass fields use
string paths directly:

    @context_requires(Ctx.User.user_id, "user.billing_plan")

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Ctx.User:
    - user_id, roles — match UserInfo fields.
    - All constants are strings with "user." prefix.

Ctx.Request:
    - trace_id, request_timestamp, request_path, request_method,
      full_url, client_ip, protocol, user_agent — match RequestInfo.
    - All constants use "request." prefix.

Ctx.Runtime:
    - hostname, service_name, service_version, container_id, pod_name —
      match RuntimeInfo.
    - All constants use "runtime." prefix.

Ctx structure:
    - Three groups: User, Request, Runtime.
    - Constants work with frozenset and string paths.
"""

from action_machine.context.ctx_constants import Ctx

# ═════════════════════════════════════════════════════════════════════════════
# Ctx.User — UserInfo fields
# ═════════════════════════════════════════════════════════════════════════════


class TestUserFields:
    """Ctx.User constants match UserInfo fields."""

    def test_user_id_path(self) -> None:
        """Ctx.User.user_id → "user.user_id" (UserInfo.user_id)."""
        # Arrange — Ctx.User.user_id
        # Act / Assert — matches Context dot-path navigation
        assert Ctx.User.user_id == "user.user_id"

    def test_roles_path(self) -> None:
        """Ctx.User.roles → "user.roles" (UserInfo.roles)."""
        # Arrange — Ctx.User.roles
        # Act / Assert — matches Context dot-path navigation
        assert Ctx.User.roles == "user.roles"

    def test_all_are_strings(self) -> None:
        """All Ctx.User constants are str."""
        # Arrange — all Ctx.User constants
        fields = [Ctx.User.user_id, Ctx.User.roles]

        # Act / Assert — each is str
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_user_prefix(self) -> None:
        """All Ctx.User constants start with "user."."""
        # Arrange
        fields = [Ctx.User.user_id, Ctx.User.roles]

        # Act / Assert
        for field in fields:
            assert field.startswith("user.")


# ═════════════════════════════════════════════════════════════════════════════
# Ctx.Request — RequestInfo fields
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestFields:
    """Ctx.Request constants match RequestInfo fields."""

    def test_trace_id_path(self) -> None:
        """Ctx.Request.trace_id → "request.trace_id"."""
        # Arrange / Act / Assert — matches RequestInfo field
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
        """All Ctx.Request constants are str."""
        # Arrange
        fields = [
            Ctx.Request.trace_id, Ctx.Request.request_timestamp,
            Ctx.Request.request_path, Ctx.Request.request_method,
            Ctx.Request.full_url, Ctx.Request.client_ip,
            Ctx.Request.protocol, Ctx.Request.user_agent,
        ]

        # Act / Assert
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_request_prefix(self) -> None:
        """All Ctx.Request constants start with "request."."""
        # Arrange
        fields = [
            Ctx.Request.trace_id, Ctx.Request.request_timestamp,
            Ctx.Request.request_path, Ctx.Request.request_method,
            Ctx.Request.full_url, Ctx.Request.client_ip,
            Ctx.Request.protocol, Ctx.Request.user_agent,
        ]

        # Act / Assert
        for field in fields:
            assert field.startswith("request.")


# ═════════════════════════════════════════════════════════════════════════════
# Ctx.Runtime — RuntimeInfo fields
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeFields:
    """Ctx.Runtime constants match RuntimeInfo fields."""

    def test_hostname_path(self) -> None:
        """Ctx.Runtime.hostname → "runtime.hostname"."""
        # Arrange / Act / Assert — matches RuntimeInfo field
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
        """All Ctx.Runtime constants are str."""
        # Arrange
        fields = [
            Ctx.Runtime.hostname, Ctx.Runtime.service_name,
            Ctx.Runtime.service_version, Ctx.Runtime.container_id,
            Ctx.Runtime.pod_name,
        ]

        # Act / Assert
        for field in fields:
            assert isinstance(field, str)

    def test_all_start_with_runtime_prefix(self) -> None:
        """All Ctx.Runtime constants start with "runtime."."""
        # Arrange
        fields = [
            Ctx.Runtime.hostname, Ctx.Runtime.service_name,
            Ctx.Runtime.service_version, Ctx.Runtime.container_id,
            Ctx.Runtime.pod_name,
        ]

        # Act / Assert
        for field in fields:
            assert field.startswith("runtime.")


# ═════════════════════════════════════════════════════════════════════════════
# Top-level Ctx structure
# ═════════════════════════════════════════════════════════════════════════════


class TestCtxStructure:
    """Top-level Ctx exposes three field groups."""

    def test_user_group_exists(self) -> None:
        """Ctx.User is available as an attribute."""
        # Arrange / Act / Assert
        assert hasattr(Ctx, "User")

    def test_request_group_exists(self) -> None:
        """Ctx.Request is available as an attribute."""
        # Arrange / Act / Assert
        assert hasattr(Ctx, "Request")

    def test_runtime_group_exists(self) -> None:
        """Ctx.Runtime is available as an attribute."""
        # Arrange / Act / Assert
        assert hasattr(Ctx, "Runtime")

    def test_constants_usable_as_plain_strings(self) -> None:
        """
        Ctx constants work alongside plain string paths in frozensets.

        Mix constants and strings for subclass fields:
        @context_requires(Ctx.User.user_id, "user.billing_plan").
        """
        # Arrange — Ctx constant mixed with string path
        keys = [Ctx.User.user_id, "user.billing_plan"]

        # Act / Assert — both are str, suitable for frozenset
        result = frozenset(keys)
        assert len(result) == 2
        assert "user.user_id" in result
        assert "user.billing_plan" in result
