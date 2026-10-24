# tests/action_machine/graph/test_entity_field_source_check.py
"""
Tests for ``scripts/check_complete_entity_fields.py`` — the explicit-root source gate.

Pydantic merges the assignment-side and annotation-side ``Field(...)`` into one
``FieldInfo``, so runtime validation cannot prove where the field was written. The source
checker restores that guarantee from the source. These tests run the checker against
temporary source fixtures in a fresh interpreter, never against this repository's source.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_CHECKER = _REPO_ROOT / "scripts" / "check_complete_entity_fields.py"

_VALID_SOURCE = textwrap.dedent(
    """
    from __future__ import annotations

    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, Inverse


    class TargetCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")


    class HostCoreEntity(BaseCoreEntity):
        link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = Field(
            description="Link"
        )
    """
)


def _run_checker(root: Path, sources: dict[str, str]) -> tuple[int, str]:
    """Write ``sources`` under ``root`` and run the checker over ``root``."""
    for name, content in sources.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(_CHECKER), str(root)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode, result.stdout


def test_valid_assignment_side_field_passes(tmp_path: Path) -> None:
    """The one legal form — a single assignment-side Field — produces no report."""
    returncode, stdout = _run_checker(tmp_path, {"host.py": _VALID_SOURCE})

    assert returncode == 0
    assert stdout.strip() == ""


def test_missing_assignment_field_is_reported(tmp_path: Path) -> None:
    """A relation field with no assignment-side Field is reported."""
    source = _VALID_SOURCE.replace(
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = Field(\n'
        '        description="Link"\n'
        "    )\n",
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")]\n',
    )
    returncode, stdout = _run_checker(tmp_path, {"host.py": source})

    assert returncode == 1
    assert "link" in stdout
    assert "Field" in stdout


def test_annotation_side_field_is_reported(tmp_path: Path) -> None:
    """A Field written inside Annotated instead of on the assignment side is reported."""
    source = _VALID_SOURCE.replace(
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = Field(\n'
        '        description="Link"\n'
        "    )\n",
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back"), Field(description="Link")]\n',
    )
    returncode, stdout = _run_checker(tmp_path, {"host.py": source})

    assert returncode == 1
    assert "link" in stdout
    assert "Annotated" in stdout


def test_duplicate_field_is_reported(tmp_path: Path) -> None:
    """A field with both an annotation-side and an assignment-side Field is reported."""
    source = _VALID_SOURCE.replace(
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = Field(\n'
        '        description="Link"\n'
        "    )\n",
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back"), Field(description="Inner")] = Field(\n'
        '        description="Link"\n'
        "    )\n",
    )
    returncode, stdout = _run_checker(tmp_path, {"host.py": source})

    assert returncode == 1
    assert "link" in stdout


def test_import_alias_field_is_recognized(tmp_path: Path) -> None:
    """``from pydantic import Field as F`` is resolved to the same Field."""
    source = _VALID_SOURCE.replace(
        "from pydantic import Field",
        "from pydantic import Field as F",
    ).replace("= Field(", "= F(")
    returncode, stdout = _run_checker(tmp_path, {"host.py": source})

    assert returncode == 0
    assert stdout.strip() == ""


def test_unsupported_assignment_syntax_is_reported(tmp_path: Path) -> None:
    """An assignment the checker cannot classify is reported, never silently accepted."""
    source = _VALID_SOURCE.replace(
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = Field(\n'
        '        description="Link"\n'
        "    )\n",
        '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = some_builder()\n',
    )
    returncode, stdout = _run_checker(tmp_path, {"host.py": source})

    assert returncode == 1
    assert "link" in stdout


def test_explicit_root_exclusion(tmp_path: Path) -> None:
    """A violating file outside the given root is not scanned."""
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir(exist_ok=True)
    (outside / "bad.py").write_text(
        _VALID_SOURCE.replace(
            '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")] = Field(\n'
            '        description="Link"\n'
            "    )\n",
            '    link: Annotated[AssociationOne[TargetCoreEntity], Inverse(TargetCoreEntity, "back")]\n',
        ),
        encoding="utf-8",
    )

    returncode, stdout = _run_checker(tmp_path, {"host.py": _VALID_SOURCE})

    assert returncode == 0
    assert stdout.strip() == ""
