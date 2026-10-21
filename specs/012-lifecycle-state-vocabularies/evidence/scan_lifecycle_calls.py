# specs/012-lifecycle-state-vocabularies/evidence/scan_lifecycle_calls.py
"""
Scan the demo lifecycle corpus and record its "before" state.

Walks `packages/aoa-demo/src`, imports every module that declares a `Lifecycle`
subclass, and records each declaration's state codes, labels, classification
and `(from, to)` transition pairs. Totals are compared against a textual count
of `.state(` / `.to(` so that the recorded numbers can be checked independently.

Usage:
    UV_CACHE_DIR=./.uvcache uv run python specs/012-lifecycle-state-vocabularies/evidence/scan_lifecycle_calls.py
    UV_CACHE_DIR=./.uvcache uv run python .../scan_lifecycle_calls.py --out /tmp/baseline.json
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_SRC = REPO_ROOT / "packages" / "aoa-demo" / "src"
DEFAULT_OUT = Path(__file__).resolve().parent / "baseline.json"

_STATE_CALL = re.compile(r"\.state\(")
_TO_CALL = re.compile(r"\.to\(")


def display_path(path: Path) -> str:
    """Return the path relative to the repository when it is inside it, the absolute path otherwise."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def module_name(path: Path, demo_src: Path) -> str:
    """Return the dotted module name for a file under the demo package."""
    relative = path.relative_to(demo_src).with_suffix("")
    return ".".join(relative.parts)


def lifecycle_classes(module: Any) -> list[type]:
    """Return the Lifecycle subclasses defined by this module, in source order."""
    from aoa.action_machine.domain import Lifecycle

    found = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Lifecycle) and obj is not Lifecycle and obj.__module__ == module.__name__
    ]
    return sorted(found, key=lambda cls: inspect.getsourcelines(cls)[1])


def chain_record(cls: type, module_path: Path) -> dict[str, Any]:
    """One lifecycle declaration: its states, labels and transition pairs."""
    template = cls._get_template()
    if template is None:
        return {"declaration": cls.__qualname__, "error": "no _template"}

    states = template.get_states()
    return {
        "declaration": cls.__qualname__,
        "module": cls.__module__,
        "file": display_path(module_path),
        "private": cls.__name__.startswith("_"),
        "states": [
            {
                "key": info.key,
                "display_name": info.display_name,
                "state_type": info.state_type.value,
                "transitions": sorted(info.transitions),
            }
            for info in states.values()
        ],
    }


def sales_order_row() -> dict[str, Any]:
    """The measured 'before' for one state row and the FSM display name it yields."""
    from aoa.action_machine.graph.nodes.lifecycle_graph_node import LifeCycleGraphNode
    from aoa.demo.model.store.entities.sales_core import SalesOrderEntity
    from aoa.demo.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle

    node = LifeCycleGraphNode(SalesOrderEntity, "lifecycle", SalesOrderLifecycle)
    state = next(s for s in node.states if s.node_obj.state_key == "payment_pending")
    template = SalesOrderLifecycle._get_template()
    info = template.get_states()["payment_pending"]
    return {
        "state_row": state.to_dict(),
        "declared_display_name_in_StateInfo": info.display_name,
        "fsm_state_item_as_maxitor_builds_it": {
            "key": info.key,
            "display_name": state.label,
            "state_type": info.state_type.value,
            "transitions": sorted(info.transitions),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where to write the JSON baseline")
    parser.add_argument("--demo-src", type=Path, default=DEMO_SRC, help="demo package source tree to scan")
    args = parser.parse_args()
    demo_src = args.demo_src.resolve()

    files = sorted(p for p in demo_src.rglob("*.py") if _STATE_CALL.search(p.read_text()))
    textual_states = sum(len(_STATE_CALL.findall(p.read_text())) for p in files)
    textual_transitions = sum(len(_TO_CALL.findall(p.read_text())) for p in files)

    chains: list[dict[str, Any]] = []
    for path in files:
        name = module_name(path, demo_src)
        try:
            module = importlib.import_module(name)
        except Exception as exc:
            chains.append({"module": name, "file": display_path(path), "error": repr(exc)})
            continue
        for cls in lifecycle_classes(module):
            chains.append(chain_record(cls, path))

    failures = [c for c in chains if "error" in c]
    states = sum(len(c.get("states", [])) for c in chains)
    transitions = sum(len(s["transitions"]) for c in chains for s in c.get("states", []))

    payload = {
        "generated_by": "scan_lifecycle_calls.py",
        "corpus": {
            "files_with_state_calls": len(files),
            "declarations": len(chains),
            "private_declarations": sum(1 for c in chains if c.get("private")),
            "states_from_templates": states,
            "transition_pairs_from_templates": transitions,
            "state_calls_textual": textual_states,
            "to_calls_textual": textual_transitions,
            "failures": len(failures),
        },
        "state_row_before": sales_order_row(),
        "chains": chains,
    }

    out_path = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    corpus = payload["corpus"]
    print(f"files with .state( calls : {corpus['files_with_state_calls']}")
    print(f"lifecycle declarations   : {corpus['declarations']} ({corpus['private_declarations']} private)")
    print(f"states (from templates)  : {corpus['states_from_templates']}")
    print(f"transition pairs         : {corpus['transition_pairs_from_templates']}")
    print(f".state( textual / .to(   : {corpus['state_calls_textual']} / {corpus['to_calls_textual']}")
    print(f"import failures          : {corpus['failures']}")
    print(f"state row label          : {payload['state_row_before']['state_row']['label']!r}")
    print(
        "FSM display_name         : "
        f"{payload['state_row_before']['fsm_state_item_as_maxitor_builds_it']['display_name']!r} "
        f"(StateInfo declares {payload['state_row_before']['declared_display_name_in_StateInfo']!r})"
    )
    print(f"baseline written         : {display_path(out_path)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
