# tests/packaging/test_wheel_install_smoke.py
"""
Wheel layout and clean-venv install smoke for publishable ``aoa-*`` distributions.

Requires prior ``python -m build packages/<pkg>`` (``run_checks_with_log.sh`` runs builds before pytest).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from zipfile import ZipFile

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_PACKAGE_DIRS: dict[str, str] = {
    "aoa-graph": "aoa-graph",
    "aoa-action-machine": "aoa-action-machine",
    "aoa-maxitor": "aoa-maxitor",
    "aoa-examples": "aoa-examples",
}

# Wheel must ship this prefix under ``aoa/`` (namespace); ``*.dist-info`` etc. are ignored.
_REQUIRED_AOA_PREFIX: dict[str, str] = {
    "aoa-graph": "aoa/graph/",
    "aoa-action-machine": "aoa/action_machine/",
    "aoa-maxitor": "aoa/maxitor/",
    "aoa-examples": "aoa/examples/",
}

# No other ``aoa.*`` subtree may appear inside the wheel archive.
_FORBIDDEN_AOA_PREFIXES: dict[str, tuple[str, ...]] = {
    "aoa-graph": ("aoa/action_machine/", "aoa/maxitor/", "aoa/examples/"),
    "aoa-action-machine": ("aoa/maxitor/", "aoa/examples/"),
    "aoa-maxitor": ("aoa/examples/",),
    "aoa-examples": ("aoa/maxitor/",),
}


def _which_uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        pytest.fail("uv executable not found on PATH (required for packaging smoke tests)")
    return uv


def _latest_wheel(dist_key: str) -> Path:
    folder = _PACKAGE_DIRS[dist_key]
    dist_dir = REPO_ROOT / "packages" / folder / "dist"
    if not dist_dir.is_dir():
        pytest.fail(
            f"Missing {dist_dir}; build wheels first, e.g.:\n"
            f"  uv run --group dev python -m build packages/{folder}"
        )
    wheels = sorted(dist_dir.glob(f"{dist_key.replace('-', '_')}-*.whl"))
    if not wheels:
        pytest.fail(f"No .whl matching {dist_key!r} under {dist_dir}")
    return wheels[-1]


def _wheel_member_paths(whl: Path) -> list[str]:
    with ZipFile(whl, "r") as zf:
        return zf.namelist()


def _aoa_paths(names: Iterable[str]) -> list[str]:
    return [n for n in names if n.startswith("aoa/")]


@pytest.mark.parametrize("dist_key", sorted(_PACKAGE_DIRS))
def test_wheel_contains_only_expected_aoa_namespace(dist_key: str) -> None:
    whl = _latest_wheel(dist_key)
    names = _wheel_member_paths(whl)
    aoa = _aoa_paths(names)
    assert aoa, f"{whl.name}: expected at least one aoa/ path, got {names[:20]!r}…"
    required = _REQUIRED_AOA_PREFIX[dist_key]
    assert any(n.startswith(required) for n in aoa), f"{whl.name}: missing prefix {required!r} in {aoa[:30]}"
    for bad in _FORBIDDEN_AOA_PREFIXES[dist_key]:
        hits = [n for n in aoa if n.startswith(bad)]
        assert not hits, f"{whl.name}: forbidden prefix {bad!r}: {hits[:5]}"


def _venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _uv_pip_install(venv_py: Path, wheels: list[Path]) -> None:
    uv = _which_uv()
    cmd = [uv, "pip", "install", f"--python={venv_py}", *[str(w) for w in wheels]]
    env = {**os.environ, "UV_LINK_MODE": "copy"}
    subprocess.run(cmd, check=True, cwd=str(REPO_ROOT), env=env)


def _run_in_venv(venv_py: Path, code: str) -> None:
    subprocess.run([str(venv_py), "-c", code], check=True, cwd=str(REPO_ROOT))


def test_clean_install_graph_only(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(vpy, [_latest_wheel("aoa-graph")])
    _run_in_venv(
        vpy,
        "import importlib.util as u; import aoa.graph; "
        "assert u.find_spec('aoa.action_machine') is None; "
        "assert u.find_spec('aoa.maxitor') is None; "
        "assert u.find_spec('aoa.examples') is None",
    )


def test_clean_install_action_machine_pulls_graph(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(vpy, [_latest_wheel("aoa-graph"), _latest_wheel("aoa-action-machine")])
    _run_in_venv(
        vpy,
        "import importlib.util as u; import aoa.graph; import aoa.action_machine; "
        "assert u.find_spec('aoa.maxitor') is None; "
        "assert u.find_spec('aoa.examples') is None",
    )


def test_clean_install_maxitor_pulls_action_machine_and_graph(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(
        vpy,
        [
            _latest_wheel("aoa-graph"),
            _latest_wheel("aoa-action-machine"),
            _latest_wheel("aoa-maxitor"),
        ],
    )
    _run_in_venv(
        vpy,
        "import importlib.util as u; import aoa.graph; import aoa.action_machine; import aoa.maxitor; "
        "assert u.find_spec('aoa.examples') is None",
    )


def test_clean_install_examples_does_not_pull_maxitor(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(
        vpy,
        [
            _latest_wheel("aoa-graph"),
            _latest_wheel("aoa-action-machine"),
            _latest_wheel("aoa-examples"),
        ],
    )
    _run_in_venv(
        vpy,
        "import importlib.util as u; import aoa.graph; import aoa.action_machine; import aoa.examples; "
        "assert u.find_spec('aoa.maxitor') is None",
    )
    listed = subprocess.run(
        [_which_uv(), "pip", "list", f"--python={vpy}"],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    ).stdout.lower()
    assert "aoa-maxitor" not in listed
