# packages/maxitor/tools/gnomon/tests/test_package.py
"""``gnomon --version`` names the version ``maxitor`` was installed with."""

from __future__ import annotations

from importlib.metadata import version

import pytest
from maxitor.gnomon.cli import main


def test_the_version_is_the_installed_maxitor(capsys: pytest.CaptureFixture[str]) -> None:
    """``gnomon --version`` prints the version of the installed ``maxitor`` distribution."""
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out == f"gnomon {version('maxitor')}\n"
