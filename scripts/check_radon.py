#!/usr/bin/env python3
"""
Fail on code over the limits of Radon, which only prints and has no failing threshold of its own.

    uv run --extra dev python scripts/check_radon.py cc    # a function graded D or worse (complexity 21 and above)
    uv run --extra dev python scripts/check_radon.py mi    # a module graded B or worse (index 19 and below)

Every offender is listed. A report that cannot be read fails too, so a broken Radon never reads as a clean tree.

Simplify first. What cannot reasonably be simplified goes into an exception table below, with the reason
beside it. An exception fails the step once it has no reason or its target is no longer over the limit, so
the tables cannot quietly outlive what they excuse.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CC_FAILS = {"D", "E", "F"}
MI_FAILS = {"B", "C"}
STALE = "stale exception: not over the limit any more"
NO_REASON = "exception has no reason"

# (file, name) to why it stays; a method is named ``Class.method``.
FUNCTION_EXCEPTIONS: dict[tuple[str, str], str] = {}
# File to why it stays.
MODULE_EXCEPTIONS: dict[str, str] = {}


class ReportError(Exception):
    """Radon gave no report that can be judged."""


def read_report(kind: str) -> dict[str, Any]:
    """Radon's JSON report over ``packages/``."""
    done = subprocess.run(
        [sys.executable, "-m", "radon", kind, "-j", "packages/"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise ReportError(f"Radon exited {done.returncode}: {done.stderr.strip()}")
    try:
        report = json.loads(done.stdout)
    except json.JSONDecodeError as error:
        raise ReportError(f"Radon did not print JSON: {error}") from error
    if not isinstance(report, dict) or not report:
        raise ReportError("Radon reported no files.")
    return report


def _function_name(block: dict[str, Any]) -> str:
    """A block's name, a method's with its class."""
    return f"{block['classname']}.{block['name']}" if block.get("classname") else block["name"]


def _exception_problems(exceptions: dict[Any, str], over: set[Any], label: Any) -> list[str]:
    """What is wrong with the exceptions themselves."""
    problems = [f"{label(target)} — {NO_REASON}" for target, reason in exceptions.items() if not reason.strip()]
    return problems + [f"{label(target)} — {STALE}" for target in exceptions if target not in over]


def cc_findings(report: dict[str, Any], exceptions: dict[tuple[str, str], str]) -> list[str]:
    """Functions graded D or worse that no exception with a reason excuses, and every broken exception."""
    findings: list[str] = []
    over: set[tuple[str, str]] = set()
    for path, blocks in report.items():
        if isinstance(blocks, dict):
            findings.append(f"{path} — Radon could not read it: {blocks.get('error')}")
            continue
        for block in blocks:
            if block["rank"] not in CC_FAILS:
                continue
            name = _function_name(block)
            over.add((path, name))
            if not exceptions.get((path, name), "").strip():
                findings.append(f"{path}:{block['lineno']} {name} — grade {block['rank']} (complexity {block['complexity']})")
    return findings + _exception_problems(exceptions, over, lambda target: f"{target[0]} {target[1]}")


def mi_findings(report: dict[str, Any], exceptions: dict[str, str]) -> list[str]:
    """Modules graded B or worse that no exception with a reason excuses, and every broken exception."""
    findings: list[str] = []
    over: set[str] = set()
    for path, grade in report.items():
        if "error" in grade:
            findings.append(f"{path} — Radon could not read it: {grade['error']}")
        elif grade["rank"] in MI_FAILS:
            over.add(path)
            if not exceptions.get(path, "").strip():
                findings.append(f"{path} — grade {grade['rank']} (index {grade['mi']:.2f})")
    return findings + _exception_problems(exceptions, over, str)


def main(argv: list[str] | None = None) -> int:
    """Judge one report; 0 when nothing is over the limit, 1 otherwise."""
    parser = argparse.ArgumentParser(description="Fail on code over the limits of Radon.")
    parser.add_argument("kind", choices=("cc", "mi"))
    kind = parser.parse_args(argv).kind
    try:
        report = read_report(kind)
    except ReportError as error:
        print(f"The report could not be read: {error}")
        return 1
    if kind == "cc":
        findings = cc_findings(report, FUNCTION_EXCEPTIONS)
        excepted = [f"{path} {name} — {reason}" for (path, name), reason in FUNCTION_EXCEPTIONS.items()]
    else:
        findings = mi_findings(report, MODULE_EXCEPTIONS)
        excepted = [f"{path} — {reason}" for path, reason in MODULE_EXCEPTIONS.items()]
    for finding in findings:
        print(finding)
    if findings:
        print(f"{len(findings)} finding(s) in {len(report)} files.")
        return 1
    for line in excepted:
        print(f"excepted: {line}")
    print(f"{len(report)} files read, over the limit: 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
