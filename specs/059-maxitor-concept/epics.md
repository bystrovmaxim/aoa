<!-- translated-from: epics.ru_draft.md @ 2026-11-04T19:50:28Z (filesystem mtime; draft is gitignored, no git history) · sha256:e4c0f7cd558e -->
# Maxitor concept: epics and stories

How the work is split into GitHub issues. Issues are created only on the maintainer's command.

---

## How it is organized

- **An epic** is a root issue of one self-contained area. It holds the goal, the boundaries and the list of stories. An epic has no branch or PR of its own.
- **A story** is a sub-issue of an epic titled "Epic k/N: …". A story has one branch `feature/issue-<n>-<slug>`, one PR and its own Spec Kit spec with a precise mockup.
- **A phase** is one commit of a story. In the story's description the phases are numbered checkboxes, ticked after each commit. The phases below are a sketch; the story's plan refines them.
- **The tail of every story** is the same, by Principle VI of the constitution: the closing check run, the documentation, the changelog. The phases below do not repeat it.
- **The shared context** is spec 059: terms, data model, catalog filling, UX and the mockup. Every epic refers to it. It reaches main together with the "Catalog storage" story of epic 1: in that story the model moves from the spec into the Maxitor package.
- **The order follows the dependencies.**

## Order

| Epic | Depends on |
|---|---|
| 1. Foundation: sign-in and the catalog | — |
| 2. Organization and access | 1 |
| 3. Story map | 1 |
| 4. Landscape: from C1 to a container's graph | 1; story 4.2 — on epic 5 |
| 5. Filling the catalog from code | — |
| 6. Catalog time | 1, 3, 4 |
| 7. Rooms on every level | 1; story 7.2 — on epic 3 |
| 8. Mob elaboration with the model | 3, 4, 5 |

Epics 1 and 5 start first and do not depend on each other: epic 5 changes the protocol and AOA, not Maxitor's interface.

---

## Epic 1. Foundation: sign-in and the catalog

**Goal.** Maxitor is closed behind a sign-in. The catalog — the organization, the map and the landscape — is stored in Maxitor as an AOA model, and every change of it is recorded with its author and time.

**Why together.** Without a sign-in a change has no author, and without storage the sign-in has nowhere to keep users.

**Context.** `model/enterprise_model.py` (the `organization`, `story_map` and `landscape` domains); `data-model` — "Editing and deletion", "Constraints checked separately"; mockup 1.1, 1.2, 2.

**Not included.** Administration screens (epic 2), the time track (epic 6).

**1/4. Old Maxitor routes under actions and resources** — this is [#278](https://github.com/bystrovmaxim/aoa/issues/278); it becomes a story of the epic.
- Why: while hand-written routes remain, the sign-in of a closed Maxitor can be bypassed.
- Done when: every Maxitor endpoint is an AOA action, and every store and service is a resource.
- Phases — in #278.

**2/4. Catalog storage**
- Why: the model of spec 059 becomes Maxitor's data.
- Done when:
  - the entities of the three domains live in the Maxitor package;
  - they are read and written only through actions and stored through a resource;
  - the model's constraints are checked on write;
  - Maxitor's graph shows the catalog's domains.
- Decide in the plan: which database, and which resource holds it.
- Phases:
  1. The catalog model in the Maxitor package.
  2. The storage resource.
  3. Read and write actions.
  4. Checking the constraints on write.

**3/4. Sign-in and invitation**
- Why: Maxitor stops being open.
- Done when:
  - without signing in only the sign-in screen is visible;
  - signing in works through a link sent by email;
  - an invited person accepts the invitation and becomes active;
  - a blocked or removed user cannot sign in;
  - after signing in Maxitor opens where the user stopped.
- Mockup: 1.1, 1.2, 2.
- Decide on the way: "The user's last place", "How an organization is created".
- Phases:
  1. Signing in through an email link.
  2. The invitation and its acceptance.
  3. Choosing an enterprise.
  4. The user's last place.

**4/4. Catalog change and undo**
- Why: every edit is visible and reversible.
- Done when:
  - every write to the catalog is a change with its author and time;
  - the catalog's state at any moment can be read;
  - ⌘Z undoes one's own last edit;
  - a past state never changes.
- Decide on the way: "Catalog change and the time track" — what counts as one change.
- Phases:
  1. The change log.
  2. The catalog's state at a moment.
  3. Undoing one's own last edit.

---

## Epic 2. Organization and access

**Goal.** Administrators manage the organization's people, and enterprise owners manage access to their enterprises.

**Context.** The terms "Organization administrator", "Enterprise access", "Owner", "User lifecycle"; `data-model` — "Organization, users and access"; `ux` — "Administration"; mockup 7.1–7.10.

**Related.** [#106](https://github.com/bystrovmaxim/aoa/issues/106) — signing in through a provider, the basis of SSO.

**Not included.** Roles inside an enterprise.

**1/3. User administration**
- Done when:
  - the user list and the access matrix stand on the canvas with the filter;
  - invitations work;
  - a user's card offers only the lifecycle moves;
  - the last active administrator cannot be blocked, removed or lose the mark.
- Mockup: 7.1–7.5.
- Phases:
  1. The administrator mark and the way into administration.
  2. The list and the matrix.
  3. Invitation.
  4. The user's card and the moves.

**2/3. Enterprise, owner and access**
- Done when:
  - an enterprise is open or closed;
  - the owner grants access; the administrator grants access and appoints an owner only when there is no active owner;
  - a closed enterprise without access is visible to the administrator only in administration, and the administrator can grant access to themselves;
  - the access card opens both from administration and from inside the enterprise.
- Mockup: 7.6–7.8, 7.10.
- Decide on the way: "Handing over an enterprise", "Deleting an enterprise".
- Phases:
  1. The owner and the rule of who manages access.
  2. The organization's list of enterprises.
  3. The access card in both places.
  4. A new enterprise.

**3/3. The organization's SSO**
- Done when: the organization has SSO connected with an email domain, and the first sign-in through it makes the user active at once.
- Mockup: 7.9.
- Decide on the way: "SSO settings".
- Phases:
  1. Signing in through a provider (#106).
  2. The organization's domain and the first sign-in.
  3. The "Sign-in and SSO" screen.

---

## Epic 3. Story map

**Goal.** An enterprise and its products are planned on a user story map, and a story is split into plan steps by container.

**Context.** The terms "User story map", "Backbone", "Business area", "Stage", "Release slice", "Initiative", "User story", "Plan step", "User story lifecycle", "Catalog editing", "Deletion"; `ux` — "Editing"; mockup 3.1, 3.3, 3.5, 3.8, 3.9, 4.1, 4.2, 4.6, 8.1–8.3.

**Not included.** Initiative content, mob elaboration with the model (epic 8).

**1/4. The enterprise's and the product's map**
- Done when:
  - the map stands on the canvas: a business area's card over its first stage, release slices from top to bottom;
  - a product's map shows how many stories of a cell are in other products and without a Software System;
  - there is a table mode and the shared filter.
- Mockup: 3.1, 3.8, 4.1.
- Phases:
  1. The enterprise's map.
  2. The product's map.
  3. The table and the filter.

**2/4. Editing the map**
- Done when:
  - a story is added in a cell and moved to another cell;
  - a stage, a business area (at once with its first stage) and a release slice are added at the edges of the map;
  - empty things can be deleted, nothing else.
- Mockup: 8.1, 8.2.
- Decide on the way: "Release slice lifecycle".
- Phases:
  1. A new story in a cell.
  2. Moving a story.
  3. The backbone and release slices.
  4. Deleting what is empty.

**3/4. A story and its plan**
- Done when:
  - the story panel is edited in place;
  - the state buttons are only the lifecycle moves, and a disabled button says what is missing;
  - a plan step points to exactly one container.
- Mockup: 4.2, 8.3.
- Decide on the way: "Plan step owner", "Person".
- Phases:
  1. The story panel.
  2. Moves with conditions.
  3. Plan steps.

**4/4. Initiatives**
- Done when: initiatives are shown as a table and a board, follow their lifecycle, each has exactly one author, and the map highlights an initiative's stories.
- Mockup: 3.3, 3.5, 3.9, 4.6.
- Decide on the way: "Initiative owner".
- Phases:
  1. The table and the board.
  2. The initiative lifecycle.
  3. The map by initiative.

---

## Epic 4. Landscape: from C1 to a container's graph

**Goal.** The enterprise's Software Systems, containers and interfaces are visible at C1 and C2, links between Software Systems are derived from container links, and a container opens its graph.

**Context.** The terms "Software System", "Digital product", "External system", "Enterprise boundary", "Container", "Interface", "Container link"; `data-model` — "Landscape", "Links are built at the container level", "A container and its graph"; `catalog-filling` — what is entered by hand; `ux` — "Where C1 and C2 live", "Interfaces at C2", "Scale"; mockup 3.2, 3.4, 3.6, 3.7, 4.3–4.5, 4.7, 5, 6.1, 6.2, 8.6–8.9.

**1/6. Software Systems**
- Done when:
  - the Software System list stands on the canvas with the filter;
  - a new digital product gathers the enterprise's containers, and a new external system is created at once with its container;
  - only a Software System without stories can be deleted.
- Mockup: 3.4, 3.7, 8.7.
- Decide on the way: "Rented SaaS we configure ourselves".
- Phases:
  1. The list.
  2. A new Software System.
  3. Deletion.

**2/6. Containers and interfaces** — depends on epic 5.
- Done when:
  - our container is created from a link to its graph, an external one together with its system;
  - the interfaces of our container are read only, those of an external one are entered by hand;
  - a container can be deleted only if nothing refers to it, and otherwise it says what is in the way.
- Mockup: 8.6, 8.8, 8.9.
- Phases:
  1. A new container from a link.
  2. The container's card.
  3. An external container's interfaces.
  4. Deletion by references.

**3/6. C1: the landscape and a product's context**
- Done when:
  - links between Software Systems are derived from the containers' interfaces;
  - the landscape is grouped by business area in backbone order;
  - a product's context shows its links.
- Mockup: 3.2, 3.6, 4.3.
- Phases:
  1. Derived links.
  2. Groups by business area.
  3. A product's context.

**4/6. A product's C2**
- Done when:
  - interfaces are drawn as ports: a used one is filled and shows the number of consumers, an unused one is hollow;
  - neighbouring Software Systems are collapsed into one node;
  - there are "Diagram", "Interfaces" and "Containers" tabs and the filter.
- Mockup: 4.4, 4.5, 4.7.
- Phases:
  1. The diagram with ports.
  2. Collapsed neighbours.
  3. Tables and the filter.

**5/6. The container layer**
- Done when: a container of the catalog opens its graph (C3) through the live link and through the history on GitHub, in today's Maxitor views.
- Mockup: 5.
- Decide on the way: "A container's private history".
- Phases:
  1. From a container to its graph.
  2. The live graph and the history.

**6/6. Hundreds of Software Systems and containers**
- Done when:
  - the breadcrumbs switch to a neighbour on the same layer;
  - ⌘K searches across layers;
  - the left panel holds mine, pinned and recent, and the rest is available as a list.
- Mockup: 6.1, 6.2.
- Phases:
  1. Breadcrumb switchers.
  2. ⌘K search.
  3. Mine, pinned, recent.

---

## Epic 5. Filling the catalog from code

**Goal.** The interfaces and integrations of our container are derived from its code, not entered by hand.

**Context.** `catalog-filling`; the terms "Interface", "Container link".

**Touches.** `open-gnomon-protocol`, `aoa-action-machine`, `aoa-fastapi-adapter`, `aoa-mcp-adapter`, Maxitor.

**Not included.** "Checking links" — reconciliation with tracing comes next.

**1/3. An adapter is an interface node in the graph**
- Done when: every AOA adapter prints an interface node into the graph, with its name, protocol and exposed actions. This closes the dictionary question "Interfaces in the graph".
- Decide on the way: "Endpoint".
- Phases:
  1. The interface node in the protocol.
  2. The FastAPI adapter.
  3. The MCP adapter.

**2/3. A resource declares its target**
- Done when: a resource that calls another container declares its target in code, and the graph holds a "resource → target interface" edge.
- Decide on the way: "How a resource declares its target in code".
- Phases:
  1. Declaring the target on a resource.
  2. The edge in the protocol and the graph.

**3/3. Maxitor derives interfaces and integrations**
- Done when: through a container's link Maxitor reads its graph, writes our container's interfaces and links into the catalog, and updates them with every graph version.
- Decide on the way: "Our container without AOA", "Our container without its own repository".
- Phases:
  1. Reading the graph through the container's link.
  2. Interfaces and links in the catalog.
  3. Updating with a new graph version.

---

## Epic 6. Catalog time

**Goal.** On every layer it is visible how the catalog changed: the track in the header, a past moment and a comparison of two moments.

**Context.** The terms "Two times", "Catalog comparison"; `data-model` — "Comparing two moments"; `ux` — "Time track", "Comparing two moments"; mockup 6.3, 6.4, 6.7, 6.8, 6.10, 6.11, 9.1–9.7.

**Related.** [#303](https://github.com/bystrovmaxim/aoa/issues/303) — it shows which graph version was running at a catalog moment.

**1/3. The track in the header**
- Done when: the track shows the volume of changes of the open page with a stretchable precision and lists the changes of the selected interval.
- Mockup: 6.3, 6.7.
- Phases:
  1. The volume of changes by page.
  2. Precision.
  3. The changes of an interval.

**2/3. A past moment**
- Done when:
  - a past moment is read only and acts on all layers;
  - on the container layer the graph version that was in effect then is suggested, but the graph does not switch by itself.
- Mockup: 6.4, 6.8, 6.11.
- Phases:
  1. The catalog at a moment on all layers.
  2. The graph version hint.

**3/3. Comparison A → B**
- Done when:
  - the open view is marked as in the graph version comparison;
  - a click shows "before → after";
  - the comparison goes across layers and is read only;
  - on the container layer it offers to compare the graph versions too.
- Mockup: 6.10, 9.1–9.7.
- Phases:
  1. Comparing two states by `id`.
  2. Choosing A and B on the track.
  3. Marking the map.
  4. Marking the landscape and the lists.
  5. The container layer: "compare the graph too".

---

## Epic 7. Rooms on every level

**Goal.** The organization's room works from the enterprise picker to a container's graph, and editing in it is shared.

**Context.** `ux` — "Rooms", "Editing"; the term "Catalog editing"; spec 028; mockup 6.5, 6.6, 6.9, 8.5.

**1/2. The organization's room across layers**
- Done when:
  - a room can be opened on any layer;
  - only a member of the organization can enter;
  - following goes across layers and stops with an explanation at a closed enterprise without access.
- Mockup: 6.5, 6.6, 6.9.
- Decide on the way: "Room" — an entity of the model or the state of the room server.
- Phases:
  1. The room belongs to the organization.
  2. Following across layers.
  3. A closed enterprise while following.

**2/2. Shared editing** — depends on epic 3.
- Done when: in a room everyone sees the others' edits at once, each object shows who is editing it, and there are no locks.
- Mockup: 8.5.
- Phases:
  1. Live edits for everyone.
  2. Who is editing what.

---

## Epic 8. Mob elaboration with the model

**Goal.** The model reads a story and the containers' graphs and proposes a Software System and plan steps, and the team accepts, edits or rejects each proposal.

**Context.** The term "Mob elaboration"; `data-model` — "Editing and deletion" (the model's proposals are not catalog data); `ux` — "Editing"; mockup 8.4.

**Not included.** "Plan step and the graph" — how a step's plan is recorded as an edit of the container's graph.

**1/2. The model proposes**
- Done when: from a story and the graphs of its product's containers the model proposes a Software System and plan steps, and every proposal says what it is based on.
- Decide in the plan: which model, and how the graph and the story are passed to it.
- Phases:
  1. What the model gets as input.
  2. Proposing the Software System.
  3. Proposing the steps.

**2/2. Accept, edit, reject**
- Done when:
  - an accepted proposal becomes an ordinary edit by whoever accepted it;
  - a rejected one does not stay in the catalog;
  - "Ready" lights up by the usual rules.
- Mockup: 8.4.
- Phases:
  1. Accepting and rejecting.
  2. Editing a proposal before accepting it.

---

## Outside the epics

These dictionary questions belong to no epic and wait for a separate decision:

- a user's rights inside an enterprise;
- initiative content;
- deployment (C4 Deployment);
- checking links against tracing;
- plan step and the graph ("graph as a plan").
