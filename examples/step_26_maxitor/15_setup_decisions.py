"""Show wizard decisions accepted or refused without changing graph commands."""

# %% Prepare an isolated graph and a configuration without setup metadata.
import json
import shlex
import sys
import tempfile
from pathlib import Path

from maxitor.graph_builder.cli import main
from maxitor.graph_builder.config import ConfigRefused, read_config

workspace = tempfile.TemporaryDirectory(prefix="graph-setup-example-")
folder = Path(workspace.name)
config = folder / "graph-builder.toml"
producer = folder / "produce.py"
producer.write_text('print(\'{"schema_version":"1.1","nodes":[],"edges":[]}\')\n', encoding="utf-8")
build = shlex.join([sys.executable, str(producer)])
base = f'graph_builder = "1.0"\n\n[[graph]]\nname = "tiny"\nbuild = {json.dumps(build)}\nfile = "graph.json"\n'
config.write_text(base, encoding="utf-8")

# %% Legacy configurations still write and check their graphs.
print("Legacy configuration:")
assert main(["write", "--config", str(config)]) == 0
assert main(["check", "--config", str(config)]) == 0

# %% Persist decisions without changing graph output or claiming version enforcement.
config.write_text(
    base + '\n[setup]\nskill = "2"\ndecided = ["local-update"]\ndeferred = ["local-update"]\n',
    encoding="utf-8",
)
print("Optional update deferred; mandatory version remains undecided:")
before = config.read_bytes()
assert main(["check", "--config", str(config)]) == 0
assert config.read_bytes() == before
print("Setup decisions preserved: True")
print("A green graph check is not evidence of release-tag enforcement.")


# %% Required items cannot be deferred; optional deferrals must be decided.
def show_refusal(label: str, decided: list[str], deferred: list[str]) -> None:
    """Print the field that rejects one invalid decision record."""
    config.write_text(
        base + f'\n[setup]\nskill = "2"\ndecided = {json.dumps(decided)}\ndeferred = {json.dumps(deferred)}\n',
        encoding="utf-8",
    )
    try:
        read_config(config)
    except ConfigRefused as exc:
        print(f"{label}: refused {exc.field}")
    else:
        raise AssertionError(f"Expected refusal: {label}")


show_refusal("Deferred mandatory version", ["version-tags"], ["version-tags"])
show_refusal("Deferred mandatory config", ["config"], ["config"])
show_refusal("Deferred mandatory graph", ["graph:tiny"], ["graph:tiny"])
show_refusal("Deferred mandatory exporter", ["exporter:tiny"], ["exporter:tiny"])
show_refusal("Undecided local update", [], ["local-update"])
show_refusal("Undecided CI check", [], ["ci-graph-check"])
show_refusal("Unknown audit item", ["unrecognized"], [])

# %% An older checklist and an explicit completion record remain readable.
for revision, decided in [("1", []), ("2", ["config", "graph:tiny", "exporter:tiny", "version-tags"])]:
    config.write_text(
        base + f'\n[setup]\nskill = "{revision}"\ndecided = {json.dumps(decided)}\ndeferred = []\n',
        encoding="utf-8",
    )
    print(f"Checklist {revision}: {len(read_config(config))} graph; audit must recheck recorded decisions")
workspace.cleanup()
