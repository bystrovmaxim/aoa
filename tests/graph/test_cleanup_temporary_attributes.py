# tests/graph/test_cleanup_temporary_attributes.py
"""cleanup_temporary_attributes removes decorator scratch from a class."""

from __future__ import annotations

from action_machine.graph.cleanup import cleanup_temporary_attributes


def test_cleanup_removes_class_level_scratch_from_dict() -> None:
    class Scratchy:
        _role_info = [{"r": 1}]
        _depends_info = [{"d": 1}]
        _connection_info = [{"c": 1}]

    cleanup_temporary_attributes(Scratchy)

    assert "_role_info" not in Scratchy.__dict__
    assert "_depends_info" not in Scratchy.__dict__
    assert "_connection_info" not in Scratchy.__dict__


def test_cleanup_removes_method_level_scratch_from_function() -> None:
    class WithMeta:
        def hook(self) -> None:
            pass

    fn = WithMeta.__dict__["hook"]
    fn._checker_meta = [{"field": "x"}]

    cleanup_temporary_attributes(WithMeta)

    assert not hasattr(fn, "_checker_meta")


def test_cleanup_idempotent_on_scrubbed_class() -> None:
    class Empty:
        pass

    cleanup_temporary_attributes(Empty)
    cleanup_temporary_attributes(Empty)


def test_cleanup_skips_non_callable_entries_in_class_dict() -> None:
    """``_get_underlying_function`` returns None for plain data attributes."""

    class WithData:
        marker = 42

    cleanup_temporary_attributes(WithData)
    assert WithData.marker == 42
