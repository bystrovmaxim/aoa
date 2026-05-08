#!/usr/bin/env python3
# scripts/check_package_metadata.py
"""
Validate ``pyproject.toml`` dependency metadata for publishable ``aoa-*`` workspace members.

Ensures declared pip dependencies match the repository ``aoa-*`` dependency matrix (see each package ``pyproject.toml``).
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMBERS = (
    "aoa-graph",
    "aoa-action-machine",
    "aoa-maxitor",
    "aoa-examples",
)

# ``packages/<folder>/pyproject.toml`` for each distribution name.
_PACKAGE_DIR: dict[str, str] = {
    "aoa-graph": "aoa-graph",
    "aoa-action-machine": "aoa-action-machine",
    "aoa-maxitor": "aoa-maxitor",
    "aoa-examples": "aoa-examples",
}

# Normalized distribution names (hyphenated).
REQUIRED_MAIN: dict[str, frozenset[str]] = {
    "aoa-graph": frozenset(),
    "aoa-action-machine": frozenset({"aoa-graph"}),
    "aoa-maxitor": frozenset({"aoa-graph", "aoa-action-machine"}),
    "aoa-examples": frozenset({"aoa-graph", "aoa-action-machine"}),
}

FORBIDDEN_ANYWHERE: dict[str, frozenset[str]] = {
    "aoa-graph": frozenset({"aoa-action-machine", "aoa-maxitor", "aoa-examples"}),
    "aoa-action-machine": frozenset({"aoa-maxitor", "aoa-examples"}),
    "aoa-maxitor": frozenset({"aoa-examples"}),
    "aoa-examples": frozenset({"aoa-maxitor"}),
}

_NAME_RE = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")


def _norm(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _first_requirement_name(line: str) -> str | None:
    """Return the PEP 508 distribution name from the start of a requirement string."""
    head = line.split(";", 1)[0].strip()
    if not head:
        return None
    if "[" in head:
        head = head.split("[", 1)[0].strip()
    m = _NAME_RE.match(head)
    if not m:
        return None
    return _norm(m.group(1))


def _collect_requirement_strings(project: dict[str, Any]) -> list[str]:
    out: list[str] = []
    deps = project.get("dependencies")
    if isinstance(deps, list):
        out.extend(str(x) for x in deps)
    opt = project.get("optional-dependencies")
    if isinstance(opt, dict):
        for _extra, lines in opt.items():
            if isinstance(lines, list):
                out.extend(str(x) for x in lines)
    return out


def _aoa_distribution_names(reqs: list[str]) -> frozenset[str]:
    found: set[str] = set()
    for line in reqs:
        name = _first_requirement_name(line)
        if name is None:
            continue
        if name == "aoa" or name.startswith("aoa-"):
            found.add(name)
    return frozenset(found)


def _load_member_pyproject(dist_name: str) -> dict[str, Any]:
    folder = _PACKAGE_DIR[dist_name]
    path = REPO_ROOT / "packages" / folder / "pyproject.toml"
    if not path.is_file():
        raise SystemExit(f"Missing package pyproject: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _project_name(data: dict[str, Any]) -> str:
    try:
        name = data["project"]["name"]
    except KeyError as exc:
        raise SystemExit("Invalid pyproject: missing [project].name") from exc
    return _norm(str(name))


def check_all() -> list[str]:
    errors: list[str] = []
    for dist in MEMBERS:
        data = _load_member_pyproject(dist)
        pname = _project_name(data)
        if pname != dist:
            errors.append(f"{dist}: [project].name is {pname!r}, expected {dist!r}")
            continue
        project = data.get("project")
        if not isinstance(project, dict):
            errors.append(f"{dist}: missing [project] table")
            continue
        reqs = _collect_requirement_strings(project)
        aoa_deps = _aoa_distribution_names(reqs)
        required = REQUIRED_MAIN[dist]
        forbidden = FORBIDDEN_ANYWHERE[dist]
        missing = sorted(required - aoa_deps)
        if missing:
            errors.append(f"{dist}: missing required dependency(ies): {missing}")
        bad = sorted(aoa_deps & forbidden)
        if bad:
            errors.append(f"{dist}: forbidden dependency(ies): {bad}")
        extra = sorted(aoa_deps - required - forbidden)
        # Any other ``aoa-*`` (e.g. typos) should fail; ``aoa`` bare is also suspicious.
        suspicious = [x for x in extra if x.startswith("aoa-") or x == "aoa"]
        if suspicious:
            errors.append(f"{dist}: unexpected aoa distribution(s) in metadata: {suspicious}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    errors = check_all()
    if errors:
        print("Package metadata check failed:", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print("Success: package metadata matches the dependency matrix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
