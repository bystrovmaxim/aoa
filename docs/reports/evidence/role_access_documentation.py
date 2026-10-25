"""Check role-access documentation links, standalone programs and shown outputs.
Run: .venv/bin/python docs/reports/evidence/role_access_documentation.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
PAGES = (
    "docs/index.md",
    "docs/how-to/authoring-action.md",
    "docs/how-to/roles-and-object-rules.md",
    "docs/reference/access-control.md",
    "docs/reference/glossary.md",
    "docs/reference/intents-and-invariants.md",
    "docs/tutorials/step-03-authorization-and-roles.md",
    "docs/reports/role-access-verification.md",
)


def anchors(path: Path) -> set[str]:
    """Read Markdown headings using GitHub-style anchor spelling."""
    text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
    names = set(re.findall(r'<a\s+(?:name|id)=[\'"]([^\'"]+)', text))
    occurrences: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.M):
        heading = re.sub(r"<[^>]+>", "", heading)
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = occurrences.get(slug, 0)
        occurrences[slug] = count + 1
        names.add(slug if count == 0 else slug + "-" + str(count))
    return names


def check_links(path: Path) -> int:
    """Check local Markdown and HTML file links and heading fragments."""
    source = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
    links = re.findall(r"\]\(([^\s)]+)\)", source)
    links += re.findall(r'(?:href|src)="([^"]+)"', source)
    count = 0
    for url in links:
        if re.match(r"[a-z]+:", url):
            continue
        name, _, fragment = unquote(url.strip("<>")).partition("#")
        if name.endswith(("_draft.md", ".ru.md")):
            continue
        target = (path.parent / name).resolve() if name else path
        assert "aoa-demo" not in target.parts
        assert target.exists(), (path.relative_to(ROOT), url)
        if fragment and target.suffix == ".md":
            assert fragment in anchors(target), (path.relative_to(ROOT), url, sorted(anchors(target)))
        count += 1
    return count


def main() -> None:
    """Execute published complete programs and validate local navigation."""
    results = json.loads(Path(__file__).with_name("role-access-execution.json").read_text())
    link_count = sum(check_links(ROOT / name) for name in PAGES)
    mappings = {
        "docs/how-to/roles-and-object-rules.md": "02_object_rule",
        "docs/tutorials/step-03-authorization-and-roles.md": "03_shared_object_rule",
    }
    executed = 0
    with tempfile.TemporaryDirectory(prefix="aoa-role-docs-") as temporary:
        for page, scenario in mappings.items():
            text = (ROOT / page).read_text()
            blocks = re.findall(r"```python\n(.*?)\n```", text, flags=re.S)
            assert len(blocks) == 1
            for code in blocks:
                path = Path(temporary) / (scenario + ".py")
                path.write_text(code + "\n")
                run = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=True, cwd=ROOT)
                assert run.stdout == results[scenario]["stdout"]
                assert "```text\n" + run.stdout + "```" in text
                executed += 1
    tutorial = (ROOT / "docs/tutorials/step-03-authorization-and-roles.md").read_text()
    for scenario in ("14_guest_and_any", "07_three_answers", "13_cascade"):
        assert "```text\n" + results[scenario]["stdout"] + "```" in tutorial
    guide = (ROOT / "docs/how-to/roles-and-object-rules.md").read_text()
    assert "```text\n" + results["07_three_answers"]["stdout"] + "```" in guide
    reference = (ROOT / "docs/reference/access-control.md").read_text()
    for line in results["24_role_declarations_and_migration"]["stdout"].splitlines():
        if line.startswith("RoleSpecTypeError:"):
            assert line in reference
    evidence = {
        "pages": len(PAGES),
        "local_links": link_count,
        "standalone_programs": executed,
        "shown_outputs": "matched",
    }
    Path(__file__).with_name("role-access-documentation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"{len(PAGES)} pages, {link_count} local links, {executed} standalone programs: passed.")


if __name__ == "__main__":
    main()
