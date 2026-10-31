# Compare two versions of a service's graph in Maxitor

With a [graph history open](open-a-graph-history.md), Maxitor shows what changed between any two versions on the ERD: what was added, removed and changed, table by table and field by field, with the two pull request messages side by side.

[17_compare_two_versions.py](../../examples/step_26_maxitor/17_compare_two_versions.py) ([notebook](../../examples/step_26_maxitor/17_compare_two_versions.ipynb)) runs the comparison below against a real port and prints what Maxitor answers.

## Pick two versions

Open the version picker and switch **One** to **Diff**. The track now holds two handles: **A**, the older version, and **B**, the newer one, with the stretch between them dark. Switching keeps your version as B and puts A on the one before it.

| To | Do |
|---|---|
| move one end | drag its handle, click a point near it, or focus it and press ← → |
| move both, keeping the distance | drag the dark stretch, or Shift + ← → |
| step the whole range by one version | the arrows in the version button, or Shift + ← → with the picker closed |

Roles follow position: drag A past B and they swap. Two handles never stand on one version. The address keeps `mode=diff`, `a` and `b`, so a link opens the same comparison; a link that names them the other way round opens with them swapped.

Under the track stand A's message on the left and B's on the right. "N versions between" opens the versions in between, newest first.

## Read the ERD

The version button carries this diagram's counts — `◷ A 0.8.0 → B 0.9.0  +15 −1 ~3` — or "no changes". The ERD draws everything in A or B:

| Table | Looks |
|---|---|
| added | green header and frame, `+` |
| removed | red header, dashed frame, `−` |
| changed inside — its own properties or any field | amber header and frame, `~`, a soft halo under it |
| unchanged | grey and faded |

Fields carry the same marks. A field whose type changed reads `~~str~~ → str | None` when it fits. A field that now points at another table keeps one amber link, solid to where it points in B and thin and dashed to where it pointed in A.

Click a marked table or field: its card lists every property that changed, before and after.

Beside the version button a stepper walks through what changed: the arrows or Shift + ↑ ↓ go to the next and the previous, and a click on its middle opens the list, where any change can be picked directly. A step goes to the table, field or line, marks it and opens its card. The [full graph](read-the-full-graph-map.md) steps the same way.

## Filter and paint

The filter panel has a **Changes** section in Diff — Added, Removed, Changed, Unchanged — next to Domains and Kinds. Switching a row off hides its tables; 1-hop then brings back the tables one link away from those left. The three points at the foot of the panel choose what paints the headers: Domains, Kinds or Changes. Diff starts painted by Changes.

A page that exists in only one version — a domain added in B — stays reachable: the left panel lists what exists in either version and marks it `+` or `−`.

## Open pull requests come after Live

The track reads: versions, Live, then the open pull requests by date, the oldest first. A pull request is work ahead of what runs, so **A = Live, B = a pull request** shows what it would add. Roles still follow position: Live is B for anything older and A for a pull request.

## Read use cases

The same comparison on a domain's **Use case view**, and on **Use case all domains view**, which draws every role and every use case at once. Actions, roles and links take the ERD's marks: an added one is green, a removed one red and dashed, a changed one amber, the rest grey and dim. A role is drawn in its colour itself, with no box.

A use-case diagram does not draw an action's parts, so an action can look the same while it changed. When anything it owns changed — params, result fields, aspects and what they check, error handlers, object rules, its link to a resource or a domain — **the action is marked changed**, and its card says the action is the same and lists its parts by group, before and after:

```text
~ InvoiceSettleAction                                    changed
The action is the same; its parts changed.
Params
  + idempotency_key
Result
  ~ capture_txn
    properties.description  Capture transaction id → The settlement's reference
```

What the diagram draws itself is never a part: a role, another action, a parent. A changed parent is marked on the parent, and an entity a field points at is the ERD's to show. An added or removed action keeps that status. A link has a card too: `~ DependSameDomainAction → SupportPingAction`, `properties.mode  extend → include`.

The version button counts everything marked: actions, roles and links. The stepper walks them in that order, each with its card.

| Panel section | What it does |
|---|---|
| Domains | hides a domain's actions and the roles left with none |
| Elements | Actions and Roles, grey, painting nothing |
| Changes | hides a kind of change, in Diff |

**1-hop**, on by default, brings back what stands one link from what the filters left, even what a filter hid, as on the ERD. So to see actions alone, switch Roles off and 1-hop off.

Hovering an action, a role or a link keeps it, its links and what they reach lit and dims the rest. Links are easy to hit at any zoom.

[19_changed_inside.py](../../examples/step_26_maxitor/19_changed_inside.py) ([notebook](../../examples/step_26_maxitor/19_changed_inside.ipynb)) runs every case of "changed inside" and prints what Maxitor answers.

## Read lifecycles

In Diff the left panel marks lifecycle rows: `+` and `−` for a lifecycle only one version has, `~` for one in both where something changed. A `~` appears only on lifecycle rows, because a domain can hold a dozen of them and there is no other way to find the changed ones.

Open a row and both versions are drawn at once. Added states and transitions are green, changed ones amber, removed ones red and dashed, everything else grey and dim. A lifecycle of one version is all green or all red, and the button counts states and transitions: a new lifecycle of four states and three transitions reads +7. The entry and exit dots take the colour of their arrows but are not counted.

- **A transition is known by the state it leaves and the state it enters.** Two transitions into one state are two elements. A transition sent to another state is a red one and a green one, never amber.
- **Every property counts.** A state whose order alone changed is amber, though it looks the same. Its card says what changed.
- **A click, the stepper and Shift + ↑ ↓** work as on the ERD. A transition's card names its two states.
- **The filter panel** has Elements, by kind of state, and Changes. The gear shift starts on Changes; on Elements a state keeps its kind's fill, its outline says its status. 1-hop is on at first, so to see one kind alone switch 1-hop off.
- **A lifecycle absent from the shown version** says so, and the left panel leads elsewhere.

[20_lifecycle_diff.py](../../examples/step_26_maxitor/20_lifecycle_diff.py) ([notebook](../../examples/step_26_maxitor/20_lifecycle_diff.ipynb)) runs these cases and prints what the diagram reads.

## Read the full graph

On the full graph the same comparison is drawn by [the map](read-the-full-graph-map.md).

## In a room

Everyone in a room sees the same two versions. Someone following you sees your picker open, the handle you drag as you drag it, the version under your pointer and its card; and your stepper, its list and your pointer on the same row.
