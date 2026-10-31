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

Roles follow position: drag A past B and they swap. Two handles never stand on one version, and Live can only be B. The address keeps `mode=diff`, `a` and `b`, so a link opens the same comparison; a link that names them the other way round opens with them swapped.

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

Beside the version button a stepper walks through what changed: the arrows go to the next and the previous, and a click on its middle opens the list, where any change can be picked directly. A step goes to the table, field or line, marks it and opens its card. The [full graph](read-the-full-graph-map.md) steps the same way.

## Filter and paint

The filter panel has a **Changes** section in Diff — Added, Removed, Changed, Unchanged — next to Domains and Kinds. Switching a row off hides its tables; 1-hop then brings back the tables one link away from those left. The three points at the foot of the panel choose what paints the headers: Domains, Kinds or Changes. Diff starts painted by Changes.

A page that exists in only one version — a domain added in B — stays reachable: the left panel lists what exists in either version and marks it `+` or `−`.

## Read the full graph

On the full graph the same comparison is drawn by [the map](read-the-full-graph-map.md).

## In a room

Everyone in a room sees the same two versions. Someone following you sees your picker open, the handle you drag as you drag it, the version under your pointer and its card; and your stepper, its list and your pointer on the same row.
