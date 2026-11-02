# Data Model: A graph's history joined with its version file

## History

| Field | Type | Rule |
|---|---|---|
| `graph_file` | path | as today; names the graph in the cache |
| `version_file` | path or none | optional |
| `version_key` | dotted key | default `version` |
| `graph_file_before` | list of paths | optional, newest first |
| `version_file_before` | list of paths | optional, newest first |

## Point (`VersionRecord`)

Today's fields, plus:

| Field | Type | Meaning |
|---|---|---|
| `graph_changed` | bool, default true | the graph document differs from the previous point's |
| `version` | string or none | the number at this commit |
| `version_changed` | bool, default false | differs from the last readable number before it |

A commit that changed a watched file is a point when `graph_changed` or `version_changed` is true. The list starts at the first commit that has the graph file.

## Number

The result of reading a key: a string, or a reason (`missing`, `not a string`, `broken`, `format`, `driver`).

## Version problem

Plain text, or none. Found at the head of the branch only.

## Cache

| Entry | Key |
|---|---|
| graph bytes, facts, detail | repository, `graph_file`, commit |
| a number | repository, `version_file`, `version_key`, commit |
| pull request, release, open pull requests | repository and commit, tag or branch, as today |
