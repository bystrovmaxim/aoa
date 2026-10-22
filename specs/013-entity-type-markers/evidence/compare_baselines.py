# specs/013-entity-type-markers/evidence/compare_baselines.py
"""
Compare two entity baselines: the same classes before and after the migration.

Keys are "module::class" in the file that was captured. The map translates the
"after" keys back to the names the "before" file used, so a rename is not
reported as a removal. Anything the migration must not touch — the scalar
fields, the relation fields with their kind, the lifecycle fields, description
and domain — is compared per class.

Usage:
    UV_CACHE_DIR=./.uvcache uv run python specs/013-entity-type-markers/evidence/compare_baselines.py --before before.json --after after.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib

EVIDENCE = pathlib.Path(__file__).resolve().parent
MAP_FILE = EVIDENCE / "entity_kind_map.py"
COMPARED_KEYS = ("scalars", "relations", "lifecycles", "description", "domain")


def load_map() -> dict[tuple[str, str], str]:
    """Return {(module, new_name): old_name} from the decision table."""
    spec = importlib.util.spec_from_file_location("entity_kind_map", MAP_FILE)
    if spec is None or spec.loader is None:
        raise SystemExit("entity_kind_map.py is not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {(entry["module"], entry["new_name"]): entry["old_name"] for entry in module.ENTITY_KIND_MAP}


def declared_count(entries: list[dict[str, object]]) -> int:
    """Count class definitions, so a name redefined in one module is counted as the declarations it is."""
    total = 0
    for entry in entries:
        path = pathlib.Path(str(entry["module"]))
        text = path.read_text(encoding="utf-8")
        total += text.count(f"class {entry['new_name']}(")
    return total


def normalise(data: dict[str, dict[str, object]], renames: dict[tuple[str, str], str]) -> dict[str, dict[str, object]]:
    """Re-key the captured data so that an after-file speaks the before-file's names."""
    out: dict[str, dict[str, object]] = {}
    for key, value in data.items():
        module, name = key.split("::", 1)
        old = renames.get((module, name))
        out[f"{module}::{old or name}"] = value
    return out


def main() -> int:
    """Print the comparison and exit non-zero when anything the migration cannot touch moved."""
    parser = argparse.ArgumentParser(description="Compare two entity baselines.")
    parser.add_argument("--before", type=pathlib.Path, required=True)
    parser.add_argument("--after", type=pathlib.Path, required=True)
    parser.add_argument(
        "--map-only",
        action="store_true",
        help="compare only the classes the decision table migrated, so the number is the corpus",
    )
    args = parser.parse_args()

    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = normalise(json.loads(args.after.read_text(encoding="utf-8")), load_map())

    scope = ""
    if args.map_only:
        spec = importlib.util.spec_from_file_location("entity_kind_map", MAP_FILE)
        module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
        if module is None:
            raise SystemExit("entity_kind_map.py is not importable")
        spec.loader.exec_module(module)
        migrated = {(entry["module"], entry["old_name"]) for entry in module.ENTITY_KIND_MAP}
        before = {key: value for key, value in before.items() if tuple(key.split("::", 1)) in migrated}
        after = {key: value for key, value in after.items() if tuple(key.split("::", 1)) in migrated}
        scope = f" ({len(migrated)} names, {declared_count(list(module.ENTITY_KIND_MAP))} declarations)"

    missing = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    changed: list[str] = []
    for key in sorted(set(before) & set(after)):
        for field in COMPARED_KEYS:
            if before[key][field] != after[key][field]:
                changed.append(f"{key}: {field}\n    before {before[key][field]!r}\n    after  {after[key][field]!r}")

    print(
        f"{len(before)} classes compared{scope}, {len(changed)} with a changed surface, "
        f"{len(missing)} missing, {len(added)} added."
    )
    for line in changed + [f"missing: {key}" for key in missing] + [f"added: {key}" for key in added]:
        print(" ", line)
    return 1 if (changed or missing or added) else 0


if __name__ == "__main__":
    raise SystemExit(main())
