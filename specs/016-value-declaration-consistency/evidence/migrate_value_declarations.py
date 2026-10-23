# specs/016-value-declaration-consistency/evidence/migrate_value_declarations.py
"""
Rewrite class-name value declarations to ``value(...)``, with a count guard.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The feature removes the hidden class-name alias: while the class body runs, the
class's own name resolved to a declaration factory. This tool rewrites the
authored form to ``value(...)``, adds the import it needs and drops the
undefined-name suppressions that existed only for the alias.

Three edits per file, and nothing else:

1. ``NAME = <Owner>Entity(`` becomes ``NAME = value(`` — only for an uppercase
   target inside a class body whose base name ends in ``EnumEntity`` or
   ``StateEntity``, and only when ``<Owner>`` is that same class, which is what
   the alias made possible;
2. ``value`` joins the module's ``from aoa.action_machine.domain import ...``, or
   a new import is inserted after the last module-level import;
3. ``# noqa: F821`` and ``# type: ignore[name-defined]`` are removed from the
   lines the declaration occupies.

Refusal: a declaring class body that calls some *other* class's name, or a file
where the migrated count differs from the count found, aborts the whole run —
a partial rewrite of this migration is not a state anyone should review.

Dry run is the default; ``--write`` applies the edits. Notebooks are handled by
the same rules in a later task, not here.

Run from the repository root::

    uv run python specs/016-value-declaration-consistency/evidence/migrate_value_declarations.py
    uv run python specs/016-value-declaration-consistency/evidence/migrate_value_declarations.py --write
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

_KIND_SUFFIXES = ("EnumEntity", "StateEntity")
_DOMAIN_MODULE = "aoa.action_machine.domain"
_SUPPRESSION = re.compile(r"\s*#\s*(?:noqa:\s*F821|type:\s*ignore\[name-defined\])")
_DEFAULT_PATHS = ("packages", "examples")


@dataclass(frozen=True)
class Declaration:
    """One class-name declaration found in a class body."""

    owner: str
    start: int
    end: int
    first_line: int
    last_line: int


@dataclass(frozen=True)
class Refusal:
    """A class body that declares with a name its owner does not explain."""

    line: int
    owner: str
    enclosing: str


class _Collector(ast.NodeVisitor):
    """Collect declarations and the class bodies that would refuse the rule."""

    def __init__(self, offsets: list[int]) -> None:
        """Remember the line offsets so an AST position becomes an index."""
        self._offsets = offsets
        self.declarations: list[Declaration] = []
        self.refusals: list[Refusal] = []
        self._enclosing: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Enter a declaring class body, then leave it."""
        declaring = any(isinstance(base, ast.Name) and base.id.endswith(_KIND_SUFFIXES) for base in node.bases)
        if declaring:
            self._enclosing.append(node.name)
        self.generic_visit(node)
        if declaring:
            self._enclosing.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Record an uppercase assignment to a kind constructor inside a declaring body."""
        self._visit_assignment(node.targets, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Record the same shape when the target carries an annotation."""
        self._visit_assignment([node.target], node.value, node.lineno)
        self.generic_visit(node)

    def _visit_assignment(self, targets: list[ast.expr], value: ast.expr | None, lineno: int) -> None:
        """Record one assignment when it is a declaration in a declaring body."""
        if not self._enclosing or not isinstance(value, ast.Call):
            return
        func = value.func
        if not isinstance(func, ast.Name) or not func.id.endswith(_KIND_SUFFIXES):
            return
        if not all(isinstance(target, ast.Name) and target.id.isupper() for target in targets):
            return
        if func.id != self._enclosing[-1]:
            self.refusals.append(Refusal(line=lineno, owner=func.id, enclosing=self._enclosing[-1]))
            return
        assert func.end_lineno is not None and func.end_col_offset is not None
        self.declarations.append(
            Declaration(
                owner=func.id,
                start=self._absolute(func.lineno, func.col_offset),
                end=self._absolute(func.end_lineno, func.end_col_offset),
                first_line=lineno,
                last_line=value.end_lineno or lineno,
            )
        )

    def _absolute(self, lineno: int, col: int) -> int:
        """Turn an AST position into an absolute index into the file text."""
        return self._offsets[lineno - 1] + col


def _line_offsets(text: str) -> list[int]:
    """Return the absolute index at which every line starts."""
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _python_files(paths: list[str]) -> Iterator[Path]:
    """Yield the Python files under the given roots, in a stable order."""
    for root in paths:
        for path in sorted(Path(root).rglob("*.py")):
            if "__pycache__" in path.parts or ".venv" in path.parts:
                continue
            yield path


def _strip_suppressions(lines: list[str], declaration: Declaration) -> None:
    """Remove the alias-only suppressions from the lines one declaration occupies."""
    for index in range(declaration.first_line - 1, min(declaration.last_line, len(lines))):
        lines[index] = _SUPPRESSION.sub("", lines[index]).rstrip() + "\n" if lines[index].endswith("\n") else (
            _SUPPRESSION.sub("", lines[index]).rstrip()
        )


def _rewrite_declarations(text: str, declarations: list[Declaration]) -> str:
    """Replace each owner name with ``value``, from the last declaration backwards."""
    for declaration in sorted(declarations, key=lambda item: item.start, reverse=True):
        text = text[: declaration.start] + "value" + text[declaration.end :]
    return text


def _add_domain_import(text: str, tree: ast.Module) -> tuple[str, bool]:
    """Add ``value`` to the domain import, or insert one; return the text and whether it changed."""
    lines = text.splitlines(keepends=True)
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    for node in imports:
        if not isinstance(node, ast.ImportFrom) or node.module != _DOMAIN_MODULE:
            continue
        names = {alias.name for alias in node.names}
        if "value" in names:
            return text, False
        open_index = node.lineno - 1
        close_index = (node.end_lineno or node.lineno) - 1
        if close_index > open_index:
            first_name = lines[open_index + 1] if len(lines) > open_index + 1 else ""
            indent = re.match(r"\s*", first_name).group(0) if first_name.strip() else "    "
            lines.insert(close_index, f"{indent}value,\n")
            return "".join(lines), True
        lines[open_index] = lines[open_index].rstrip("\n").rstrip() + ", value\n"
        return "".join(lines), True
    if not imports:
        return text, False
    last = max(imports, key=lambda node: node.end_lineno or node.lineno)
    insert_at = (last.end_lineno or last.lineno)
    lines.insert(insert_at, f"from {_DOMAIN_MODULE} import value\n")
    return "".join(lines), True


@dataclass(frozen=True)
class Plan:
    """One file's rewrite, held until the whole run has been checked."""

    path: Path
    declarations: int
    import_added: bool
    text: str


def _plan(path: Path) -> tuple[Plan | None, list[Refusal]]:
    """Compute one file's rewrite without touching it; return refusals as found."""
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        raise SystemExit(f"{path}: cannot parse: {error}") from error
    collector = _Collector(_line_offsets(text))
    collector.visit(tree)
    if collector.refusals:
        return None, collector.refusals
    if not collector.declarations:
        return None, []
    rewritten = _rewrite_declarations(text, collector.declarations)
    lines = rewritten.splitlines(keepends=True)
    for declaration in collector.declarations:
        _strip_suppressions(lines, declaration)
    rewritten = "".join(lines)
    rewritten, imported = _add_domain_import(rewritten, ast.parse(rewritten))
    return Plan(path=path, declarations=len(collector.declarations), import_added=imported, text=rewritten), []


def main() -> None:
    """Rewrite every declaration under the given roots, or report what would change."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=list(_DEFAULT_PATHS), help="roots to scan")
    parser.add_argument("--write", action="store_true", help="apply the edits instead of reporting them")
    arguments = parser.parse_args()
    plans: list[Plan] = []
    refusals: list[tuple[Path, Refusal]] = []
    for path in _python_files(arguments.paths):
        plan, refused = _plan(path)
        if refused:
            refusals.extend((path, refusal) for refusal in refused)
        elif plan is not None:
            plans.append(plan)
    for path, refusal in refusals:
        print(
            f"REFUSED {path}:{refusal.line}: class body {refusal.enclosing} declares with {refusal.owner}; "
            "the owner must be the enclosing class, so this file needs a human",
            file=sys.stderr,
        )
    if refusals:
        print(f"refused: {len(refusals)} case(s); nothing was written", file=sys.stderr)
        raise SystemExit(1)
    verb = "rewrote" if arguments.write else "would rewrite"
    for plan in plans:
        if arguments.write:
            plan.path.write_text(plan.text, encoding="utf-8")
        import_note = ""
        if plan.import_added:
            import_note = ", added the value import" if arguments.write else ", would add the value import"
        print(f"{plan.path}: {verb} {plan.declarations} declaration(s){import_note}")
    mode = "rewritten" if arguments.write else "found"
    imports = sum(1 for plan in plans if plan.import_added)
    print(
        f"{mode}: {sum(plan.declarations for plan in plans)} declaration(s) in {len(plans)} file(s); "
        f"{imports} import(s) {'updated' if arguments.write else 'would be updated'}; 0 refusal(s)"
    )


if __name__ == "__main__":
    main()
