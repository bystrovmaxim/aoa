# packages/maxitor/tests/gnomon/test_package.py
"""``gnomon --version`` names the version ``maxitor`` was installed with."""

from __future__ import annotations

from importlib.metadata import version

import maxitor


def test_package_states_its_installed_version() -> None:
    """``maxitor.__version__`` is the version the distribution was installed with."""
    assert maxitor.__version__ == version("maxitor")
