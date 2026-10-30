# packages/maxitor/front/tests/test_front_imports_without_jwt.py
"""Maxitor's server starts without the JWT extra, which its image does not install (found on the local stand, #289)."""

from __future__ import annotations

import subprocess
import sys

_IMPORT_WITHOUT_JWT = """
import sys
sys.modules["jwt"] = None  # as in an image built without ``aoa-action-machine[jwt]``
from maxitor.front.api.app import create_app
create_app()
print("ok")
"""


def test_the_app_builds_without_the_jwt_extra() -> None:
    """With ``jwt`` unimportable, the app module imports and builds."""
    done = subprocess.run([sys.executable, "-c", _IMPORT_WITHOUT_JWT], capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr[-2000:]
    assert done.stdout.strip().endswith("ok")
