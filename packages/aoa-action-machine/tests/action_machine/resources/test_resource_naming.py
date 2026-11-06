# packages/aoa-action-machine/tests/action_machine/resources/test_resource_naming.py
"""ResourceNaming — declaration and model-build contracts for resource kinds."""

from types import SimpleNamespace

import pytest

from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.resource_wrapper_validator import validate_resource_wrappers
from aoa.action_machine.resources import BaseController, BaseGateway, BaseResource, BaseStorage
from aoa.action_machine.resources.base_resource import resource_kind


def _resource(name, base=BaseStorage, **attributes):
    """Declare an isolated resource without constructing an instance."""
    return exclude_graph_model(type(name, (base,), attributes))


def _validate(*classes):
    """Validate the resource declarations supplied by graph nodes."""
    validate_resource_wrappers(SimpleNamespace(node_obj=cls) for cls in classes)


@pytest.mark.parametrize("base,kind", [(BaseStorage, "Storage"), (BaseGateway, "Gateway"), (BaseController, "Controller")])
def test_kind_names_and_wrappers(base, kind):
    """Accept both names belonging to each resource kind."""
    for name in (f"Orders{kind}", f"Orders{kind}Wrapper"):
        assert resource_kind(_resource(name, base)) == kind


@pytest.mark.parametrize("base", [BaseStorage, BaseGateway, BaseController])
def test_missing_kind_suffix(base):
    """Refuse a name lacking the inherited kind suffix."""
    with pytest.raises(NamingSuffixError, match=r"Class 'Orders'.*suffix"):
        _resource("Orders", base)


@pytest.mark.parametrize("base", [BaseStorage, BaseGateway, BaseController])
def test_missing_wrapper_kind_suffix(base):
    """Refuse a wrapper name lacking its kind."""
    with pytest.raises(NamingSuffixError, match=r"OrdersWrapper.*Wrapper"):
        _resource("OrdersWrapper", base)


@pytest.mark.parametrize("attributes", [{}, {"RESOURCE_KIND": "Storage"}, {"__module__": "aoa.action_machine.resources.base_storage"}])
def test_direct_resource_subclass_cannot_impersonate_a_kind(attributes):
    """Reject copied names, attributes and canonical module names."""
    with pytest.raises(DeclarationStructureError, match="inherits BaseResource directly"):
        _resource("BaseStorage", BaseResource, **attributes)


def test_kind_override_does_not_change_ancestry():
    """Ignore descendant kind attributes when deriving identity."""
    cls = _resource("OrdersStorage", RESOURCE_KIND="Gateway")
    assert resource_kind(cls) == "Storage"
    with pytest.raises(NamingSuffixError):
        _resource("OrdersGateway", RESOURCE_KIND="Gateway")


def test_mixed_kinds_are_refused():
    """Reject resources inheriting two distinct kinds."""
    with pytest.raises(DeclarationStructureError, match="resource kinds"):
        type("MixedStorage", (BaseStorage, BaseGateway), {})


def test_same_kind_multiple_inheritance():
    """Allow a diamond within one resource kind."""
    left = _resource("LeftStorage")
    right = _resource("RightStorage")
    cls = exclude_graph_model(type("CombinedStorage", (left, right), {}))
    assert resource_kind(cls) == "Storage"


def test_no_wrapper_and_inherited_class_method():
    """Accept inherited declarations without constructing resources."""
    def forbid_construction(self):
        """Fail if validation attempts resource construction."""
        raise AssertionError("resource constructed")

    parent = _resource("ParentStorage", get_wrapper_class=classmethod(lambda cls: None), __init__=forbid_construction)
    child = _resource("ChildStorage", parent)
    _validate(parent, child, object, None)
    assert child.get_wrapper_class() is None


@pytest.mark.parametrize("descriptor", [lambda self: None, staticmethod(lambda: None), None])
def test_non_class_method_is_refused(descriptor):
    """Reject instance, static and non-callable wrapper declarations."""
    cls = _resource("OrdersStorage", get_wrapper_class=descriptor)
    with pytest.raises(DeclarationStructureError, match=r"get_wrapper_class.*class method"):
        _validate(cls)


@pytest.mark.parametrize("result", [42, object, "OrdersStorageWrapper"])
def test_invalid_wrapper_result(result):
    """Reject results other than resource classes or None."""
    cls = _resource("OrdersStorage", get_wrapper_class=classmethod(lambda cls: result))
    with pytest.raises(DeclarationStructureError, match="resource class or None"):
        _validate(cls)


def test_wrong_wrapper_kind():
    """Reject a valid wrapper belonging to a different kind."""
    wrapper = _resource("OtherGatewayWrapper", BaseGateway)
    cls = _resource("OrdersStorage", get_wrapper_class=classmethod(lambda cls: wrapper))
    with pytest.raises(DeclarationStructureError, match="same resource kind"):
        _validate(cls)


def test_wrapper_target_requires_wrapper_suffix():
    """Reject an ordinary resource as a wrapper target."""
    target = _resource("OtherStorage", get_wrapper_class=classmethod(lambda cls: None))
    cls = _resource("OrdersStorage", get_wrapper_class=classmethod(lambda cls: target))
    with pytest.raises(NamingSuffixError, match="StorageWrapper"):
        _validate(cls)


@pytest.mark.parametrize("cycle", [False, True])
def test_recursive_wrappers_and_cycles(cycle):
    """Visit every reachable wrapper exactly once, even in cycles."""
    calls = []
    first = _resource("FirstStorageWrapper")
    second = _resource("SecondStorageWrapper")

    def first_wrapper(cls):
        """Record the first wrapper visit."""
        calls.append(cls)
        return second

    def second_wrapper(cls):
        """Record the second wrapper visit."""
        calls.append(cls)
        return first if cycle else None

    first.get_wrapper_class = classmethod(first_wrapper)
    second.get_wrapper_class = classmethod(second_wrapper)
    _validate(first, second)
    assert calls == [first, second]


def test_self_wrapper_cycle():
    """Accept a wrapper returning itself without recursion."""
    cls = _resource("SelfStorageWrapper", get_wrapper_class=classmethod(lambda cls: cls))
    _validate(cls)


def test_deeper_wrapper_is_checked():
    """Reject a malformed target beyond the first wrapper."""
    wrapper = _resource("DeepStorageWrapper", get_wrapper_class=classmethod(lambda cls: object))
    cls = _resource("OrdersStorage", get_wrapper_class=classmethod(lambda cls: wrapper))
    with pytest.raises(DeclarationStructureError, match="DeepStorageWrapper"):
        _validate(cls)


def test_getter_failure_is_not_suppressed():
    """Propagate a wrapper declaration failure."""
    def fail(cls):
        """Expose an application declaration error."""
        raise ValueError("broken wrapper declaration")

    cls = _resource("OrdersStorage", get_wrapper_class=classmethod(fail))
    with pytest.raises(ValueError, match="broken wrapper declaration"):
        _validate(cls)


def test_model_build_checks_wrappers():
    """Exercise the real coordinator path, including a later resource node."""
    from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
    from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
    from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator

    good = _resource("GoodStorage", get_wrapper_class=classmethod(lambda cls: None))
    bad = _resource("BadStorage", get_wrapper_class=classmethod(lambda cls: object))

    class ResourceGraphNode(BaseGraphNode[object]):
        """Supply a resource without unrelated graph edges."""

        def __init__(self, **kwargs):
            """Initialize the test node through the base contract."""
            super().__init__(**kwargs)

        def get_all_edges(self):
            """Return no edges for this isolated contract test."""
            return []

    class ResourceInspector(BaseGraphNodeInspector[object]):
        """Supply two declarations to the real model build."""

        def _get_node(self, cls):
            """Leave discovery to the explicit node list."""
            return None

        def get_graph_nodes(self):
            """Return both resources in a deterministic order."""
            return [ResourceGraphNode(node_id=cls.__name__, node_type="Resource", label=cls.__name__, properties={}, node_obj=cls)
                    for cls in (good, bad)]

    with pytest.raises(DeclarationStructureError, match="BadStorage"):
        NodeGraphCoordinator().build([ResourceInspector()])


@pytest.mark.parametrize("statement", [
    "from aoa.action_machine.resources import BaseStorage, BaseGateway, BaseController",
    "from aoa.action_machine.resources.postgres import PostgresStorage",
    "from aoa.action_machine.intents.connection import connection",
])
def test_resource_imports_in_a_fresh_interpreter(statement):
    """Keep resource and connection entry points free of import cycles."""
    import os
    import subprocess
    import sys

    environment = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    result = subprocess.run([sys.executable, "-c", statement], env=environment, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
