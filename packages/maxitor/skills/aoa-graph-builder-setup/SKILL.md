---
name: aoa-graph-builder-setup
description: Guide a project through setting up or auditing version checks, saved model graphs, or both. Walk the user through one decision at a time, prove the proposed changes, and apply the reviewed setup. Reviewing or editing this skill does not start the wizard.
---

# Versions and model graphs: setup wizard

Help the user choose what happens the next time someone changes this project. A version check asks whether the affected parts received higher numbers. A graph check rebuilds a service's model map and compares it with the saved file. Either can help on its own. Neither requires release tags. Use this wizard for setup, repair or a repeat audit. A request to explain, quote, translate or revise it is a writing task.

## How to conduct the conversation

Use the user's language, including in the stage labels. Keep paths, commands and project-facing code in their original form. Use the same four stages throughout: **1/4 Discover**, **2/4 Services**, **3/4 Updates and checks**, **4/4 Review**.

**One step, one decision, one question. Wait for the answer.** Work on one service or versioned folder at a time. A numbered procedure below is your working order, never a questionnaire to paste into the chat. Do the research yourself; ask about choices, not facts you can read. If the user already chose a scope or a setting, carry it forward. On a repeat visit, audit everything relevant, mention healthy items briefly and address a broken item first.

Build each question from one observed fact, its consequence for the user, and two or three meaningful options. Put the recommended option first and explain why it fits this project. Use the host's question card when available; leave room for an answer in the user's own words. Say which service you mean. Do not invent a count of remaining questions. After an answer, acknowledge the consequence in one sentence and move to the next applicable decision. If a service is left out, skip its exporter, destination and other dependent questions.

For example, **only if discovery established these facts**:

> **2/4 · Services · orders — track this folder separately?**
>
> The orders service already has a saved map. Today it shares the package's version. A separate number would let someone following this service see its changes without treating every change to the package as a new orders version.
>
> 1. **Track orders separately (recommended):** a change here will require the service and its tracked parents to increase their versions.
> 2. **Keep the package version:** there will be no separate number to maintain for orders.

Only after option 1, and only if there is no existing number, ask what first number to record. Never put a second decision about the number, the changelog or CI into this card.

Accept “back”, “change my answer”, “show my choices”, “details”, “pause” and “stop”. If an answer changes, reopen only choices that depended on it. If the user asks for an explanation, give one concrete before/after example and return to the pending question. Silence or a preselected option is not an answer. Keep working notes of observed facts, choices, blockers and proof; do not make the user fill out a form.

## 1/4 Discover

Read the repository layout, manifests, version declarations, graph configuration, saved graphs, relevant CI and local check commands. Inspect the current diff so the proposal preserves the user's work. Distinguish installed packages, folders the project treats as solutions of their own, and services with an exportable model. A directory alone does not establish a component. Read both setup records if present; recorded choices are a memory of intent, never proof that CI or an exporter still works.

Treat the scope of this visit separately from settings already in force. “Only graphs today” leaves existing version tracking and its CI in place. Enter the retirement dialogue when the user asks to stop tracking something or the audit finds evidence that its purpose has changed. If scope is clear, use it. Otherwise ask **which part to work on**: versions, graphs, or both, recommending the choice supported by what you found. The user may decline both. On an audit, report what is healthy; if nothing needs changing, finish with the evidence. Do not create setup files merely to record that the user declined. A graph-only setup creates no version configuration; a versions-only setup creates no graph configuration.

Prepare and prove changes in a temporary directory outside the project. Before Review, do not edit the project, install tools into it, change the CI provider's settings, or create Git history in the real repository. If a project build might write generated files, run discovery in a disposable copy with the necessary inputs. A read-only audit ends with findings and proposed repairs.

**Version tool, only for the versions part.** This revision supports stable version-gate releases from **v0.1.1 up to, but excluding, v0.2.0**. Read the repository's existing pin. Discover tags with `git ls-remote --tags https://github.com/bystrovmaxim/version-gate.git`; verify the chosen tag has published release assets. Resolve an annotated tag to its commit. Propose an exact compatible update if one is available; never silently upgrade. If an upgrade requires a newer minor or major line, report that this wizard must be updated first and leave that pin unchanged. Do not downgrade a project already on an unsupported line.

Download the chosen binary and `checksums.txt` from the same GitHub Release into the temporary directory. Select the actual published asset for the system: v0.1.1 uses `version-gate-{linux,darwin,windows}-{amd64,arm64}`, with `.exe` on Windows. Require a matching SHA-256 entry for that exact filename and verify the downloaded bytes before execution. Use the verified binary for `version-gate check --base <base-ref>`. No Go installation is needed. If the release, checksum, binary or base ref cannot be verified, name the missing prerequisite; do not claim a successful check.

**Graph tool, only for the graphs part.** Keep a working project pin if appropriate. For a new setup, verify the commit of `main` at `https://github.com/bystrovmaxim/aoa`. With uv, run the base Maxitor package at that full commit:
```sh
uvx --from "git+https://github.com/bystrovmaxim/aoa@<full-commit>#subdirectory=packages/maxitor" graph-builder --version
```
Replace the placeholder before running or proposing the command. Use a release tag or an exact PyPI version only after verifying it exists for this tool and works. Below, `graph-builder` means the verified invocation. The tool needs the project's own environment only when executing its graph builds. It does not require the project to use AOA or Python.

## 2/4 Services

Start with the first affected folder. If both parts are selected, explain separately what will own its version and what will generate its graph. A graph at a package root can use the package's version; do not invent a component or move a file to make the layout fit. Several graphs may share an owner.

**Versions.** Resolve only the unsettled choices, one per turn:

1. Identify the repository root and package manifests. Propose each meaningful component from the project layout. Explain which parent versions a change in this folder would also affect. A component cannot contain a component. A single-package repository can share its root version.
2. For a package with a standard manifest, offer to track it or deliberately list its directory in the root `untracked` list. This exemption removes the need for its own declaration; its files still count for tracked parents. An ordinary folder which does not need a separate version can simply stay part of its parent.
3. Prefer the authoritative version already in the project. A repository or package declaration names a driver **or** holds its own literal number. The drivers are `python` (pyproject.toml), `rust` (Cargo.toml), `node` (package.json), `php` (composer.json), `dart` (pubspec.yaml), `maven` (pom.xml), `gradle` (gradle.properties), `dotnet` (.csproj) and `ruby` (version.rb). Check a nonstandard or inherited source with the actual tool before offering it. For a component, use its own literal `version`. When a new literal is needed, ask the user for the first number. **Never raise an existing number on the user's behalf.** If the build computes a number the gate cannot read, explain that a separately maintained number is the project's responsibility.
4. Ask about a versioned changelog only where applicable. Separately resolve the repository's `require_bump` policy and meaningful `changes.ignore` patterns. Use observed examples: with the root bump disabled, a change confined to an unversioned root script may need no bump; a package change still does. Start with no exclusions unless the project has a reason. Never ignore a saved model graph. Explain that a new exception on a PR does not exempt that PR retroactively.
5. On a repeat visit, keep healthy declarations; identify stale exemptions or references to removed folders and propose only the evidenced cleanup. If it might be a move, show the old and new paths before proposing removal. Keep version setup decisions under the root `version.toml`'s reserved `[setup]` table. Use the wizard's revision `skill = "3"` and lists `decided` and `deferred` for version choices such as `version-files` and `ci-version-check`; a deferred choice is also decided. Preserve unrelated settings. The gate ignores this table; the declarations themselves determine coverage.

**Graphs.** Audit configured entries with `graph-builder check`. A listed file may be current, stale, missing, failed to build, or refused by the schema. A malformed configuration is one configuration problem, not a failure in every service. Discover unlisted services and existing graph files separately: a successful check cannot find a service absent from the configuration.

For each service, identify an existing exporter or prove a small exporter in the project's language. Its sole standard output must be one protocol graph. Use the project's model registration and runtime environment. An HTTP-only route is not a standalone build command. Run each service in its own process. If there is no reliable producer, leave it out and explain what is missing; do not hand-author graph JSON.

Prove a new or repaired exporter with a temporary `graph-builder.toml`: `graph_builder = "1.0"`, one `[[graph]]` with its `name`, exact `cwd`, `build` and a temporary output `file`. Run `graph-builder write --config <temporary-config>` and then `graph-builder validate <temporary-file>`. A pipe into validate cannot prove the producer exited successfully. For an existing file, compare with `graph-builder check`; a raw byte comparison with exporter output is not equivalent.

Ask whether to include the service and its proven exporter as **one** scope decision. If included and no destination is established, ask where to save its map; recommend the project's convention, otherwise beside the service. Preserve existing destinations unless a move is chosen. If an entry's graph is missing, run the generator in the temporary copy: propose restoring the file, or show the failure. When a service disappears or its independent map is superseded, use the retirement dialogue below. A missing output on its own calls for repair. A stale graph needs regeneration. An unlisted graph needs a proven build before offering an entry.

Keep graph decisions in the existing `graph-builder.toml` schema: revision `skill = "3"`; IDs `config`, `graph:<name>`, `exporter:<service>`, `local-update`, `ci-graph-check`. Only the last two may be deferred, and must then also be decided. On migration propose removing `version-tags` from wizard decisions. Existing tags, releases and independently maintained release workflows belong to the project. Add no mandatory tagging step. Never store version decisions here or create an empty graph config.

### When an existing setup has outlived its purpose

A service can remain on disk after its responsibility moves. Look for a concrete signal such as an exporter moving to its parent, a service being folded into a package, or the owner saying that nobody maintains a separate map anymore. Check possible moves first. Age, an unchanged version, an unchanged graph or a single failed build is insufficient. Bring up one candidate once and give the user the evidence. A working setup needs no periodic reconfirmation.

For example, when the orders service has been folded into the shop package and the owner has confirmed that change:

> **2/4 · Services · orders — should shop now carry the version for orders?**
>
> The orders folder still exists. Its changes currently require both an orders version and a shop version. Keeping only the shop version would remove one number from each future orders change.
>
> 1. **Use the shop version.** Retire the separate orders declaration. Changes under orders will still count for shop.
> 2. **Keep both versions.** Continue checking orders and shop separately.

Respect this answer before considering a graph decision. For a retired component, propose removing only its declaration and updating the relevant wizard records. Identify all remaining tracked parents. For a package whose standard manifest stays, retain its native package version and prepare the root `untracked` exception the gate requires. Check the transition against the actual base: exemptions on a PR take effect after merge. Where necessary, first land the exception with the declaration still present, then retire the declaration in a separate change. Show the stages and any parent bump needed; leave the number to the owner.

For a map that may be redundant, ask one different question: **“Should this service still publish a separate map?”** Name the replacement map if one exists and explain what users would lose. If it is retired, propose removing its `[[graph]]` entry and associated decision IDs. Show known consumers of its path, including history links; flag any external consumer you cannot verify. By default keep the saved file and exporter. If the user also wants either removed, settle that as a separate choice after checking its consumers. An archived snapshot on its own is no reason to offer to connect the service again.

## 3/4 Updates and checks

For graphs, first settle **how maps get updated**, then **how stale maps are detected**. Reuse an adequate existing integration. Otherwise offer `graph-builder write` at the end of a successful local check run, or an explicit manual update command if the project has no such run. Explain that changed maps are reviewed with the code. Separately offer `graph-builder check` in CI with the project environment prepared, or record the choice to defer. CI checks and never rewrites maps. Do not add hooks.

For versions, offer one CI check on pull requests into `main`. On GitHub use full history and the Action pinned to the verified release commit, with the release tag supplied separately. For v0.1.1 the job steps are:
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: bystrovmaxim/version-gate@e0052e7ddbc429c726389ef945225cb22c5857a0
  with:
    version: v0.1.1
```
For another supported release resolve and verify its own SHA and tag. Preserve all existing workflow triggers and jobs; restrict the new version job to PRs into main. On another host use its native PR mechanism, full history, and a checksum-verified release download; run `version-gate check --base <current-main-ref>`. Do not offer GitHub Actions there. If CI is deferred, explain that no automatic enforcement will exist. A routine local version check is optional.

**Reconcile the integrations after a retirement.** Show the before and after counts of active version levels or graph entries and which checks each job still runs. Removing one component or one graph normally leaves the shared check in use. Keep the graph check and local write step for all remaining maps. Removing the last graph leaves no valid empty `graph-builder.toml`: include retirement of that config in the review, inspect local write steps and CI graph checks, and offer to remove their obsolete invocations. Keep files or workflow jobs still used by other checks.

Version declarations, manual checks and automatic enforcement are separate choices. Disabling version CI alone can leave the declarations usable locally. If the owner retires version tracking repository-wide, show each affected declaration and any history reader that still uses its numeric value. Resolve those dependencies before removing the files. Skipping version setup, or switching off only the root bump, never implies removing the CI job.

When an invocation has become redundant, ask **one question about its automatic check**. Identify the exact CI step or job and what will still run. Prefer removing just the step from a mixed job; inspect job dependencies, downstream references and the reported check name. If that name must disappear or change, check whether it is required by branch rules. If rules cannot be read, ask the owner to verify that one name. Include the owner action in the reviewed plan: release the obsolete requirement, or require the replacement once it reports, before the old name disappears. Wait for that prerequisite on the affected removal. Leave unrelated required checks in force. Settle a separate local update step only if that choice is still open.

Name the exact job the owner must make required and explain why branches must be up to date before merging: two PRs can propose the same next number. Do not change repository rules. The owner's verification is a PR with a counted change and no bump that cannot merge; do not open one during setup.

## 4/4 Review

Lead with what developers will do after setup. Give a compact table: **folder or service | current state | proposed change | version source or saved map**. For each retirement say which files will still count, which maps will still rebuild, which CI names will still report, and any owner action required before cleanup. List deferred items separately. Below it show every file to create, change or remove, exact diffs or prepared new contents, tool pins, final commands and working directories, and the actual proof with exit status. Distinguish results in a temporary copy from checks of the real project. A failed proof is a blocker for that item, not a proposed fix.

If there is a diff, ask one final question: **apply this plan, change a choice, or stop?** Apply only the reviewed choices when authorized. If nothing would change, report the evidence and finish without an Apply question. If a new scope decision appears while applying, stop that part and return to the relevant question.

Apply the reviewed declarations, exporters, integrations and decision records. Run the accepted final graph builds from the real configuration with `graph-builder write`, then `graph-builder check`; inspect changed files. Only run graph commands if the final config still has at least one graph. When version tracking remains in scope, run the verified version command in the actual repository and state exactly which committed HEAD and base it saw. **The gate reads Git commits, not uncommitted files.** If the reviewed configuration exists only in the working tree, report that limitation and prove that exact configuration in a disposable Git copy. Do not commit in the user's repository to manufacture a green result.

In the disposable copy, put the reviewed configuration and the relevant project files in a **committed baseline**. With full history available, run `version-gate check --base <baseline-sha>` as a control. Make a second, temporary commit with one counted change in a tracked level that requires growth; leave all versions unchanged. Run the same command. Require exit 1 **and a diagnostic naming the expected level and unchanged version**. A missing binary, an invalid config or a bootstrap-only run is not this proof. If the chosen policy has no level requiring growth, explain why no such proof is possible under it. Skip this exercise for graphs-only setups. Synthetic commits belong only in the disposable copy.

For a retirement, verify the intended loss of coverage as well as what survives. In a disposable setup where orders now uses its package version, a counted orders edit must still fail for the package when it requires a bump and must produce no separate orders requirement. With one of two maps retired, the surviving map must still build and pass `graph-builder check`. With the last map retired, verify the remaining CI and local commands can run without the graph config. With version CI retired, verify the remaining job steps and dependencies and report exactly which owner setting was verified or is pending. Repeat discovery against the resulting state: the same choices must yield no diff and no request to turn an intentionally retired check back on solely because its CI step is absent.

Report what changed, one real command and its actual answer, what remains manual, and which owner setting is still pending. On a repeat run the same choices should produce no project diff. If a command failed, state what was already applied and what remains; do not retry while the same prerequisite is missing. Leave the project's changes for review.
