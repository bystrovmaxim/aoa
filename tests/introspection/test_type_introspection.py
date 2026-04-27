from action_machine.introspection_tools.type_introspection import TypeIntrospection


class _CallableHost:
    value = "not-callable"

    def keep_me(self) -> None:
        pass

    def skip_me(self) -> None:
        pass

    @property
    def calculated(self) -> int:
        return 1


def test_collect_own_class_callables_filters_by_predicate() -> None:
    callables = TypeIntrospection.collect_own_class_callables(
        _CallableHost,
        lambda fn: fn.__name__ in {"keep_me", "calculated"},
    )

    assert callables == [_CallableHost.keep_me, _CallableHost.calculated.fget]
