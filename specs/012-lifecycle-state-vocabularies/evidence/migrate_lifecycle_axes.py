"""Rewrite the demo lifecycle declarations as axis classes with status objects.

One-off migration used for phase 5 of `specs/012-lifecycle-state-vocabularies`.
Run from the repository root with `UV_CACHE_DIR=./.uvcache uv run python <this file>`.
"""

from __future__ import annotations

import ast
import importlib
import keyword
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEMO_SRC = REPO / "packages" / "aoa-demo" / "src"

DOMAIN_IMPORT = re.compile(r"^from aoa\.action_machine\.domain import (.+)$", re.M)


def module_name(path: Path) -> str:
    return ".".join(path.relative_to(DEMO_SRC).with_suffix("").parts)


def constant_name(code: str) -> str:
    name = re.sub(r"[^0-9A-Za-z]+", "_", code).strip("_").upper()
    if not name or name[0].isdigit():
        name = f"S_{name}" if name else "STATUS"
    if keyword.iskeyword(name.lower()):
        name += "_"
    return name


def type_name(class_name: str) -> str:
    base = class_name[: -len("Lifecycle")] if class_name.endswith("Lifecycle") else class_name
    return f"{base}StateEntity"


def docstring_text(node: ast.ClassDef) -> str:
    text = ast.get_docstring(node, clean=True)
    if not text:
        return f"Statuses and links of the {node.name} axis."
    return text


def emit_docstring(text: str, indent: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    if len(lines) == 1:
        return f'{indent}"""{lines[0]}"""'
    body = "\n".join(f"{indent}{line}" if line else "" for line in lines)
    return f'{indent}"""\n{body}\n{indent}"""'


def replacement(node: ast.ClassDef, states: list[dict], status_type: str) -> str:
    lines: list[str] = [
        f"class {status_type}(BaseStateEntity):",
        f'    """Status of the {node.name} axis."""',
        "",
        '    sort_order: int = Field(default=0, description="Presentation order")',
        "",
        "",
        f"class {node.name}(Lifecycle, StateVocabulary):",
        emit_docstring(docstring_text(node), "    "),
        "",
    ]
    names: dict[str, str] = {}
    for index, state in enumerate(states, start=1):
        name = constant_name(state["key"])
        names[state["key"]] = name
        lines.append(
            f'    {name} = {status_type}(code={state["key"]!r}, display_name={state["display_name"]!r}, sort_order={index})'
        )
    lines.append("")
    lines.append("    _template = (")
    lines.append("        Lifecycle()")
    for state in states:
        targets = sorted(state["transitions"])
        call = f"        .state({names[state['key']]})"
        if targets:
            call += ".to(" + ", ".join(names[target] for target in targets) + ")"
        call += f".{state['state_type']}()"
        lines.append(call)
    lines.append("    )")
    return "\n".join(lines) + "\n"


def update_imports(source: str, needs_field: bool) -> str:
    match = DOMAIN_IMPORT.search(source)
    assert match is not None, "domain import not found"
    names = sorted({part.strip() for part in match.group(1).split(",")} | {"BaseStateEntity", "StateVocabulary"})
    replacement = "from aoa.action_machine.domain import (\n" + "".join(f"    {name},\n" for name in names) + ")"
    source = source[: match.start()] + replacement + source[match.end() :]
    if needs_field and "from pydantic import" not in source:
        source = source.replace(replacement, "from pydantic import Field\n\n" + replacement, 1)
    elif needs_field and re.search(r"^from pydantic import .*\bField\b", source, re.M) is None:
        # extend an existing pydantic import
        source = re.sub(
            r"^from pydantic import (.+)$",
            lambda m: "from pydantic import " + ", ".join(sorted({p.strip() for p in m.group(1).split(",")} | {"Field"})),
            source,
            count=1,
            flags=re.M,
        )
    return source


def migrate(path: Path) -> int:
    module = importlib.import_module(module_name(path))
    source = path.read_text()
    tree = ast.parse(source)
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and any(isinstance(base, ast.Name) and base.id == "Lifecycle" for base in node.bases)
    ]
    edits: list[tuple[int, int, str]] = []
    for node in classes:
        cls = getattr(module, node.name)
        template = cls._get_template()
        states = [
            {
                "key": info.key,
                "display_name": info.display_name,
                "state_type": info.state_type.value,
                "transitions": sorted(info.transitions),
            }
            for info in template.get_states().values()
        ]
        edits.append((node.lineno, node.end_lineno, replacement(node, states, type_name(node.name))))

    for start, end, text in sorted(edits, reverse=True):
        lines = source.splitlines(keepends=True)
        source = "".join(lines[: start - 1]) + "\n" + text + "".join(lines[end:])

    source = update_imports(source, needs_field=True)
    path.write_text(source)
    return len(classes)


total = 0
for path in sorted(p for p in DEMO_SRC.rglob("*.py") if ".state(" in p.read_text()):
    count = migrate(path)
    total += count
    print(f"{path.relative_to(REPO)}: {count} class(es)")
print("total:", total)
