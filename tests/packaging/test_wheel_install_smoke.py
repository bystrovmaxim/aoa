# tests/packaging/test_wheel_install_smoke.py
"""
Wheel layout and clean-venv install smoke for the publishable distributions (``aoa-*`` and ``maxitor``).

Requires prior ``uv build --package <pkg> --out-dir packages/<pkg>/dist`` (the CI packaging job builds before pytest).
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

# Single source of truth: every publishable distribution → the one top-level tree its wheel ships.
# ``aoa-*`` share the ``aoa/`` namespace; ``maxitor`` stands outside it.
_DIST_TREE: dict[str, str] = {
    "aoa-action-machine": "aoa/action_machine/",
    "aoa-ocel": "aoa/ocel/",
    "aoa-otel": "aoa/otel/",
    "aoa-fastapi-adapter": "aoa/fastapi/",
    "aoa-mcp-adapter": "aoa/mcp/",
    "aoa-langgraph": "aoa/langgraph/",
    "maxitor": "maxitor/",
    "aoa-demo": "aoa/demo/",
}

_PACKAGE_DIRS: dict[str, str] = {dist: dist for dist in _DIST_TREE}

# A wheel must vendor ONLY its own tree — every other package's tree is forbidden (cross-package
# code arrives as a declared pip dependency, never bundled in the wheel), and a package outside
# the ``aoa`` namespace ships nothing under ``aoa/`` at all.
_FORBIDDEN_PREFIXES: dict[str, tuple[str, ...]] = {
    dist: tuple(other for d, other in _DIST_TREE.items() if d != dist) + (() if own.startswith("aoa/") else ("aoa/",))
    for dist, own in _DIST_TREE.items()
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
            f"Missing {dist_dir}; build wheels first, e.g.:\n" f"  uv build --package {folder} --out-dir packages/{folder}/dist"
        )
    wheels = sorted(dist_dir.glob(f"{dist_key.replace('-', '_')}-*.whl"))
    if not wheels:
        pytest.fail(f"No .whl matching {dist_key!r} under {dist_dir}")
    return wheels[-1]


def _wheel_member_paths(whl: Path) -> list[str]:
    with ZipFile(whl, "r") as zf:
        return zf.namelist()


def _code_paths(names: Iterable[str]) -> list[str]:
    return [n for n in names if ".dist-info/" not in n]


@pytest.mark.parametrize("dist_key", sorted(_PACKAGE_DIRS))
def test_wheel_contains_only_its_own_tree(dist_key: str) -> None:
    whl = _latest_wheel(dist_key)
    code = _code_paths(_wheel_member_paths(whl))
    own = _DIST_TREE[dist_key]
    assert any(n.startswith(own) for n in code), f"{whl.name}: missing prefix {own!r} in {code[:30]}"
    for bad in _FORBIDDEN_PREFIXES[dist_key]:
        hits = [n for n in code if n.startswith(bad)]
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


def test_clean_install_action_machine_provides_graph(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(vpy, [_latest_wheel("aoa-action-machine")])
    _run_in_venv(
        vpy,
        "import importlib.util as u; import aoa.action_machine; "
        "from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode; "
        "from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator; "
        "from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA; "
        "assert GRAPH_JSON_SCHEMA['properties']['schema_version'] == {'const': '1.2'}; "
        "assert u.find_spec('aoa.action_machine.plugin.ocel') is None; "
        "assert u.find_spec('aoa.ocel') is None; "
        "assert u.find_spec('aoa.otel') is None; "
        "assert u.find_spec('maxitor') is None; "
        "assert u.find_spec('aoa.demo') is None; "
        "assert u.find_spec('maxitor') is None",
    )


def test_clean_install_maxitor_brings_no_aoa(tmp_path: Path) -> None:
    """``pip install maxitor`` with no extra is the ``graph-builder`` command alone: no AOA, none of the front's dependencies."""
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(vpy, [_latest_wheel("maxitor")])
    installed = subprocess.run(
        [str(vpy), "-c", "import importlib.metadata as m; print('\\n'.join(sorted(d.metadata['Name'].lower() for d in m.distributions())))"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    brought = [d for d in installed if d.startswith("aoa") or d in {"fastapi", "uvicorn", "duckdb", "httpx", "websockets"}]
    assert brought == [], f"the base install brought {brought}"
    fixture = REPO_ROOT / "packages" / "maxitor" / "tools" / "graph_builder" / "tests" / "fixtures" / "graph-1.2.json"
    (tmp_path / "graph-builder.toml").write_text(
        f'graph_builder = "1.0"\n\n[[graph]]\nname = "sample"\nbuild = "cat {fixture}"\nfile = "graph.json"\n', encoding="utf-8"
    )
    graph_builder = str(venv / "bin" / "graph-builder")
    subprocess.run([graph_builder, "write"], check=True, cwd=str(tmp_path))
    checked = subprocess.run([graph_builder, "check"], check=True, capture_output=True, text=True, cwd=str(tmp_path)).stdout
    assert checked.startswith("ok sample")
    validated = subprocess.run(
        [graph_builder, "validate", "graph.json"], check=True, capture_output=True, text=True, cwd=str(tmp_path)
    ).stdout
    assert validated.startswith("ok 1.2: ")
    skill = subprocess.run([graph_builder, "skill"], check=True, capture_output=True, text=True, cwd=str(tmp_path)).stdout
    assert skill.startswith("---\nname: aoa-graph-builder-setup\n")


def test_clean_install_maxitor_front_names_its_extra(tmp_path: Path) -> None:
    """Without the ``front`` extra, ``maxitor`` names the extra instead of failing on an import."""
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(vpy, [_latest_wheel("maxitor")])
    _run_in_venv(vpy, "import importlib.util as u; import importlib.metadata as m; assert m.version('maxitor'); assert u.find_spec('aoa') is None")
    started = subprocess.run(
        [str(venv / "bin" / "maxitor")], check=False, capture_output=True, text=True, cwd=str(tmp_path)
    )
    assert started.returncode == 2
    assert started.stderr == 'maxitor needs its front: pip install "maxitor[front]"\n'


def test_clean_install_repo_graph_port_names_its_extra(tmp_path: Path) -> None:
    """Without the ``repo-graph-port`` extra, ``repo-graph-port`` names the extra instead of failing on an import."""
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(vpy, [_latest_wheel("maxitor")])
    started = subprocess.run(
        [str(venv / "bin" / "repo-graph-port")], check=False, capture_output=True, text=True, cwd=str(tmp_path)
    )
    assert started.returncode == 2
    assert started.stderr == 'repo-graph-port needs its extra: pip install "maxitor[repo-graph-port]"\n'


def test_clean_install_examples_does_not_pull_maxitor(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    subprocess.run([_which_uv(), "venv", str(venv)], check=True, cwd=str(REPO_ROOT))
    vpy = _venv_python(venv)
    _uv_pip_install(
        vpy,
        [
            _latest_wheel("aoa-action-machine"),
            _latest_wheel("aoa-ocel"),
            _latest_wheel("aoa-demo"),
        ],
    )
    _run_in_venv(
        vpy,
        "import importlib.util as u; import aoa.action_machine; "
        "import aoa.demo; "
        "assert u.find_spec('aoa.action_machine.plugin.ocel') is None; "
        "assert u.find_spec('aoa.ocel') is not None; "
        "assert u.find_spec('maxitor') is None",
    )
    listed = subprocess.run(
        [_which_uv(), "pip", "list", f"--python={vpy}"],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    ).stdout.lower()
    assert "maxitor" not in listed
