# Read a diagram without zooming in

Every field, table and line of the ERD, and every node and link of the full graph, has one card. Rest the pointer on an element, and it says what the element is, what it is for, what changed in a comparison, and shows a lifecycle's picture. You can read a large diagram from far away, and hide what you do not need on it.

[21_element_card.py](../../examples/step_26_maxitor/21_element_card.py) ([notebook](../../examples/step_26_maxitor/21_element_card.ipynb)) runs the read a card makes, case by case.

## The card

The card waits about 300 ms, so moving across a diagram opens nothing. It stays while the pointer is on it or on its element, and closes when the pointer leaves both, on Escape, or when you drag or zoom.

| Rest on | The card shows |
|---|---|
| a field | its name, type and description |
| a lifecycle field | the same, and a small picture of the lifecycle |
| a table | its description, how many fields it has, and its lifecycles |
| a line | what joins what, its kind and cardinalities, and its description |
| a node of the full graph | what it is, its name and description, and a lifecycle's picture |
| a link of the full graph | its two ends |

In a table's card the fields are hidden behind **N fields**; open or close them on one table, and every table follows, in this browser, also after a reload. With the list hidden, **N fields** counts what changed in it, such as `+1 ~2`. Rest on a field: its type and description appear in a fixed place below the list, so the list stays short and the card does not move. On a phone, tap the field. Rest on a lifecycle field and its picture stays bright while the others dim.

The speech-balloon icon on the toolbar switches cards off and on, for you, in this browser; they start on.

A click on a name copies it, on every field and table. On a phone a tap opens the card, and a button in it copies the name.

The use-case and lifecycle diagrams keep a small white label. Folded domains and bundles on the full graph behave as before.

## From far away

When rows are too small to read, a card of one row would be of no use, so the pointer anywhere on a table opens the table's card. Under 10 px a row counts as too small for a pointer, and under 20 px for a finger: a person on a phone taps a table and sees it all without zooming in.

## In a comparison

Every card has one shape. At the right of its name stands the disk of the Changes filter: `+`, `−` or `~` in their colours, and a grey `=` for unchanged. Below, a changed element says what happened. A table that moved to another domain counts as changed and says so. A table with a changed field wears `~`, though the table itself did not change. Its open list shows what changed first, with its sign, and rest on a field whose type changed: it reads `old → new` below the list. In a lifecycle's picture added and removed states wear their colours, as on the full diagram.

The change stepper's card works as before, and while it stands a hover opens no other card. A click on the full graph also works as before: on a change it opens that change's card.

## Hide a table's fields

The chevron at the right of a table's header collapses it, and the icon with two chevrons on the toolbar collapses every table. A collapsed table is as wide as a whole one, and keeps:

- its primary key and foreign keys;
- any other row a line belongs to;
- in a comparison, every added, removed and changed row, so the stepper never leads to something hidden.

The last row says how many fields are hidden, and the table's card still lists them all.

- **Tables move.** The diagram is laid out again. The header you clicked stays where it was, and collapsing all keeps your view.
- **New tables follow.** After collapsing all, a table that 1-hop or a filter brings in comes collapsed. A table you opened by hand stays open.
- **The default** is everything open, including tables 1-hop brings in.
- **A specialization block** does not collapse as a whole; its tables collapse one by one.

## In a room and in the address

Someone following you sees all you do: your card on the same spot of the diagram, whatever their screen, the field list open or closed, the field you point at, the scroll, and the row you point at in the list of changes. Their own cards switch does not hide your card from them.

Without following, the room shares the picture itself. Collapsing belongs to the room, like filters, and is kept in the address as `collapsed` and `except`, so a copied link opens the same picture. Your cards and whether a table's card shows its fields stay yours.

## Where descriptions come from

From your model: `Field(description=...)` on an entity's fields and lifecycles, `description` on a role, and on `@connection`. Version 1.2 of the [Open Gnomon Protocol](../../packages/open-gnomon-protocol/README.md) carries them in the graph file. An `id` the model never declared has no description, and the card leaves that line out.

A graph of an earlier version still opens, and its fields have no description. Comparing a 1.1 graph with a 1.2 one marks those elements as changed once, because their descriptions are new.
