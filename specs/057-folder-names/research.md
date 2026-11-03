# Research: Maxitor's parts in folders named the way people call them

## Following a file through a move

- **Decision**: `git log --first-parent --follow --format= --name-status <branch> -- <path>`; every `R<score>\t<old>\t<new>` line names an earlier path, newest first.
- **Rationale**: tried on a repository whose graph file moved inside a merged pull request: the merge commit shows `R097 a/graph.json b/graph.json`, and the three commits before it are listed at `a/graph.json`. The port already reads a version at the first of a history's paths that exists in that commit (`first_file_at`), so the found paths are all it needs.
- **Alternatives considered**: listing the old paths in a config — a public history has no config; redirecting old links — the port cannot know a link is old until it reads the repository, and a link to the old path still shows its versions.

## Doing the move

- **Decision**: `git mv` of the three folders, then a replacement of the three path prefixes in every tracked file outside `CHANGELOG.md` and `specs/`, then a look at relative paths (`pyproject.toml` of `packages/maxitor`, relative links) that do not carry the prefix.
- **Rationale**: `git mv` renames the folders on disk, so untracked `node_modules` and built files move with them; the prefixes are unambiguous: `packages/maxitor/web` (never followed by another letter), `tools/repo_graph_port`, `tools/graph_builder`.
- **Alternatives considered**: symbolic links at the old paths — two names for one folder is what the move is to end.
