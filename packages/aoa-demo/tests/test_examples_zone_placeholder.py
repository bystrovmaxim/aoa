# tests/examples/test_examples_zone_placeholder.py
"""Minimal smoke: ``aoa.demo`` imports without ``maxitor.front``."""


def test_import_examples_namespace() -> None:
    import aoa.demo  # noqa: F401
