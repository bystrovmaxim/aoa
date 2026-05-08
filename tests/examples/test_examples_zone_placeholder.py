# tests/examples/test_examples_zone_placeholder.py
"""Minimal smoke: ``aoa.examples`` imports without ``aoa.maxitor``."""


def test_import_examples_namespace() -> None:
    import aoa.examples  # noqa: F401
