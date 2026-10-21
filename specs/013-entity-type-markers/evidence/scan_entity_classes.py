# specs/013-entity-type-markers/evidence/scan_entity_classes.py
"""
Scan the entity corpus and report the numbers the specification rests on.

Walks every Python module under `packages/` and `examples/`, reads class
declarations with the `ast` module — the tree is never imported — and reports
how many classes sit directly on `BaseEntity`, how many sit on one of the six
kind markers, how many names carry a kind suffix, and how many carry none.
The same script produces the "before" numbers on the branch base and the
"after" numbers once the migration has run, so the two can be compared.

When `entity_kind_map.py` exists beside this file, it is imported and must
expose `ENTITY_KIND_MAP`: a sequence of mappings with the keys `module`,
`old_name`, `kind`, `new_name` and `reason`. The scan then reports how many
old names still appear anywhere in `packages/` and `examples/`, which is the
number the delivered branch must drive to zero.

Usage:
    UV_CACHE_DIR=./.uvcache uv run python specs/013-entity-type-markers/evidence/scan_entity_classes.py
    UV_CACHE_DIR=./.uvcache uv run python specs/013-entity-type-markers/evidence/scan_entity_classes.py --out specs/013-entity-type-markers/evidence/scan.before.txt
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = Path(__file__).resolve().parent
MAP_FILE = EVIDENCE_DIR / "entity_kind_map.py"

SCAN_ROOTS = ("packages", "examples")
SKIP_DIRS = frozenset(
    {"__pycache__", ".venv", "node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build"}
)

BASE_ENTITY = "BaseEntity"
MARKER_NAMES = (
    "BaseCoreEntity",
    "BaseAssocEntity",
    "BaseDetailEntity",
    "BaseSpecEntity",
    "BaseEnumEntity",
    "BaseStateEntity",
)
KIND_SUFFIXES = (
    "CoreEntity",
    "AssocEntity",
    "DetailEntity",
    "SpecEntity",
    "EnumEntity",
    "StateEntity",
)
STATE_MARKER = "BaseStateEntity"


@dataclass
class EntityClass:
    """One class declaration the scan found, with what it inherits and whether it is declared."""

    module: str
    name: str
    bases: tuple[str, ...]
    decorated: bool

    @property
    def is_marker(self) -> bool:
        """True when the class is one of the six abstract markers."""
        return self.name in MARKER_NAMES

    @property
    def on_base(self) -> bool:
        """True when the class names the entity base among its direct bases and is not a marker."""
        return BASE_ENTITY in self.bases and not self.is_marker

    @property
    def on_marker(self) -> bool:
        """True when the class names one of the six markers among its direct bases and is not one."""
        return any(base in MARKER_NAMES for base in self.bases) and not self.is_marker

    @property
    def is_real(self) -> bool:
        """True when the class is neither a marker nor an abstract intermediate the scan cannot see."""
        return self.on_base or self.on_marker

    @property
    def kind_suffix(self) -> str | None:
        """The kind suffix the name carries, or None when the name carries none."""
        for suffix in KIND_SUFFIXES:
            if self.name.endswith(suffix):
                return suffix
        return None


@dataclass
class Scan:
    """Everything the scan counted, kept together so the report and the totals read from one place."""

    classes: list[EntityClass] = field(default_factory=list)

    @property
    def markers(self) -> list[EntityClass]:
        """The marker declarations found in the tree."""
        return [cls for cls in self.classes if cls.is_marker]

    @property
    def on_base(self) -> list[EntityClass]:
        """Real classes whose direct base is the entity base itself."""
        return [cls for cls in self.classes if cls.on_base]

    @property
    def on_marker(self) -> list[EntityClass]:
        """Classes whose direct base is one of the six markers."""
        return [cls for cls in self.classes if cls.on_marker]

    @property
    def real(self) -> list[EntityClass]:
        """Every real entity and status class the scan can see."""
        return [cls for cls in self.classes if cls.is_real]

    def with_suffix(self) -> list[EntityClass]:
        """Real classes whose name carries one of the six kind suffixes."""
        return [cls for cls in self.real if cls.kind_suffix is not None]

    def without_suffix(self) -> list[EntityClass]:
        """Real classes whose name carries no kind suffix."""
        return [cls for cls in self.real if cls.kind_suffix is None]


def is_skipped(path: Path) -> bool:
    """True when any part of the path is a directory the scan must not read."""
    return any(part in SKIP_DIRS for part in path.parts)


def iter_python_files() -> list[Path]:
    """Return every Python module under the scan roots, in a stable order."""
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        for path in sorted((REPO_ROOT / root_name).rglob("*.py")):
            if not is_skipped(path):
                files.append(path)
    return files


def direct_bases(node: ast.ClassDef) -> tuple[str, ...]:
    """Return the direct base names of a class, without generic parameters."""
    return tuple(ast.unparse(base).split("[", 1)[0].strip() for base in node.bases)


def is_entity_decorated(node: ast.ClassDef) -> bool:
    """True when the class carries the ``@entity`` decorator, with or without arguments."""
    return any(ast.unparse(decorator).startswith("entity") for decorator in node.decorator_list)


def scan_file(path: Path) -> list[EntityClass]:
    """Return the entity declarations of one module; a module that does not parse is reported, not fatal."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as error:
        print(f"  ! skipped {display_path(path)}: {error}", file=sys.stderr)
        return []
    module = display_path(path)
    found: list[EntityClass] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = direct_bases(node)
            if BASE_ENTITY in bases or any(base in MARKER_NAMES for base in bases):
                found.append(EntityClass(module, node.name, bases, is_entity_decorated(node)))
    return found


def display_path(path: Path) -> str:
    """Return the path relative to the repository when it is inside it, the absolute path otherwise."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def scan() -> Scan:
    """Walk the corpus and collect every entity declaration."""
    result = Scan()
    for path in iter_python_files():
        result.classes.extend(scan_file(path))
    return result


def load_map() -> ModuleType | None:
    """Load ``entity_kind_map.py`` beside this file when it exists, otherwise return None."""
    if not MAP_FILE.exists():
        return None
    spec = importlib.util.spec_from_file_location("entity_kind_map", MAP_FILE)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def old_name_occurrences(old_names: tuple[str, ...]) -> dict[str, int]:
    """Count, per file, how often any old class name appears in the scan roots as text."""
    if not old_names:
        return {}
    hits: dict[str, int] = {}
    for path in iter_python_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = sum(text.count(name) for name in old_names)
        if count:
            hits[display_path(path)] = count
    return hits


def format_line(label: str, value: object) -> str:
    """Return one report line with the label padded so the values line up."""
    return f"  {label:<52}{value}"


def report(scan_result: Scan, map_module: ModuleType | None) -> str:
    """Render the scan as the block the quickstart shows, in a fixed order."""
    on_base = scan_result.on_base
    on_marker = scan_result.on_marker
    real = scan_result.real
    with_suffix = scan_result.with_suffix()
    without_suffix = scan_result.without_suffix()
    decorated = [cls for cls in on_base if cls.decorated]
    undeclared = [cls for cls in on_base if not cls.decorated]
    state_classes = [cls for cls in on_marker if STATE_MARKER in cls.bases]

    lines = [
        "Repository scan — entity classes",
        format_line("markers found", f"{len(scan_result.markers)}  {sorted(cls.name for cls in scan_result.markers)}"),
        format_line("classes directly on BaseEntity (real)", len(on_base)),
        format_line("  of them decorated with @entity", len(decorated)),
        format_line("  of them without @entity", len(undeclared)),
        format_line("classes on a marker", len(on_marker)),
        format_line(f"  of them on {STATE_MARKER}", len(state_classes)),
        format_line("real classes (on the base or on a marker)", len(real)),
        format_line("  with a kind suffix", len(with_suffix)),
        format_line("  without a kind suffix", len(without_suffix)),
    ]

    for suffix in KIND_SUFFIXES:
        lines.append(format_line(f"    {suffix}", len([cls for cls in real if cls.kind_suffix == suffix])))

    if undeclared:
        lines.append("  classes without @entity (teaching examples and negative fixtures):")
        lines.extend(f"    {cls.module}::{cls.name}" for cls in sorted(undeclared, key=lambda cls: (cls.module, cls.name)))

    if map_module is None:
        lines.append(format_line("old names still present", "no map yet — the migration has not been planned"))
    else:
        entries = getattr(map_module, "ENTITY_KIND_MAP", ())
        old_names = tuple(entry["old_name"] for entry in entries)
        hits = old_name_occurrences(old_names)
        lines.append(format_line("old names recorded in the map", len(old_names)))
        lines.append(format_line("old names still present", f"{sum(hits.values())} occurrence(s)"))
        lines.extend(f"    {count:>4}  {path}" for path, count in sorted(hits.items()))

    return "\n".join(lines)


def main() -> int:
    """Run the scan and print it, writing the same text to ``--out`` when asked."""
    parser = argparse.ArgumentParser(description="Scan the entity corpus and report its counts.")
    parser.add_argument("--out", type=Path, default=None, help="write the report to this file as well")
    args = parser.parse_args()

    text = report(scan(), load_map())
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"\nwritten to {display_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
