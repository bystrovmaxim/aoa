# Research: Maxitor Reads a Graph's History from Its Repository

Decisions taken while planning #288. Each: what was chosen, why, and what was rejected.

## R1. The rename to `front` comes first, as its own phase

**Decision**: phase 1 renames Maxitor's web part — `git mv packages/maxitor/app packages/maxitor/front`, `src/maxitor/viewer` → `src/maxitor/front`, `maxitor.viewer` → `maxitor.front`, extra `viewer` → `front`, command `maxitor-api` → `maxitor` (entry `maxitor.front.launch:main`), `app/graph.json` → `front/graph.json` — with the same mechanical sweep #286 used (every tracked file but old specs and past changelog entries), the old-name test extended to `maxitor.viewer`, `maxitor[viewer]`, `packages/maxitor/app`, `maxitor-api`.

**Rationale**: the issue's §0.1; the core is wired into this part in phase 4, so it must carry its final name first. One commit keeps the rename apart from new behaviour.

**Alternatives rejected**: renaming at the end (every new file would be written twice).

## R2. Where the core lives and what it may import

**Decision**: `packages/maxitor/core/repo_graph_port/` with `src/maxitor/repo_graph_port/` (namespace `maxitor`, like `front` and `graph_builder`) and `tests/`; hatch `sources` and `dev-mode-dirs` gain `core/repo_graph_port/src`. A new extra, `repo-graph-port = ["aoa-action-machine>=1.0.1a0", "PyJWT[crypto]>=2.8,<3", "httpx>=0.28,<1.0"]`; `front = ["maxitor[repo-graph-port]", …]`. Boundaries: `[packages.repo_graph_port]` with `may_import = ["action_machine", "graph_builder"]` (it checks graphs with the protocol's schema through `maxitor.graph_builder.schemas`); `front` may import `repo_graph_port`; `graph_builder` and `repo_graph_port` never import `front`.

**Rationale**: FR-004, FR-019; the layout of #286 (`core/` for what the front and tools share).

**Alternatives rejected**: inside `front` (the gateway could not reuse it without the whole front); a second copy of the schema check (one implementation, in `graph_builder`).

## R3. Reading git: a partial bare mirror through the `git` command

**Decision**: one resource, `GitMirror`, owns a bare partial clone per repository (`git clone --bare --filter=blob:none`) under a cache folder, and exposes meaningful methods only (rule 52): `fetch(repository)`, `versions(path, branch)` (`git log --first-parent --format=… -- <path>`), `file_at(sha, path)` (`git show`), `tags()` (`git for-each-ref refs/tags`), `is_ancestor(a, b)`. It runs `git` as a subprocess with no shell, an argument list, a timeout and a lock per repository (FR-016). Local paths are read the same way, with no clone.

**Rationale**: first parents and large files come straight from git (the REST API follows branch commits and returns contents over 1 MB empty); `git` is everywhere the projects are; a subprocess keeps the resource working with the store directly (rule 53).

**Alternatives rejected**: a Python git library (dulwich, pygit2) — a heavy dependency for five commands, and partial clones are less mature there; the REST API alone (above).

The Docker image installs `git` (`python:3.12-slim` lacks it).

## R4. Which commits are versions, and where tags go

**Decision**: versions = `git log --first-parent <branch> -- <path>` on the mirror, oldest first. Tags are placed by walking the first-parent chain once: each tag's commit goes to the newest version that is its ancestor-or-self on that chain (`git merge-base --is-ancestor`), so a tag on a later commit that did not change the graph lands on the version before it. A tag off the chain (on a side branch) is not placed.

**Rationale**: the decisions of #273 (2) and FR-006, FR-008.

## R5. The host: one resource per host, GitHub first

**Decision**: `GitHubHost` (rule 52 names): `token_for(repository)` (App JWT, RS256, signed with `PyJWT`, exchanged for an installation token valid one hour, kept in memory only), `git_auth(repository)` (the token as an `Authorization` header passed to each git call through `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0=http.extraHeader`/`GIT_CONFIG_VALUE_0` in that call's environment — never in a remote URL, so the mirror's `config` on disk and the process list never hold it), `pull_request_of(repository, sha)` (`GET /repos/{r}/commits/{sha}/pulls`), `release_of(repository, tag)` (`GET /repos/{r}/releases/tags/{tag}`), `verify_webhook(body, signature)` (`X-Hub-Signature-256`, HMAC-SHA256 of the raw body). A public repository uses the same calls without a token. A test stand-in host serves the same answers from fixtures.

**Rationale**: FR-015, FR-018, FR-024; GitLab later is one more resource with the same methods. A token in the clone URL was rejected: git writes the remote URL into the bare mirror's `config`.

## R6. Read keys: an AOA auth coordinator, not a parameter

**Decision**: a key travels in the header `X-Maxitor-History-Key` (the front reads it from the history's address in the browser and sends it), never in a query string or path — so it is in no access log. A `HistoryKeyAuthCoordinator` (AOA's `AuthCoordinator`: a credential extractor for that header, an authenticator that hashes the key and finds it in the histories config, and a context assembler) puts the reader into the context: `user_id` = the key's `name`, roles = `HistoryReaderRole`, and the history id it opens. Actions declare `@check_roles(HistoryReaderRole, GuestRole)` and check the history they serve against the context. A public history needs no key (`GuestRole`). Every refusal — unknown, revoked or expired key, other history, missing version — is the same "not found". Wrong keys are limited per client address per minute in the coordinator.

**Rationale**: FR-011–FR-014; AOA's access model (rules 55–57) rather than a hand check in each aspect; the key is a sensitive value (rule 58).

**Alternatives rejected**: the key in the address the server receives (`/h/<key>/…`, the old #288) — access logs and proxies would keep it.

## R7. The histories config

**Decision**: a TOML file named by the environment variable `MAXITOR_HISTORIES` (read only by the settings loader, reaching actions through declared context — rule 63), reread when its modification time changes. Shape as in #288: `[github]` (`app_id`, `private_key_env`, `webhook_secret_env`) and `[[history]]` (`id`, `host`, `repository`, `branch`, `graph_file`) with `[[history.keys]]` (`name`, `sha256`, `expires`). `maxitor history key new|revoke|list|check` edits and checks it (a CLI, not HTTP: FR-011).

## R8. The cache

**Decision**: per repository, the mirror is the cache; per `(repository, sha)` the version's facts (counts, refusal) and graph bytes are kept on disk forever; tags and pull request descriptions are kept with a time and refreshed by a webhook or when older than the fallback interval (default 10 minutes, `MAXITOR_HISTORY_REFRESH_SECONDS`). `history` answers with an `ETag` (hash of its body) through the adapter's conditional GET; `version` answers `Cache-Control: immutable`.

## R9. The actions and their routes

**Decision**: in `maxitor.repo_graph_port.actions`: `DescribeHistoryAction`, `HistoryAction` (`after`), `VersionAction` (`sha`), `ReceiveHostEventAction` (the webhook). The front mounts them under `/api/v1/history/…`: a configured history by its id (`/api/v1/history/{id}`, `/versions`, `/versions/{sha}`); a public one by its link on its own routes (`/api/v1/history/public?link=…`, `/public/versions?link=…`, `/public/versions/{sha}?link=…`), named in the cache by the link's repository, branch and path; `POST /api/v1/history/events/github` for the webhook. The webhook's signature is checked by a small ASGI middleware on that one route, over the raw body and before the adapter parses it (rule 47: the transport checks the request); a bad signature is answered `401` and never reaches the action.

## R10a. The cache's place and the boundary checker

**Decision**: the mirrors and the version cache live under `MAXITOR_HISTORY_CACHE` (default `~/.cache/maxitor/history`), through declared context. The boundary checker learns the new package: `repo_graph_port` joins its `CANONICAL` names and its `[packages.*]`, and a `[packages.*]` entry may name a standalone owner (`graph_builder`) in `may_import`.

## R10b. The stand

**Decision**: the stand (`deploy/stand/`) runs Maxitor's image with `git` installed; `MAXITOR_HISTORIES` points at a config file on the server and `MAXITOR_HISTORY_CACHE` at a volume; `GITHUB_APP_PRIVATE_KEY` and `GITHUB_WEBHOOK_SECRET` come from the server's environment file, which the maintainer writes and which is not in the repository; the App's webhook URL is the stand's `/api/v1/history/events/github`. The maintainer chooses the repositories; read keys for the private histories are issued on the server with `maxitor history key new` and handed to the maintainer only. How the stand is deployed (the host and its script) is agreed with the maintainer before the phase.

## R10. Tests

**Decision**: a small git repository built in a temporary folder by a test fixture (`git init`, commits, `git merge --no-ff`, tags), read as a local path; the GitHub host replaced by a stand-in; the end-to-end read of a real private repository checked once by hand and recorded in the pull request.

## R11. Rules the code is written by

Rules 41–66 of the offers project's constitution, as the maintainer adopted them for Maxitor (2026-10-29): actions with frozen `Params`/`Result` (42), logic in aspects (43), no state (44), `@depends`/connections (45), the adapter at the boundary (47–49), constants in their method (51), meaningful resource methods (52), resources on the store directly (53), a file per class (54), roles and checks (55–57), sensitive keys (58), a graph from the service's own code (60), complex input as `Params` models (62), environment through context (63–64), no globals in actions (65). This repository's own: English (Principle II), the tail (Principle VI).
