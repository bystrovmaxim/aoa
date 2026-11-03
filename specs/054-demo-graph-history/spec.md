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
3. It raises the demo's version, because `version-gate` requires it for any change of `packages/aoa-demo` outside README and tests: the middle digit when the graph changes (`V`), the right digit when only the code does (`C`). So every point on the track has its own version, and the chip `<version> · #<pull request>` changes both parts at once. The pull request numbers in the plan are expected, not promised: any issue or pull request opened meanwhile takes a number.
4. A release is a real one: the tag `aoa-demo-v<version>` on the version's merge commit, a GitHub Release with a title, and the package published to PyPI by `publish.yml`, which that tag starts. Before the demo's first release, `aoa-action-machine`, which the demo depends on and which changed since its last release, is released the same way, and the demo's lower bound on it is raised to that version. Maxitor is not released.
5. Kinds of change are mixed: most versions touch several diagrams at once. Sizes are mixed too.
6. Maxitor flags a point only for a real release, a tag published as a GitHub Release. A tag is never a release by its name alone.

## Plan of pull requests

`V` changes the graph (a large point on the track). `C` changes the demo's code and version but not its graph (a small point). `N` changes nothing the history counts (not on the track).

| # | Size | Story | What changes | Track | Chip |
|---|---|---|---|---|---|
| ✅ V1 (#366) | small | a gift wrap gets a note for the recipient | In the store domain, the gift wrap table (`GiftWrapAddon`) gains the field `recipient_note`, a note for the recipient. Nothing else | large point | 3.3.0 · #366 |
| ✅ V2 (#367) | medium | subscriptions appear | In the store domain, a new table `Subscription` with the fields `plan_code` and `renewal_day` and two relations: to the customer (`CustomerAccount`) and to the first order (`SalesOrder`). The subscription has its own lifecycle: Trial → Active → Cancelled, and Trial straight to Cancelled. A new action `SubscriptionStart` for the editor role | large point | 3.4.0 · #367 |
| ✅ V3 (#368) | small | prices and statuses are made precise | The discount (`DiscountApplication`) field `discount_amount` changes its type from `float` to `Decimal` and gets a new description. The customer lifecycle (`CustomerAccount`) gains the transition Provisioned → Closed | large point | 3.5.0 · #368 |
| C1 | small | a started subscription gets a readable id | `SubscriptionStart` builds the subscription id differently: only the code inside changes, the graph stays | small point | 3.5.1 · #369 |
| M1 | small | Maxitor flags only real releases | A change to Maxitor itself: a release flag only for a tag with a GitHub Release, not for a tag named `release…`. The demo is untouched | not shown | — |
| N1 | small | the demo's README and tests are tidied | The demo's README and a test are tidied. The demo's version does not rise | not shown | — |
| V4 | small | checkout gets a new check | The action `CheckoutSubmit` gains the parameter `promo_code` and a new step, "check the promo code". Nothing moves on any diagram: it shows only in the action's card | large point | 3.6.0 · #372 |
| V5 | large | gift cards start, as their own domain | A new domain `gift_cards`: the tables `GiftCard` (lifecycle Issued → Active → Spent) and `GiftCardRedemption` (linked to the order); the roles gift card issuer and cashier; the actions issue a card and redeem a card. In store, `LoyaltyPointsStub` moves from the guest role to the viewer role, and the gift wrap loses the field `lineage_batch_token`. aoa is released before the merge, the demo's 3.7.0 after it | large point, release flag | 3.7.0 · #373 🚩 |
| V6 | medium | subscriptions are linked differently | The subscription loses the relation `first_order`. The parcel's (`ShipmentParcel`) origin now points at the cross-dock (`CrossdockStaging`) instead of the warehouse (`FacilityWarehouse`). The subscription lifecycle gains the state Paused (Active ⇄ Paused). `SubscriptionStart` gains the parameter `renewal_day` (in its card) | large point | 3.8.0 · #374 |
| V7 | small | the warehouse takes a table from the catalogue | The table `AvailabilityProjection` moves from the catalog domain to the inventory domain. The audit log lifecycle (`AuditLogEntry`) loses the state Indexed: now Written → Retained | large point | 3.9.0 · #375 |
| C2 | small | the loyalty stub counts points per currency unit | The loyalty points stub counts points differently: only the code inside changes, the graph stays | small point | 3.9.1 · #376 |
| V8 | medium | roles are simplified | The legacy role (`DeprecatedRole`) is removed; its action `RoleMigration` moves to the editor role. The action `CartAbandonStub` is removed. The customer lifecycle loses the transition Provisioned → Closed | large point | 3.10.0 · #377 |
| V9 | large | the gift card pilot is closed | The domain `gift_cards` is removed whole: both tables, their lifecycle, roles and actions. The audit log (`AuditLogEntry`) loses its lifecycle | large point | 3.11.0 · #378 |
| V10 | small | the demo's first release | The gift wrap gets a new description and a new field `wrap_color`. After the merge, the demo's release 3.12.0 | large point, release flag | 3.12.0 · #379 🚩 |
| V11 | medium | work after the release | In the catalog domain, a new table `ProductReview` linked to the product, an action to submit a review and a new role, review moderator. The subscription lifecycle gains the state Expired | large point | 3.13.0 · #380 |
| V12 | medium | returns | Returns: the return request (`ReturnRequest`) gains the field `reason_code`, an action to approve a return and a new state. The pull request stays open | after Live, open | 3.14.0 · #381 |

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
