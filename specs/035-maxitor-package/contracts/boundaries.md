# Contract: import boundaries inside `maxitor`

```text
maxitor.viewer ──► aoa.action_machine, maxitor.gnomon        allowed
maxitor.gnomon ──► aoa.*                                      violation
maxitor.gnomon ──► maxitor.viewer                             violation
aoa.*          ──► maxitor.*                                  violation (no aoa package may import maxitor)
```

`scripts/check_package_boundaries.py` (a step of the check run):

1. Resolves an import to its owner by the longest matching prefix: `maxitor.viewer…` → `maxitor`, `maxitor.gnomon…` → `gnomon`, `aoa.<name>…` → `<name>`, `<name>…` → `<name>` for the canonical names.
2. For a `[packages.*]` root: an import of another internal owner not in `may_import` is a violation.
3. For a `[standalone.*]` root: an import of `aoa` or of any prefix in its `forbid` list is a violation.
4. A violation line names the file, the line, the owner and the imported module, as today; exit 1.

`maxitor.launch` is not a part the checker knows: its rule — nothing heavy at import time — is held by the packaging smoke test, which runs `maxitor-api` in a clean venv without `[viewer]` and expects exit 2 with the message, not an import error.

The same rules hold in the packaging smoke test: a clean `pip install maxitor` imports `maxitor.gnomon` and runs `gnomon check` without AOA installed.
