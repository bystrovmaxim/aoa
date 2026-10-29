# packages/maxitor/tools/graph_builder/tests/test_package.py
"""``graph-builder --version`` names the version ``maxitor`` was installed with."""

from __future__ import annotations

from importlib.metadata import version

import pytest
from maxitor.graph_builder.cli import main


def test_the_version_is_the_installed_maxitor(capsys: pytest.CaptureFixture[str]) -> None:
    """``graph-builder --version`` prints the version of the installed ``maxitor`` distribution."""
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out == f"graph-builder {version('maxitor')}\n"
