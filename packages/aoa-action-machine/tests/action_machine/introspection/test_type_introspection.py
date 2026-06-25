import types

import pytest

from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class _CallableHost:
    value = "not-callable"

    def keep_me(self) -> None:
        pass

    def skip_me(self) -> None:
        pass

    @property
    def calculated(self) -> int:
        return 1


class _SubclassWithDupProperty(_CallableHost):
    @property
    def calculated(self) -> int:
        return 99


def test_unwrap_callable_strips_bound_method_wrapper() -> None:
    bound = types.MethodType(_CallableHost.keep_me, _CallableHost())
    unwrapped = TypeIntrospection.unwrap_callable(bound)
    assert unwrapped.__name__ == "keep_me"
    assert TypeIntrospection.unwrapped_callable_name(bound) == "keep_me"


def test_qualname_of_and_module_name_fallbacks() -> None:
    sentinel = types.SimpleNamespace()
    assert TypeIntrospection.qualname_of(sentinel) == "SimpleNamespace"


class _NonStrModule:
    __module__ = 404


def test_module_name_of_rejects_non_str_module_attribute() -> None:
    assert TypeIntrospection.module_name_of(_NonStrModule()) is None


def test_qualname_of_falls_through_empty_qualname_strings() -> None:
    sentinel = types.SimpleNamespace()
    object.__setattr__(sentinel, "__qualname__", "")
    object.__setattr__(sentinel, "__name__", "named_via_name")
    assert TypeIntrospection.qualname_of(sentinel) == "named_via_name"


def test_full_qualname_bare_qualname_under_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(TypeIntrospection, "module_name_of", lambda _owner: "__main__")
    assert TypeIntrospection.full_qualname(_CallableHost) == "_CallableHost"


def test_own_namespace_keys_exposes_declaration_order() -> None:
    assert "value" in TypeIntrospection.own_namespace_keys(_CallableHost)


def test_collect_own_class_callables_filters_by_predicate() -> None:
    callables = TypeIntrospection.collect_own_class_callables(
        _CallableHost,
        lambda fn: fn.__name__ in {"keep_me", "calculated"},
    )

    assert callables == [_CallableHost.keep_me, _CallableHost.calculated.fget]


def test_property_members_merges_subclass_overrides() -> None:
    props = TypeIntrospection.property_members(_SubclassWithDupProperty)
    assert props["calculated"] is _SubclassWithDupProperty.__dict__["calculated"]


def test_callable_parameter_names_and_return_annotation() -> None:
    def sample(a: str, *, b: int = 1) -> bool:
        return True

    assert TypeIntrospection.callable_parameter_names(sample) == ("a", "b")
    assert TypeIntrospection.callable_return_annotation(sample) is bool
