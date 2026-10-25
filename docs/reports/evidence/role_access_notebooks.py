"""Execute authorization notebooks in fresh Python processes and compare scripts.
Run: .venv/bin/python docs/reports/evidence/role_access_notebooks.py
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "examples/step_03_authorization_and_roles"


async def execute_notebook(path: Path) -> None:
    """Execute ordered cells with top-level await and save actual streams."""
    notebook = json.loads(path.read_text())
    assert notebook["nbformat"] == 4
    namespace = vars(sys.modules["__main__"])
    count = 0
    flags = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        count += 1
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            compiled = compile("".join(cell["source"]), str(path), "exec", flags=flags)
            flags |= compiled.co_flags & 0x1000000  # Preserve future annotations across cells.
            result = eval(compiled, namespace)  # pylint: disable=eval-used
            if asyncio.iscoroutine(result):
                await result
        cell["execution_count"] = count
        cell["outputs"] = []
        for name, stream in (("stdout", stdout), ("stderr", stderr)):
            if stream.getvalue():
                cell["outputs"].append(
                    {"output_type": "stream", "name": name, "text": stream.getvalue().splitlines(True)}
                )
    notebook["metadata"]["execution"] = {
        "method": "Fresh Python subprocess; ordered cells with top-level await, without a Jupyter kernel."
    }
    path.write_text(json.dumps(notebook, indent=1) + "\n")


def main() -> None:
    """Compare every chapter notebook with its script in separate fresh processes."""
    results = {}
    for notebook_path in sorted(EXAMPLES.glob("*.ipynb")):
        script = notebook_path.with_suffix(".py")
        execution = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True, check=True)
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child", str(notebook_path)], cwd=ROOT, check=True
        )
        notebook = json.loads(notebook_path.read_text())
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        output = "".join(
            "".join(item["text"]) for cell in code_cells for item in cell["outputs"] if item["name"] == "stdout"
        )
        assert output == execution.stdout, (script.name, output, execution.stdout)
        assert [cell["execution_count"] for cell in code_cells] == list(range(1, len(code_cells) + 1))
        results[script.stem] = {
            "script": str(script.relative_to(ROOT)),
            "notebook": str(notebook_path.relative_to(ROOT)),
            "code_cells": len(code_cells),
            "outputs_match": True,
            "stdout": output,
            "script_stderr": execution.stderr,
        }
        print(script.stem + ": outputs match")
    Path(__file__).with_name("role-access-execution.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"{len(results)} script/notebook pairs passed.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        asyncio.run(execute_notebook(Path(sys.argv[2])))
    else:
        main()
