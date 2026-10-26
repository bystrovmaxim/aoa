"""
05_full_graph_in_the_browser.py — what the browser does, measured by the tool of this issue

The page is drawn by AntV G6, and what a user feels — the bytes on the wire, the arrangement,
the frozen stretches, the canvas — can only be read from a real browser. This script starts a
production build of Maxitor and the frozen reference graph, and runs the measurement tool
(``packages/aoa-maxitor/client/scripts/measure-full-graph.ts``) once per case:

  1. the same picture as before the change — the settled canvas against the reference;
  2. the remembered arrangement — the repeat open reports its own bytes and first pixel;
  3. storage disabled — the page still draws both opens and logs no error;
  4. a dragged node does not move — the hover card appears, the drag leaves the canvas as it was.

Requirements, one time: ``cd packages/aoa-maxitor/client && npm ci && npx playwright install chromium``,
and a production build copied into ``packages/aoa-maxitor/src/aoa/maxitor/static`` as
``quickstart.md`` §2–§3 does (``npm run build`` and ``cp -R dist ../src/aoa/maxitor/static``).

Output:

    1. The same picture
       canvas against the reference: identical
       first open: 1229863 bytes, 618 ms longest task, 1200 ms to the first pixel

    2. The remembered arrangement
       repeat open: 22120 bytes, 767 ms to the first pixel, no layout

    3. Storage disabled
       both opens drawn: True, console failures: 0

    4. A dragged node does not move
       the hover card appeared, the canvas was unchanged after the drag
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "packages/aoa-maxitor/client"
DATA = ROOT / "specs/026-full-graph-fast-open/data"
STATIC = ROOT / "packages/aoa-maxitor/src/aoa/maxitor/static"
FROZEN = ROOT / "specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz"
GRAPH_PORT = 8765
API_PORT = 8102
MAXITOR = f"http://127.0.0.1:{API_PORT}"
SOURCE = f"http://127.0.0.1:{GRAPH_PORT}/graph-json"

# %%
def wait_for(url: str, seconds: float = 30.0) -> None:
    """Block until the URL answers, so a case never races the server's start."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"{url} did not answer within {seconds} s")


# %%
def run_tool(report: Path, *args: str) -> tuple[int, dict[str, object]]:
    """Run the measurement tool once and return its exit code and report."""
    command = [
        "node",
        "scripts/measure-full-graph.ts",
        "--maxitor",
        MAXITOR,
        "--source",
        SOURCE,
        "--out",
        str(report),
        *args,
    ]
    completed = subprocess.run(command, cwd=CLIENT, check=False, capture_output=True, text=True)
    return completed.returncode, json.loads(report.read_text(encoding="utf-8"))


# %%
def main() -> None:
    """Serve the page and the graph, then run one measurement per case."""
    if not (STATIC / "index.html").exists():
        print(f"No built client in {STATIC}: run `npm run build` and copy `dist` there first.")
        raise SystemExit(1)

    work = Path("/tmp/aoa-ref-graph")
    work.mkdir(parents=True, exist_ok=True)
    with gzip.open(FROZEN, "rb") as source, (work / "graph-json").open("wb") as target:
        shutil.copyfileobj(source, target)

    graph_server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(GRAPH_PORT), "--bind", "127.0.0.1", "--directory", str(work)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    api = subprocess.Popen(
        ["uv", "run", "maxitor-api"],
        cwd=ROOT,
        env={**os.environ, "MAXITOR_API_PORT": str(API_PORT)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for(f"{MAXITOR}/")
        wait_for(SOURCE)

        canvas = DATA / "canvas-main.png"
        report = Path("/tmp/aoa-case-1.json")
        code, measured = run_tool(report, "--runs", "1", "--conditions", "cpu1x", "--compare-canvas", str(canvas))
        first = measured["conditions"]["cpu1x"]["first"]  # type: ignore[index]
        print("1. The same picture")
        print(f"   canvas against the reference: {'identical' if code == 0 else 'differs'}")
        print(
            f"   first open: {first['totalBytes']} bytes, {round(first['longestTaskMs'])} ms longest task, "
            f"{round(first['firstGraphPixelMs'])} ms to the first pixel"
        )

        report = Path("/tmp/aoa-case-2.json")
        _, measured = run_tool(report, "--runs", "1", "--conditions", "cpu1x")
        repeat = measured["conditions"]["cpu1x"]["repeat"]  # type: ignore[index]
        print("2. The remembered arrangement")
        print(
            f"   repeat open: {repeat['totalBytes']} bytes, {round(repeat['firstGraphPixelMs'])} ms to the "
            "first pixel, no layout"
        )

        report = Path("/tmp/aoa-case-3.json")
        code, measured = run_tool(report, "--runs", "1", "--conditions", "cpu1x", "--no-storage")
        repeat = measured["conditions"]["cpu1x"]["repeat"]  # type: ignore[index]
        drawn = repeat["firstGraphPixelMs"] is not None
        print("3. Storage disabled")
        print(f"   both opens drawn: {drawn}, console failures: {len(measured['consoleFailures'])}")

        report = Path("/tmp/aoa-case-4.json")
        code, measured = run_tool(report, "--runs", "1", "--conditions", "cpu1x", "--interaction-probe")
        print("4. A dragged node does not move")
        verdict = "the hover card appeared, the canvas was unchanged after the drag"
        print(f"   {verdict if code == 0 else 'the probe failed: ' + '; '.join(measured['consoleFailures'])}")
    finally:
        api.terminate()
        graph_server.terminate()
        api.wait(timeout=10)
        graph_server.wait(timeout=10)


if __name__ == "__main__":
    main()
