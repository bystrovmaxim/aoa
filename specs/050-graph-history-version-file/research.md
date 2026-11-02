# Research: A graph's history joined with its version file

## 1. What `graph_changed` compares

- **Decision**: reuse `graph_change`, and add `schema_version`. A file that does not parse as a graph on either side is compared by its bytes.
- **Rationale**: `graph_change` already matches nodes and edges by identity, so formatting and top-level order do not count, and `proposals_of` already asks the same question.
- **Alternatives**: comparing parsed documents counts a reordering as a change. A content hash cannot ignore order without sorting.

## 2. Which commits read the graph

- **Decision**: only commits that touched the graph file read it. A version-only point takes its facts from the point before and an empty `change`, and reads its contribution from git. `versions/{sha}` still reads the file when someone opens the point.
- **Rationale**: the cache keeps one file per commit, and Maxitor's graph is large. A point per version bump must not store a copy.
- **Alternatives**: `detail_of` for every point would write a full graph per commit.

## 3. Reading a number

- **Decision**: `version_source.py` picks TOML or JSON by the file's extension and walks the dotted key. The result is a number or a reason. It has no I/O.
- **Rationale**: the port stays free of drivers and of `version-gate`, and the same code serves points and the check at the head.
- **Alternatives**: running the `version-gate` program per commit adds a binary to the service.

## 4. Where a problem is found

- **Decision**: `version_problem_of` runs at the head of the branch on every history and describe answer. Older commits only give an empty `version`.
- **Rationale**: a reader needs to know what is wrong now. Old broken commits are history, not a fault.
- **Alternatives**: checking in `load_histories` refuses the whole file, and a public link has no config.

## 5. Moves

- **Decision**: `graph_file_before` and `version_file_before` list old paths, newest first. `git log` runs over all paths, and a commit is read from the first path that exists there.
- **Rationale**: git cannot follow a rename across two paths at once, and a declared list cannot guess wrong.
- **Alternatives**: `--follow` takes one path only. Reading `graph-builder.toml` at each commit, as #316 proposed, ties the port to a file this history may not have.

## 6. The cache

- **Decision**: keep per graph under `graphs/<repository key>/<graph key>/`, where the graph key is the hash of `graph_file`. Version reads go under `numbers/<repository key>/<file key>/`. The old `versions/` folder is removed when the cache opens.
- **Rationale**: a new root cannot serve an old entry, and removal frees the space. Pull requests and releases stay shared: they belong to the commit.
- **Alternatives**: keeping `versions/` beside the new root leaves dead files on the server.
- **Key of a moved graph**: the current `graph_file`, so a move in the config rereads the history once and costs nothing else.

## 7. Requests to the host

- **Decision**: no budget in this feature. Each point asks the host for its pull request once per interval, as a version does today, and a failed answer already falls back to the commit message.
- **Rationale**: the fallback means the cost is a slower first read, not a broken one. The count must be measured on a real history before a limit is designed.
- **Alternatives**: the budget of 30 requests in #316 needs an ordering of points and partial answers, which is a change of its own.
- **Risk**: a public link has a small anonymous limit, so its numbers of pull requests may fall back sooner. The quickstart counts the requests.
