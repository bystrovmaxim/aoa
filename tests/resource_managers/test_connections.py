# tests/resource_managers/test_connections.py
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connections import Connections


class DummyRes(BaseResourceManager):
    def get_wrapper_class(self):
        return None

def test_connections_typeddict():
    res = DummyRes()
    conn: Connections = {"connection": res}
    assert conn["connection"] is res
