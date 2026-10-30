# Mandatory release versions in graph setup

The `aoa-graph-builder-setup` wizard keeps its per-service dialogue and adds one mandatory item: `version-tags`. A configured graph alone is no longer enough to finish setup. Every release on the main branch needs an increasing SemVer tag, and CI must reject violations. A tag is the version authority; no language-specific version file is required.

## What changes when you rerun the wizard

Every run audits the same six item families: `config`, `graph:<name>`, `exporter:<service>`, `local-update`, `ci-graph-check` and `version-tags`. It reports all items in one Review table, including working items and deferred optional integrations. Existing good choices appear as statuses without repeat questions.

The priority is broken existing items, then unfinished mandatory items (the new version requirement first among new decisions), then optional choices. The existing dialogue within each service is retained. On a healthy project set up before this revision, the first new question is how to assign the required version. A stale graph is discussed before missing versioning.

The version question offers a release tool or a person creating tags with CI enforcement. There is no skip option. A free-text refusal is respected, leaves `version-tags` unrecorded and shows **🔴 not done — required**; the final result says **setup is incomplete**. A later run offers it again after any broken items. The wizard never pressures the user into a tag by repeating the question in the same run.

For a stream with no tags, a separate decision proposes `v0.1.0` (with the monorepo prefix where appropriate) or the user's number on the verified current main-branch commit. It shows the exact SHA and creation/publication commands. Choosing automation does not authorize this first tag.

## Decisions in graph-builder.toml

Place the table at the root, outside `[[graph]]`:

```toml
[setup]
skill = "2"
decided = ["local-update", "ci-graph-check", "version-tags"]
deferred = ["local-update"]
```

`skill` is the checklist revision, not a release version. Configurations without `[setup]` still work. The wizard infers their existing decisions from facts and writes the table only during authorized Apply. For an older revision it checks missing IDs; it does not silently downgrade a newer revision. A persisted completion is rechecked on every run.

Only `local-update` and `ci-graph-check` can be deferred, and each must also occur in `decided`. Unknown IDs, duplicate entries, missing fields and mandatory deferrals are refused. Dynamic graph/exporter IDs use the real names. Mandatory items enter `decided` only once demonstrated complete; accepting the plan is insufficient. Read-only runs do not save decisions. An old graph-builder that rejects `[setup]` must be upgraded to a verified compatible revision before the table is added.

The [script](../../examples/step_26_maxitor/15_setup_decisions.py) and [notebook](../../examples/step_26_maxitor/15_setup_decisions.ipynb) run the same configuration cases in temporary files:

```bash
uv run --extra dev python examples/step_26_maxitor/15_setup_decisions.py
```

Observed output includes:

```text
Legacy configuration:
ok tiny (written)
ok tiny
Optional update deferred; mandatory version remains undecided:
ok tiny
Setup decisions preserved: True
A green graph check is not evidence of release-tag enforcement.
Deferred mandatory version: refused setup.deferred.0
Undecided local update: refused setup.decided
```

The configuration reader and `graph-builder check` validate metadata and graphs; they do not perform the version audit. The skill prepares the project's separate version CI. The example does not prove conversational behavior or release enforcement.

## How version evidence is evaluated

| Observation | Version status |
|---|---|
| Complete tag inventory has no release tags | absent |
| Valid increasing tags, required CI not demonstrated | tags without enforcement |
| Malformed/decreasing/off-main tags, or known broken enforcement | broken |
| All mapped streams have valid increasing tags and proven rejecting CI | done |
| Missing access or incomplete history | not done, with the missing evidence identified |

The wizard inspects the actual default branch and follows its first-parent history. It resolves annotated and lightweight tags and compares SemVer numerically, not by date or text order. For example, `v1.10.0` followed by `v1.9.0` decreases. Established prerelease policies use full SemVer precedence; changing build metadata alone is not an increase. It never fixes old history by moving or deleting tags.

A monorepository maps each graph to a release stream, such as `maxitor-v*` or `port-v*`. Shared releases can share a stream. The mapping is made explicit in the generated release/check configuration. Versions from different prefixes are never compared. The preceding release is found with `git describe --tags --abbrev=0 --first-parent --match '<pattern>' '<release-sha>^'`, after checking that history is complete. First releases have no predecessor. A report includes an actual command and its exact answer or failure, not an assumed version.

## CI and owner settings

The PR check validates Conventional Commit titles, including scopes and `!`, and reruns when a title changes. Release analysis must actually consume that title, for example through squash merging. A valid `docs:` title need not create a release. A release commit must be identifiable independently of tag existence; otherwise a missing tag could silently escape the check.

The tag validator runs after the release writer, refreshes tags and checks the exact release SHA. It fails for missing or invalid tags, decreases and off-main targets. Checkout needs full history (`fetch-depth: 0` on GitHub); a tag-push-only job cannot detect a missing tag. Manual tagging needs a rerun path for the same release commit. When publishing commits and tags, send explicit refs together atomically; for an already-merged commit, publish its explicit tag and rerun validation. Checks only read; the release job or a person writes tags.

Reuse appropriate existing release tooling. Release-please normally tags a release-PR merge; it does not release every ordinary PR. Do not introduce version manifests or package-version files to satisfy a tag-only rule. A tag-based semantic-release setup can use explicit plugins without package-version writes; its runtime is tooling, not a requirement that the project use JavaScript. See [release-please](https://github.com/googleapis/release-please#whats-a-release-pr), [semantic-release configuration](https://semantic-release.org/usage/configuration/), [SemVer](https://semver.org/) and [git describe](https://git-scm.com/docs/git-describe).

The wizard never enables repository Rulesets itself. It gives the owner the exact PR check names, merge/title settings, tag patterns and allowed release actors, and tells them which post-release check gates release/deployment. A check after merge cannot retroactively block that merge. Owner settings not inspected remain unverified. Adding a workflow alone is not proof that enforcement works.

## Acceptance scenarios

These are dialogue review cases, not a claim that an agent has been run end to end on each project.

| Project or answer | Expected wizard behavior |
|---|---|
| Previously configured; no `[setup]` or tags | Existing items shown by status; first question asks how to assign the mandatory version, then asks separately about the first tag |
| User refuses versioning | Required item stays incomplete and outside both arrays; next run offers it again |
| Increasing tags and demonstrated enforcing CI | Done row; no version question |
| Tags but no enforcing CI | Tags without enforcement; propose the missing checks |
| `v1.10.0` then `v1.9.0` | Broken; address before new choices |
| Stale graph and no version | Graph repair first, mandatory version second, optional choices afterward |
| `maxitor-v*` and `port-v*` | Per-graph stream mapping; separate comparisons and first-tag decisions |
| Valid title but no release-worthy change | Keep PR validation; do not invent a release |
| First tag or release permissions withheld | No unauthorized tag; setup remains incomplete |
| Shallow history or unavailable remote | Explain missing evidence; never certify done |
| Empty or unrelated project | Full audit summary; no empty config or forced project bootstrap |

Rendering prefixed tags as version numbers in Maxitor is a separate port change; this work does not introduce the proposed `version_tag` history setting.
