<!-- translated-from: ux.ru_draft.md @ 2026-11-04T19:52:14Z (filesystem mtime; draft is gitignored, no git history) · sha256:0b4c3e3fc1e6 -->
# Maxitor concept: how people move through it

Mockup: [mockup/index.html](mockup/index.html). This page records why it is built the way it is.

---

## Layers

Maxitor is four layers nested in each other. Each layer matches an entity of the model:

| Layer | Entity | What people do there | C4 level |
|---|---|---|---|
| Organization | `OrganizationCoreEntity` | choose an enterprise, manage people and access | — |
| Enterprise | `EnterpriseCoreEntity` | plan the development of the whole enterprise, look at the landscape | C1 of the whole enterprise |
| Digital product | `DigitalProductSpecEntity` | keep the product's map, work out stories, look at containers | C1 of the product and C2 |
| Container | `ContainerCoreEntity` | read the code's graph: domains, actions, entities, lifecycles | C3 and code |

## Where people spend their time

The main observation: **moving between layers is rare, while work inside one layer is long and dense.** So the interface is built so that:
- everything inside a layer is at hand;
- a neighbour on the same layer is one click away;
- going down and up between layers is explicit but infrequent.

| How often | Path | Layer |
|---|---|---|
| Every day | Product map → story → its plan steps → the graph of a step's container → back to the story | product ↔ container |
| Every day | A container's graph: domains, ERD, lifecycles, comparing versions | container |
| Every day | Switch to a neighbouring product or container without going up | product, container |
| Once a week | The enterprise's whole map by release slice, the list of initiatives, the C1 landscape | enterprise |
| Rarely | Switch enterprise (a studio has several) | organization |
| Rarely | Invite or block a user, open or close an enterprise | organization |
| Once a session | Sign in | — |

## Eleven rules

1. **Maxitor opens where the user stopped.** After signing in, the user lands straight on the last layer, object and tab. The enterprise picker is shown only to a user who comes for the first time. The most frequent path must not start with a choice.
2. **Breadcrumbs are switchers too.** The header always shows the path `Organization / Enterprise / Product / Container`. Clicking a name goes up to that layer. Clicking the arrow next to it opens the list of neighbours on the same layer, with search. So going down and up is visible, and switching sideways costs one click.
3. **⌘K search jumps across layers.** It searches the whole enterprise: products, containers, stories, initiatives. From it one lands right on the object, skipping the layers in between.
4. **Every layer has its own left panel in the style of today's Maxitor.** On the container layer it is today's panel: Applications, Domains, ERD, lifecycles. On the layers above it holds their views and the layer's children. There may be hundreds of children, so the panel holds only **mine** (where I am the owner), **pinned** and **recent**, and an "All 176 →" row leads to a list with search. This is the most frequent way down, so it is always in sight.
5. **The same view looks the same on different layers.** The product map is the same as the enterprise map, but with only this product's stories. The backbone stays whole, so it is visible which part of the process the product falls into. The product's initiatives are the same list of initiatives with a filter.
6. **A story opens as a panel on the right and does not leave the layer.** The panel holds its plan: the steps with their containers. A step in another product's container is marked: that is cross-product impact. Clicking a step's container is that most frequent way down to the graph.
7. **Any diagram switches to a list.** C1 and C2 can be viewed as a diagram and as a table. The diagram is for understanding the structure, the table for finding, sorting and comparing.
8. **Everything lives on a canvas and is handled like a graph.** Views have no title bar: a view is named by the selected row of the left panel. The canvas always has one layout: tabs at the top centre, the filter at the top left, zoom at the bottom left, the legend at the bottom right. **Tabs and the filter are different things.** Tabs (as in the Events explorer, with counts) choose the viewing mode, that is, the point of view: "Map · Stories", "Table · Board", "Diagram · Interfaces · Containers", "Groups · Links". A view with one point of view has no tabs. **The filter is always the same**: a panel like DOMAINS/KINDS on the ERD, with accordion sections (the first open, the others closed), rows with an icon in a coloured circle and no checkboxes, a row that is off goes pale, and a switch at the bottom collapses the panel to icons. States, slices, products, authors, protocols are always the filter, never tabs. Tables lie on the canvas too: the wheel zooms, dragging moves, ⊡ shows everything. A table fits the width, and a long one is moved down. The filter and the tabs do not reset the camera.
9. **Catalog time is one track on every level; code time is its own.** The catalog time button is always in the header, and what it shows depends on the page. On the container layer today's graph version track stays next to the graph (see "Time track").
10. **A room works on every level.** "Open a room" is in the header from the enterprise picker down to the container's graph. "Go to" and "Follow" lead across layers.
11. **Hundreds are the norm, not the exception.** An enterprise has hundreds of Software Systems and containers. So search, filters and tables are the main navigation, diagrams show groups and open on a click, and counts are visible before the click (see "Scale").

## Where C1 and C2 live

| View | Layer | What it shows |
|---|---|---|
| **Landscape** (C1, System Landscape) | enterprise | groups of Software Systems by business area in backbone order, "Off the map", and external systems on the boundary; a group opens to its Software Systems, and a Software System to its context |
| **Context** (C1, System Context) | product | the product in the centre and the Software Systems it is linked to: other products and external systems |
| **Containers** (C2) | product | the product's containers inside its frame, each with its published interfaces as lollipops; outside — the Software Systems they are linked to, collapsed into one node that opens to its containers; the filter on the left |
| **Graph** (C3) | container | today's Maxitor: domains, actions, entities, lifecycles |

Links at C1 are not drawn by hand: they are a roll-up of the containers' links. The number on a link is how many interfaces stand behind it. A shared container, for example the residents' mobile app, is marked "also in: Billing".

## Interfaces at C2

- Every published interface is drawn explicitly, as a lollipop (from UML) on the container's left edge: a row with its name and protocol.
- A filled circle means the interface is used, with the number of consumers on the right. A hollow dashed one means it is **unused**: this shows at once, without searching.
- A link goes from the consumer straight into the lollipop. The line needs no label: the interface is labelled at the port.
- The flow goes from left to right: clients → services → data → neighbouring Software Systems. Orange lines are calls into other products; light ones are calls into the product from outside.
- A collapsed neighbouring Software System shows only those of its interfaces that concern the product.
- The filter on the left, like DOMAINS and KINDS on the ERD:
  - used and unused interfaces;
  - protocols;
  - whose interface: inside the product, of other products, of external systems;
  - open or collapse all neighbours.

## Scale

An enterprise has hundreds of Software Systems and containers, so every view is designed for hundreds:

| Where | How it works |
|---|---|
| Left panel | mine, pinned, recent, and an "All N →" row into the list; a container shows only a graph dot on the right: green — live, grey — history, no dot — no graph; the rest is in the tooltip |
| Switcher in the breadcrumbs | search first, then mine, pinned and recent, then the first rows of the whole list and an "All N as a list" link |
| Software System list | search, filters (kind, business area, owner, "mine only"), sorting, pages, saved views |
| C1 landscape | groups by business area; links between groups are the sum of interfaces; the links of one Software System are visible only once it is selected (1-hop) |
| A product's C2 | neighbouring Software Systems are collapsed into one node with the number of containers and open on a click; links to a collapsed Software System are gathered into one line |

**A Software System's group on the landscape is derived, not stored.** It is the business area where its stories lie. A product with stories in several areas stands in each of them: that is the fair price for nobody keeping the groups by hand. Software Systems without stories are gathered in "Off the map", external systems in a separate group on the boundary.

## Time track

Time is the same thing on every level; only what counts as a change differs.

- **Not a list of PRs but a chart of the volume of changes.** A bar shows how many changes there were in the interval.
- **The precision stretches:** hour, day, week, month; smoothly with the wheel or a pinch over the track.
- **The track depends on the open page.** On the enterprise map the whole map counts, on the landscape — Software Systems and interfaces, on a product's page — only its objects. So the track differs from page to page.
- **Clicking a bar shows the changes of the interval; clicking a change opens the catalog at that moment.** This acts on all layers at once, because every change saves the state of the whole catalog. While a past moment is selected, everything is read only, and a yellow strip under the header has a "Back to now" link.
- **The container layer has two times, and they stand in different places** (decided: keep both). In the header, as on every layer, is catalog time: changes of the container's record (owner, interfaces, products). In the workspace row is **today's Maxitor graph version mechanism, unchanged** (specs 030 and 051): the track of commits from the repository, a big dot where the graph changed, a small one where only the version was raised, Live after the dashes, one version or a comparison of A and B.
- **The link between the two times is a hint, not automation.** If a past catalog moment is selected in the header, "v1.3.0 was in effect then →" appears next to the graph version button; the graph switches only on a click.

## Comparing two moments

Screens 9.1–9.7 of the mockup. The catalog comparison speaks the same language as the graph version comparison in Maxitor (spec 038).

- **A and B are chosen on the same track in the header.** The "One moment · Comparison" switch stands where it does for graph versions. B is "now" by default. Between A and B the bars are dark, and it shows at once how many changes of this page fall into the interval.
- **The difference is drawn on the view itself.** On the map, at C2 and in the lists the union of A and B is shown: added is green, removed is red with a dashed outline, changed is amber, the rest is faded. A moved story is amber in its new place, and a faint dashed outline stands in the old one.
- **"Before → after" opens on a click.** In a comparison the story panel shows every changed property with its author and time.
- **The filter is the same**, and it gains a "Changes A → B" section: added, removed, changed, unchanged.
- **The comparison goes across layers**, like a past snapshot, and the strip under the header reminds of it and counts the page's changes. On the container layer the strip has "compare the graph too": it switches on the comparison of the graph versions that were in effect at A and B. The graph itself does not switch.
- **If nothing changed on the page**, it says so, and the view is drawn as usual, without fading.
- **A comparison is read only**, like a past snapshot: it has no "+", no moving and no edit buttons.

## Administration

Administration is part of the organization layer, screens 7.1–7.10 of the mockup. Only organization administrators see it. It can be entered from two places: under the cards in the enterprise picker and from the left panel of any enterprise. People come here rarely, so it has no place in the header.

- **Three sections in the left panel**: users, enterprises, sign-in and SSO. Under them, short lists of signals: who has not accepted an invitation yet and who is blocked.
- **Tables live on the canvas**, like every view, and the filter is the same panel: the user's state, role and how they appeared. Users have two viewing modes: a list and an access matrix with people in rows and enterprises in columns.
- **A user's card opens on the right**, like a story. Its buttons are only the lifecycle moves from the current state. Removal is confirmed in a separate window, because it is final, and the window lists what the person owns.
- **The last-administrator rule is visible, not only checked.** For the last active administrator the "Block" and "Remove" buttons and the administrator mark are disabled, and it says why.
- **The owner manages access where they work.** The "Open · you are the owner" line under the enterprise's name in the left panel opens the access card over the map, without going to administration. The administrator manages access and may appoint a new owner only if there is no active owner: none was appointed, or the owner is blocked or removed.
- **A closed enterprise without access is visible to the administrator only in administration**: its name, owner and access list. Its description and number of products are hidden. If the owner is not active, the administrator can grant access to themselves, and that stays in the catalog history.
- **Where the decision is not yours, the switch is disabled**, and the caption says who decides: for example, "granted by the owner, Maria Lebedeva".

## Editing

Screens 8.1–8.9 of the mockup. Editing happens in place, as in Miro or Notion, and every action at once becomes a catalog change with its author and time.

- **Undo is always at hand.** After an edit a note appears at the bottom, such as "Moved: …", with "Undo ⌘Z". Every change is visible on the time track. A past snapshot is read only: it has neither "+" nor dragging.
- **The map is edited where it is seen.** "+ story" appears in a stage × release slice cell on hover, a card is dragged into another cell, and "+ stage", "+ business area" and "+ release slice" stand at the edges. A new business area gets its first stage at once: without one its card has nowhere to stand.
- **The story panel is also the form.** The title and text are edited in place. The Software System, initiative, release slice and owner are chosen with the arrow next to the value. The state buttons are only the allowed moves, and a disabled button says what is missing.
- **Mob elaboration: the model proposes, people decide.** The model's proposal stands in the story panel in a dashed frame. Every proposal says what it is based on: what the model found in the containers' graphs. An accepted proposal becomes an ordinary edit by whoever accepted it, and a rejected one does not stay in the catalog.
- **Editing is shared and has no locks.** In a room each object shows who is editing it now, and a new card appears for everyone while it is being written.
- **Forms ask only for what the code does not have.** A new container: name, kind, a link to the graph, products and owner. What the container publishes and uses, Maxitor shows from the graph right in the form. A new Software System: name, description and containers; for an external system, a web link.
- **The interfaces of our container are read only**; those of an external container are entered by hand in its card.
- **Only what nothing refers to can be deleted.** Instead of a "Delete" button it says what is in the way and where: for example, which plan steps point to the container.

## Rooms

- A room works on every level, from the enterprise picker to the container's graph, and belongs to the organization. Only a member of the organization can enter, and the name comes from the account: a separate name dialog is not needed.
- The participants' circles stand in the header. A participant's card says which level and view they are on and offers "Go to" and "Follow".
- When following, the screen goes after the leader across layers. The frame and the strip under the header are in the leader's colour, and everyone keeps their own zoom. Following stops with a button, the Esc key or one's own move.
- If the leader goes into a closed enterprise you have no access to, following stops with an explanation.
- Pointers, shared filters and the ban on following in a circle stay as in today's rooms (spec 028).

## What the mockup suggests adding to the model

None of this is required for any screen. Everything the mockup shows comes from the current model. But three things are worth discussing:

- **The user's last place** (rule 1). It is the state of the interface, not the catalog. I suggest keeping it outside the model, on the client side or in separate user settings.
- **Catalog change** — one change with its author and time, after which the state of the whole catalog is saved. The time track is built from them. The word is already in the dictionary together with the term "Catalog editing".
- **Which product a shared container is opened through.** A container may belong to several products. The breadcrumbs show the product one came from. If the container is opened from search, its first product is shown, and the others are listed next to it.

## What the mockup does not show yet

- The "Changes A → B" section in the filter of C2 and of the lists: in the mockup it exists only on the map.
- Comparison marks on the C1 diagrams.
