# packages/maxitor/tools/repo_graph_port/tests/test_version_source.py
"""Reading a number: version-gate's own samples, and every reason there is none."""

from __future__ import annotations

from pathlib import Path

import pytest
from maxitor.repo_graph_port.version_source import (
    BROKEN,
    DRIVER,
    FORMAT,
    MISSING,
    NOT_A_STRING,
    NumberRead,
    read_number,
)

SAMPLES = Path(__file__).parent / "fixtures" / "version_gate"


@pytest.mark.parametrize("sample", ["component.toml", "package-direct.toml", "repository-direct.toml"])
def test_a_sample_with_a_direct_number_gives_it(sample: str) -> None:
    """A number written in ``version.toml`` is read by the default key."""
    read = read_number("version.toml", (SAMPLES / sample).read_bytes(), "version")
    assert read.number is not None and read.reason is None


def test_a_sample_with_a_driver_names_the_driver() -> None:
    """A ``version.toml`` that points at a driver holds no number of its own."""
    assert read_number("version.toml", (SAMPLES / "package-driver.toml").read_bytes(), "version") == NumberRead(reason=DRIVER)


@pytest.mark.parametrize(
    ("name", "content", "key", "expected"),
    [
        ("pyproject.toml", b'[project]\nversion = "1.0.1a6"\n', "project.version", NumberRead(number="1.0.1a6")),
        ("Cargo.toml", b'[workspace.package]\nversion = "2.0.0"\n', "workspace.package.version", NumberRead(number="2.0.0")),
        ("package.json", b'{"version": "1.2.3"}', "version", NumberRead(number="1.2.3")),
        ("pyproject.toml", b'[project]\nname = "a"\n', "project.version", NumberRead(reason=MISSING)),
        ("Cargo.toml", b"[package]\nversion.workspace = true\n", "package.version", NumberRead(reason=NOT_A_STRING)),
        ("package.json", b'{"version": 3}', "version", NumberRead(reason=NOT_A_STRING)),
        ("package.json", b'{"version": ""}', "version", NumberRead(reason=NOT_A_STRING)),
        ("package.json", b"[1]", "version", NumberRead(reason=MISSING)),
        ("version.toml", b"version = ", "version", NumberRead(reason=BROKEN)),
        ("version.toml", b"\xff\xfe", "version", NumberRead(reason=BROKEN)),
        ("package.json", b"{", "version", NumberRead(reason=BROKEN)),
        ("pom.xml", b"<project/>", "version", NumberRead(reason=FORMAT)),
    ],
)
def test_a_file_gives_its_number_or_its_reason(name: str, content: bytes, key: str, expected: NumberRead) -> None:
    """Each format and each reason, on any bytes."""
    assert read_number(name, content, key) == expected
