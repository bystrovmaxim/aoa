# Data Model: The version track shows where the graph changed

## HistoryEntry (server)

| Field | Meaning |
|---|---|
| `version_file` | The file the history names, or none |
| `version_problem` | The port's plain sentence, or none |
| `version_link`, `version_key` | A public history's parameters, or none |

## PublicHistory (server and client)

`link` stays the graph's link. `name` is the link with the two parameters when they are given.

## HistoryVersion (client)

Gains `graph_changed?: boolean`, `version?: string | null`, `version_changed?: boolean`, all as the port sends them.

## OpenedHistory and the polling answer (client)

Gain `version_file: string | null` and `version_problem: string | null`.

## Point (track)

Loses `release`. Gains `large: boolean`, `named: boolean` (a number stands under it) and `carried: string[]` (flags of hidden points).

| Point | `large` | `named` with a file | `named` without |
|---|---|---|---|
| Version | `graph_changed !== false` | `version_changed` and `version` | has its own version tag |
| Live, pull request | as drawn today | as drawn today | as drawn today |
