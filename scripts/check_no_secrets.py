#!/usr/bin/env python3
"""
Fail when a tracked file is a secrets file by its name, or holds a value detect-secrets has not been told about.

Two questions, because they fail differently. A tracked `.env` is wrong whatever it holds, so its name
is enough. Anything else is scanned, and what the scan finds is compared with `.secrets.baseline`: the
reviewed findings, all of them false alarms such as a test's stand-in token.

The baseline is compared by file, type and hash, never by line, so moving a reviewed value does not
fail the run, and the script only reads it. `detect-secrets-hook` would rewrite it on every moved line.

After reviewing a new false alarm, record it:

    uv run --extra dev python scripts/check_no_secrets.py --update
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / ".secrets.baseline"
SECRET_FILE = re.compile(r"(^|/)(\.env(\.(?!example$)[^/]+)?|[^/]+\.(pem|key))$")
# Generated text full of hashes, and the places where sample values are the point.
NOT_SCANNED = re.compile(
    r"^(tests/|docs/|archive/|specs/|\.specify/integrations/|\.secrets\.baseline$)|(\.ipynb|graph\.json)$"
)

Finding = tuple[str, str, str]


def _tracked_files() -> list[str]:
    """Every path git tracks or has staged."""
    output = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [path for path in output.split("\0") if path]


def secret_files(paths: list[str]) -> list[str]:
    """The paths that are secrets files by their name alone."""
    return [path for path in paths if SECRET_FILE.search(path)]


def scanned_files(paths: list[str]) -> list[str]:
    """The paths the scan reads: on disk, and outside what ``NOT_SCANNED`` leaves out."""
    return [path for path in paths if not NOT_SCANNED.search(path) and (ROOT / path).is_file()]


def _scan(paths: list[str]) -> dict[str, list[dict[str, object]]]:
    """Run detect-secrets over ``paths`` and return its results, file by file."""
    done = subprocess.run(
        ["detect-secrets", "scan", *paths], cwd=ROOT, capture_output=True, text=True, check=True
    )
    results: dict[str, list[dict[str, object]]] = json.loads(done.stdout)["results"]
    return results


def _findings(results: dict[str, list[dict[str, object]]]) -> set[Finding]:
    """The results as (file, type, hash), the identity of one finding."""
    return {(path, str(item["type"]), str(item["hashed_secret"])) for path, items in results.items() for item in items}


def new_findings(found: set[Finding], reviewed: set[Finding]) -> list[Finding]:
    """The findings that were not reviewed, in a stable order."""
    return sorted(found - reviewed)


def main() -> int:
    """Answer both questions; with ``--update``, record today's findings as reviewed."""
    paths = _tracked_files()
    forbidden = secret_files(paths)
    for path in forbidden:
        print(f"FAIL {path} is a secrets file and must not be tracked: git rm --cached {path}")

    results = _scan(scanned_files(paths))
    if sys.argv[1:] == ["--update"]:
        BASELINE.write_text(json.dumps({"results": results}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Recorded {len(_findings(results))} reviewed findings in {BASELINE.name}")
        return 1 if forbidden else 0

    reviewed = _findings(json.loads(BASELINE.read_text(encoding="utf-8"))["results"])
    unknown = new_findings(_findings(results), reviewed)
    for path, kind, _ in unknown:
        print(f"FAIL {path}: {kind}. Remove it, or if it is a false alarm, review it and run --update.")
    return 1 if forbidden or unknown else 0


if __name__ == "__main__":
    sys.exit(main())
