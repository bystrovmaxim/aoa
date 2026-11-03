# Feature Specification: A real graph history of the demo

**Feature Branch**: `feature/issue-325-demo-graph-history`, one branch per version

**Created**: 2026-11-03

**Status**: In progress

**Input**: Issue #325, "Demo: a real graph history of ten and more merged pull requests, showing every kind of change".

## What this is

Maxitor shows the history of a service's graph: any past version, or two versions compared. The demo of this repository gets a real history made of ordinary pull requests into `main`. Anyone opens it in Maxitor by the public link to `packages/aoa-demo/graph.json`, joined with the demo's version file `packages/aoa-demo/pyproject.toml`, and sees every kind of change on every diagram.

## Rules every version follows

1. One version is one pull request into `main`, merged, with a title and a body that say in plain words what changed.
2. It runs `graph-builder write` and commits the rebuilt `packages/aoa-demo/graph.json` with its code.
3. It raises the demo's version, because `version-gate` requires it for any change of `packages/aoa-demo` outside README and tests.
4. A release is a real one: the tag `aoa-demo-v<version>` on the version's merge commit, a GitHub Release with a title, and the package published to PyPI by `publish.yml`, which that tag starts.
5. Kinds of change are mixed: most versions touch several diagrams at once. Sizes are mixed too.
6. Maxitor flags a point only for a real release, a tag published as a GitHub Release. A tag is never a release by its name alone.

## Plan of pull requests

`V` changes the graph (a large point on the track). `C` changes the demo's code and version but not its graph (a small point). `N` changes nothing the history counts (not on the track).

| # | Size | Story | What changes | Track |
|---|---|---|---|---|
| V1 | small | a gift wrap gets a note for the recipient | ERD: field `recipient_note` added on the gift wrap. One change only | large point |
| V2 | medium | subscriptions appear | ERD: table `Subscription` added, relations to customer and first order · Lifecycle: subscription lifecycle added (trial → active → cancelled) · Use case: action `SubscriptionStart` added | large point |
| V3 | small | prices and statuses are made precise | ERD: field type changed, description rewritten · Lifecycle: transition added | large point |
| C1 | small | a started subscription gets a readable id | the body of an aspect is rewritten; the graph stays | small point |
| M1 | small | Maxitor flags only real releases | Maxitor only: a tag named `release…` with no GitHub Release is no longer a flag; the demo's graph stays | not shown |
| N1 | small | the demo's README and tests are tidied | README and tests only, no version raised | not shown |
| V4 | small | checkout gets a new check | Use case: an action changes only inside (params, result, aspects); nothing on any diagram moves | large point |
| V5 | large | gift cards start, as their own domain | Full graph: domain added · Use case: roles and actions added, a role link changed · ERD: field removed in another domain · changes across several domains | large point, release flag |
| V6 | medium | subscriptions are linked differently | ERD: a relation points at another table, another relation removed · Lifecycle: state added · Use case: an action changes inside | large point |
| V7 | small | the warehouse takes a table from the catalogue | ERD: table moved to another domain · Lifecycle: state removed | large point |
| C2 | small | the loyalty stub counts points per currency unit | the body of an aspect is rewritten; the graph stays | small point |
| V8 | medium | roles are simplified | Use case: role removed, action removed · Lifecycle: transition removed | large point |
| V9 | large | the gift card pilot is closed | Full graph: domain removed with its tables, actions and roles · Lifecycle: a lifecycle in another domain removed | large point |
| V10 | small | the demo's first release | ERD: a description and one field | large point, release flag |
| V11 | medium | work after the release | ERD: table and relation added · Use case: action and role added · Lifecycle: state added | large point |
| V12 | medium | returns | a mixed change; the pull request stays open | after Live, open |

## Where each kind of change is found

| Diagram | Kind of change | Version |
|---|---|---|
| ERD | table added / removed | V2 / V9 |
| ERD | field added / removed | V1 / V5 |
| ERD | field type changed, description changed | V3 |
| ERD | relation added / removed | V2 / V6 |
| ERD | relation pointing at another table | V6 |
| ERD | table moved to another domain | V7 |
| Lifecycle | state added / removed | V6 / V7 |
| Lifecycle | transition added / removed | V3 / V8 |
| Lifecycle | lifecycle added / removed | V2 / V9 |
| Use case | action added / removed | V2 / V8 |
| Use case | role added / removed | V5 / V8 |
| Use case | role link changed | V5 |
| Use case | action changed only inside | V4 |
| Full graph | domain added / removed | V5 / V9 |
| Full graph | a large change across several domains | V5 |
| History | one change | V1, V4 |
| History | large version | V5, V9 |
| History | tag and release (flag) | V5, V10 |
| History | code changed, graph not (small point) | C1, C2 |
| History | nothing counted changed (not shown) | N1 |
| History | open pull request after Live | V12 |

## Checks

- Each version: the demo's tests and `graph-builder check`. The browser check is waived for the versions, which touch only the demo; the required status says so in its description.
- Before the final pull request (closing check run, documentation, changelog): the full browser check, `bash scripts/check_before_pr.sh`, with no waiver.

## Success Criteria

- **SC-001**: The demo's history shows at least ten versions on the track, with one pull request open after Live.
- **SC-002**: Every row of "Where each kind of change is found" is seen by comparing two versions in Maxitor.
- **SC-003**: The history opens by its public link with no key.
- **SC-004**: The demo runs and every check passes after each merged pull request.

## Out of scope

- Other changes to Maxitor; a bug found this way gets its own issue. M1 is the one change to Maxitor this work makes.
- A new demo application.
- A history kept by hand: versions come only from git.
