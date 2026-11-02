# Quickstart: The version track shows where the graph changed

## Automatic

```bash
cd /Users/bystrovmaxim/PythonDev/aoa-issue-345 && uv run --extra dev pytest packages/maxitor/web/tests/test_history_version_file.py -q
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa-issue-345/packages/maxitor/web/client && npx vitest run src/components/history src/lib/versionNames.test.ts src/lib/historyAddress.test.ts
```

## On the stand

Start it on the local history `erd-full`, extended with a version file: some commits raise the version alone, and one branch of the history names a broken file.

1. Large points are graph changes; small points carry numbers where the version rose.
2. Choose a small point and switch off the three-point icon: the point stays, the version button does not change.
3. In Diff, put both handles either side of a small point: the picker says the graphs are the same.
4. Open a second viewer in a room: its icon is its own.
5. Open the broken history: the graph opens, and the problem is in plain words.
6. Open a history with no version file: no icon, numbers from tags.
