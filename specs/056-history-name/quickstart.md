# Quickstart: A history named after what was opened

1. Server rules: `cd packages/maxitor/web && uv run --extra dev pytest tests/test_history_name.py -q` — the name and the full path for a nested folder, the root and a private history.
2. Client: `cd packages/maxitor/web/client && npx vitest run src/components/history/VersionPicker` — the header shows the name, hover shows the path, a click copies it.
3. By hand: start `maxitor-api` and `maxitor-client` (`.claude/launch.json`), open `https://github.com/bystrovmaxim/aoa/blob/main/packages/aoa-demo/graph.json`, open the version picker:
   - the header reads `aoa-demo`;
   - hovering it shows `bystrovmaxim/aoa/packages/aoa-demo`;
   - a click puts that path on the clipboard;
   - the tab reads `aoa-demo · <version> — Maxitor`, and Recent lists `aoa-demo`.
