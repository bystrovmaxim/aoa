# tests/examples/harness.py
"""
Example harness — what the example checks read, compare and run.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The documentation's examples are scripts, notebooks and the Python blocks of
its pages. This module finds the pages a reader opens, splits a page into its
fenced blocks, reads a block's fragment mark and the output the page shows for
it, masks the values that differ on every run, and runs a page's blocks in
order in one process, capturing what each one prints.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    git ls-files ──► pages_in_scope() ──► page_blocks(path) ──► Block
                                                                  │
                     run_page(blocks) ◄── runnable Python blocks ─┘
                            │  one subprocess, blocks in page order
                            ▼
                     BlockRun (printed text or error) ──► mask() ──► compare

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

A fragment carries ``# Fragment: <reason>.`` as its first line: visible on the
page, kept when copied, and readable without a Markdown extension. A ``text``
block is a Python block's shown output when nothing but blank lines, or one
lead-in sentence ending with a colon, stands between the two; a block with no
language counts as ``text``. A block that opens with a docstring is a whole
module and runs in a process of its own.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = REPO_ROOT / "examples"
PAGE_TIMEOUT_SECONDS = 300

FRAGMENT_PREFIX = "# Fragment:"
_FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,})(?P<info>[^`]*)$")

_MASKS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"errors\.pydantic\.dev/[0-9][0-9.]*/"), "errors.pydantic.dev/<v>/"),
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "<jwt>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<uuid>"),
    (re.compile(r"\b[0-9a-f]{32}\b"), "<hex>"),
    (re.compile(r"\b([a-z]+-)(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{8}\b"), r"\1<id>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<addr>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<time>"),
    (re.compile(r"\b\d+(?:\.\d+)?\s?(?:ms|µs|us|ns|s)\b"), "<duration>"),
    (re.compile(r"(localhost|127\.0\.0\.1|\[::1\]):\d+"), r"\1:<port>"),
    (re.compile(r"(duration\w*[\"']?\s*[:=]\s*)\d+(?:\.\d+)?"), r"\1<n>"),
    (re.compile(r"\b1[6-9]\d{8}\b"), "<epoch>"),
)


@dataclass(frozen=True)
class Block:
    """One fenced block of a page."""

    page: Path
    line: int
    language: str
    code: str
    shown_output: str | None = None

    @property
    def fragment_reason(self) -> str | None:
        """Reason after ``# Fragment:`` on the first line, or ``None`` for a block meant to run."""
        first = next((line.strip() for line in self.code.splitlines() if line.strip()), "")
        if not first.startswith(FRAGMENT_PREFIX):
            return None
        return first[len(FRAGMENT_PREFIX) :].strip()

    @property
    def where(self) -> str:
        """Page path and line, as a failure names the block."""
        page = self.page.relative_to(REPO_ROOT) if self.page.is_relative_to(REPO_ROOT) else self.page
        return f"{page.as_posix()}:{self.line}"


@dataclass(frozen=True)
class BlockRun:
    """What one block printed, or the error that stopped it."""

    block: Block
    printed: str
    error: str | None


def pages_in_scope() -> list[Path]:
    """Tracked pages a reader opens: ``docs/``, the root README and every package README."""
    listed = subprocess.run(
        ["git", "ls-files", "docs", "README.md", "packages"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    pages = []
    for name in listed:
        path = Path(name)
        if path.suffix != ".md" or path.name.endswith("_draft.md") or "CHANGELOG" in path.name:
            continue
        if name.startswith("packages/") and path.name != "README.md":
            continue
        pages.append(REPO_ROOT / path)
    return sorted(pages)


def page_blocks(page: Path) -> list[Block]:
    """Fenced blocks of ``page`` in order, each Python block paired with its shown output."""
    lines = page.read_text(encoding="utf-8").splitlines()
    raw: list[tuple[int, int, str, str]] = []
    index = 0
    while index < len(lines):
        opening = _FENCE.match(lines[index])
        if not opening:
            index += 1
            continue
        indent, fence = opening.group("indent"), opening.group("fence")
        language = opening.group("info").strip().split(" ")[0].lower()
        body: list[str] = []
        end = index + 1
        while end < len(lines):
            closing = _FENCE.match(lines[end])
            if closing and closing.group("fence").startswith(fence) and not closing.group("info").strip():
                break
            body.append(lines[end][len(indent) :] if lines[end].startswith(indent) else lines[end].lstrip())
            end += 1
        raw.append((index + 1, end + 1, language, "\n".join(body) + "\n"))
        index = end + 1
    blocks = []
    for position, (start, stop, language, code) in enumerate(raw):
        shown = None
        if language == "python" and position + 1 < len(raw):
            next_start, _, next_language, next_code = raw[position + 1]
            between = lines[stop : next_start - 1]
            if next_language in ("text", "") and _is_lead_in(between):
                shown = next_code
        blocks.append(Block(page=page, line=start, language=language, code=code, shown_output=shown))
    return blocks


def _is_lead_in(between: list[str]) -> bool:
    """Whether the lines between two blocks are blank, or one sentence ending with a colon."""
    paragraphs = [part for part in "\n".join(line.strip() for line in between).strip().split("\n\n") if part]
    if not paragraphs:
        return True
    return len(paragraphs) == 1 and paragraphs[0].endswith(":")


def mask(text: str) -> str:
    """``text`` with values that differ on every run replaced by placeholders, trailing spaces dropped."""
    for pattern, placeholder in _MASKS:
        text = pattern.sub(placeholder, text)
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


_DRIVER = r"""
import ast, asyncio, contextlib, io, json, sys, traceback, types
blocks = json.load(sys.stdin)
page_module = types.ModuleType("__main__")
sys.modules["__main__"] = page_module
namespace = page_module.__dict__
loop = asyncio.new_event_loop()
results = []
for where, code in blocks:
    buffer = io.StringIO()
    error = None
    try:
        compiled = compile(code, where, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        with contextlib.redirect_stdout(buffer):
            outcome = eval(compiled, namespace)
            if asyncio.iscoroutine(outcome):
                loop.run_until_complete(outcome)
    except BaseException:
        error = traceback.format_exc(limit=-3)
    results.append({"printed": buffer.getvalue(), "error": error})
    if error:
        break
sys.__stdout__.write("\n@@RESULTS@@" + json.dumps(results))
"""


def is_whole_module(block: Block) -> bool:
    """Whether ``block`` is a whole module, opening with its docstring, that runs in a process of its own."""
    return block.code.lstrip().startswith(('"""', "'''"))


def run_page(blocks: list[Block]) -> list[BlockRun]:
    """Run ``blocks`` in page order: whole modules each alone, the rest together; stop at the first error."""
    runs: list[BlockRun] = []
    together = [block for block in blocks if not is_whole_module(block)]
    together_runs = {id(run.block): run for run in _run_together(together)} if together else {}
    for block in blocks:
        run = _run_together([block])[0] if is_whole_module(block) else together_runs.get(id(block))
        if run is None:
            break
        runs.append(run)
        if run.error:
            break
    return runs


def _run_together(blocks: list[Block]) -> list[BlockRun]:
    """Run ``blocks`` in order in one process from the repository root; stop at the first error."""
    payload = json.dumps([[block.where, block.code] for block in blocks])
    finished = subprocess.run(
        [sys.executable, "-c", _DRIVER],
        input=payload,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=PAGE_TIMEOUT_SECONDS,
    )
    marker = finished.stdout.rfind("@@RESULTS@@")
    if marker < 0:
        return [BlockRun(block=blocks[0], printed="", error=finished.stderr[-2000:] or "the page's process died")]
    results = json.loads(finished.stdout[marker + len("@@RESULTS@@") :])
    return [BlockRun(block=block, printed=result["printed"], error=result["error"]) for block, result in zip(blocks, results, strict=False)]


def runnable_python_blocks(page: Path) -> list[Block]:
    """Python blocks of ``page`` that carry no fragment mark."""
    return [block for block in page_blocks(page) if block.language == "python" and block.fragment_reason is None]


# What each imported module needs from PyPI, matched by the longest module prefix.
PYPI_FOR_MODULE: dict[str, tuple[str, ...]] = {
    "aoa.action_machine": ("aoa-action-machine",),
    "aoa.action_machine.resources.postgres": ("aoa-action-machine[postgres]",),
    "aoa.fastapi": ("aoa-fastapi-adapter",),
    "aoa.mcp": ("aoa-mcp-adapter",),
    "aoa.langgraph": ("aoa-langgraph",),
    "aoa.otel": ("aoa-otel",),
    "aoa.ocel": ("aoa-ocel",),
    "maxitor": ("maxitor",),
    "maxitor.web": ("maxitor[web]",),
    "pydantic": ("aoa-action-machine",),
    "pydantic_core": ("aoa-action-machine",),
    "jsonschema": ("aoa-action-machine",),
    "asyncpg": ("aoa-action-machine[postgres]",),
    "jwt": ("aoa-action-machine[jwt]",),
    "cryptography": ("aoa-action-machine[jwt]",),
    "fastapi": ("aoa-fastapi-adapter",),
    "fastapi.testclient": ("aoa-fastapi-adapter", "httpx"),
    "starlette": ("aoa-fastapi-adapter",),
    "starlette.testclient": ("aoa-fastapi-adapter", "httpx"),
    "httpx": ("httpx",),
    "mcp": ("aoa-mcp-adapter",),
    "langgraph": ("aoa-langgraph",),
    "opentelemetry": ("aoa-otel",),
}

_REQUIREMENT = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)(?:\[(?P<extras>[^\]]*)\])?")


def imported_modules(sources: list[str]) -> set[str]:
    """Absolute modules the code ``sources`` import; shell and magic lines are left out."""
    modules: set[str] = set()
    for source in sources:
        code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith(("!", "%")))
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module)
    return modules


def requirements_for(module: str) -> tuple[str, ...] | None:
    """PyPI requirements ``module`` needs: ``()`` for the standard library, ``None`` when unknown."""
    if module.split(".")[0] in sys.stdlib_module_names:
        return ()
    parts = module.split(".")
    for length in range(len(parts), 0, -1):
        prefix = ".".join(parts[:length])
        if prefix in PYPI_FOR_MODULE:
            return PYPI_FOR_MODULE[prefix]
    return None


def install_line(requirements: set[str]) -> str:
    """The ``!pip install`` line for ``requirements``, a bare name dropped when an extra of it is there."""
    merged: dict[str, set[str]] = {}
    for requirement in requirements:
        found = _REQUIREMENT.match(requirement)
        assert found is not None, requirement
        extras = {extra.strip() for extra in (found.group("extras") or "").split(",") if extra.strip()}
        merged.setdefault(found.group("name"), set()).update(extras)
    names = []
    for name in sorted(merged, key=lambda item: (not item.startswith("aoa-"), item)):
        extras = merged[name]
        names.append(f'"{name}[{",".join(sorted(extras))}]"' if extras else name)
    return "!pip install -q " + " ".join(names)


def installed_requirements(line: str) -> dict[str, set[str]]:
    """Package names an ``!pip install`` line installs, each with its extras."""
    installed: dict[str, set[str]] = {}
    for token in line.split()[2:]:
        token = token.strip("\"'")
        if token.startswith("-"):
            continue
        found = _REQUIREMENT.match(token)
        if found:
            extras = {extra.strip() for extra in (found.group("extras") or "").split(",") if extra.strip()}
            installed.setdefault(found.group("name").lower(), set()).update(extras)
    return installed


def is_satisfied(requirement: str, installed: dict[str, set[str]]) -> bool:
    """Whether ``installed`` holds ``requirement``, with every extra it names."""
    found = _REQUIREMENT.match(requirement)
    assert found is not None, requirement
    extras = {extra.strip() for extra in (found.group("extras") or "").split(",") if extra.strip()}
    name = found.group("name").lower()
    return name in installed and extras <= installed[name]
