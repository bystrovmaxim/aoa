# tests/plugins/context/test_user_info.py
"""
Тесты для класса UserInfo.
"""
from action_machine.context.user_info import UserInfo


class TestUserInfo:
    def test_create_with_attributes(self):
        user = UserInfo(user_id="123", roles=["admin", "user"], extra={"org": "acme"})
        assert user.user_id == "123"
        assert user.roles == ["admin", "user"]
        assert user.extra == {"org": "acme"}

    def test_default_values(self):
        user = UserInfo()
        assert user.user_id is None
        assert user.roles == []
        assert user.extra == {}

    def test_dict_protocol_getitem(self):
        user = UserInfo(user_id="123")
        assert user["user_id"] == "123"

    def test_dict_protocol_contains(self):
        user = UserInfo(user_id="123")
        assert "user_id" in user
        assert "missing" not in user

    def test_dict_protocol_get(self):
        user = UserInfo(user_id="123")
        assert user.get("user_id") == "123"
        assert user.get("missing", "fallback") == "fallback"
        assert user.get("missing") is None

    def test_dict_protocol_keys(self):
        user = UserInfo(user_id="123", roles=["admin"])
        keys = user.keys()
        assert "user_id" in keys
        assert "roles" in keys
        assert "extra" in keys
        assert "_resolve_cache" not in keys

    def test_dict_protocol_values(self):
        """values возвращает значения публичных полей."""
        user = UserInfo(user_id="123", roles=["admin"])
        values = user.values()
        # Исправлено: 123 (int) нельзя использовать с 'in str(...)' — только строку
        assert "123" in str(values)
        assert ["admin"] in values
        assert {} in values

    def test_dict_protocol_items(self):
        user = UserInfo(user_id="123")
        items = user.items()
        assert ("user_id", "123") in items