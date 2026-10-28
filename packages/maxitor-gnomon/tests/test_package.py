# packages/maxitor-gnomon/tests/test_package.py
"""The package imports and states the version it was installed with."""

from __future__ import annotations

from importlib.metadata import version

import maxitor_gnomon


def test_package_states_its_installed_version() -> None:
    """``__version__`` is the version the distribution was installed with."""
    assert maxitor_gnomon.__version__ == version("maxitor-gnomon")
