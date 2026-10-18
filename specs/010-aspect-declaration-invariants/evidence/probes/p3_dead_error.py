# specs/010-aspect-declaration-invariants/evidence/probes/p3_dead_error.py
"""Probe 3: whether anything raises ``ActionResultTypeError`` in the package."""
import pathlib
import re

SOURCE = pathlib.Path("packages/aoa-action-machine/src")
raisers = [path for path in SOURCE.rglob("*.py") if re.search(r"raise\s+ActionResultTypeError", path.read_text())]
mentions = sorted(
    f"{path}:{number}"
    for path in SOURCE.rglob("*.py")
    for number, line in enumerate(path.read_text().splitlines(), 1)
    if "ActionResultTypeError" in line
)

print("raise sites:", len(raisers))
for path in raisers:
    print("  ", path)
print("mentions:", len(mentions))
for mention in mentions:
    print("  ", mention)
