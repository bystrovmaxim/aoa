# Research: A history named after what was opened

## Where the name is made

- **Decision**: `PublicHistory.title` returns the last folder of the link's path; at the root it returns the repository's name. A new `PublicHistory.path` returns `owner/repo` joined with the folder path.
- **Rationale**: `_GITHUB_PATH` already splits the link into owner, repo, branch and path; the name needs nothing else, so no request is added (FR-004). Every reader of the history's name (`HistoryEntry.title`, the open answer, the log lines, the tab, the recent list) takes `title`, so they follow without change.
- **Alternatives considered**: a `name` in `version.toml` or a manifest's name — refused by the maintainer: a copied file can carry a wrong name, and a folder exists for every language and tool. A name inside the graph file — a protocol change for a label.

## The full path of a private history

- **Decision**: a private history's `path` is its name, the port's address without the key.
- **Rationale**: it is what tells it apart, and it never carries the key.

## Hover and copy

- **Decision**: the picker's name is a button inside a MUI `Tooltip` that shows the full path; a click or Enter writes it with `navigator.clipboard.writeText`, and the tooltip says `Copied` for 1.5 s, or `Not copied` when the clipboard refuses.
- **Rationale**: `ServiceUrlInput` already copies addresses this way with a short feedback; the picker reuses the idiom. A button is reachable by keyboard and is announced.
- **Alternatives considered**: a second line under the name — the maintainer chose hover.
