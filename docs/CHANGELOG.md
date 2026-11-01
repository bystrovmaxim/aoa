# Changelog

## [2026-11-01] — Before a pull request, only the browsers run on your machine

`scripts/check_before_pr.sh` used to repeat everything GitHub then ran again. It now runs only the check in three browsers, which GitHub's machines cannot do, and leaves the proof on the commit. All the rest is checked once, on the pull request. The full run still exists for when you want everything on your machine, and the speed tests run only there.

## [2026-11-01] — Secrets stay out of the repository, and the checks stop any that try to return

The file `.env` with working credentials had been public in this repository since March. Those credentials have been replaced, and the file is gone from the whole history, so branches and tags no longer contain it. Every commit therefore has a new identifier, and links to old commits may no longer open.

Git now ignores `.env` files and the `certificates` folder, so a careless `git add -A` cannot pick them up. An `.env.example` stays in the repository, because it shows the shape and holds no real values.

A new check looks through the tracked files for secrets, both before a commit and on every pull request. A hook covers the commit on your machine, and CI covers a commit made without it. When the check fails, it names the file and never prints the value.

The empty `aoa_run` folder is gone as well. It held no code, and `aoa-run` still installs under the same name with the same extras.

## [2026-11-01] — The checks now have two homes, and a pull request carries the proof of the long one

The long check that finishes a change no longer needs the internet. It used to download a build tool from the package index for every package it packed, and on a poor connection it failed for no reason of ours. Those package builds, and the smoke test that installs them, now run on GitHub with every pull request, where a broken package is caught before a release and never blocks a local run.

A pull request now gets a real result. GitHub runs the static checks, the client's build and tests, the diagram checks, the tests of every package and the saved graph files on its own machines, so the answer does not depend on one computer.

The check in three browsers stays on the maintainer's computer, because GitHub's machines have no graphics card and Firefox cannot draw the map there. GitHub controls it instead: the full run leaves a mark on the exact commit it proved, and a pull request whose commit carries no mark fails. A new commit has no mark, so what merges is what passed.

Two scripts now say which check belongs to which moment. `scripts/check_before_commit.sh` runs the cheap steps, during the work and before every commit. `scripts/check_before_pr.sh` runs everything on a pushed commit and leaves the mark, and no pull request is opened until it has passed.

The speed tests that used to fail on a busy machine run only in the full local run. The saved graph files are always checked, even when another step failed, and a green run now brings a stale one up to date instead of failing on it.

## [2026-11-01] — Maxitor shows two versions side by side, and a room compares them together

The picker's third mode now works. **Side by side** stands the older version on the left and the newer on the right, on every diagram, each laid out as that version really was. A serious change can rebuild a picture completely, and here you see both pictures rather than one drawn over the other.

The two halves work as one comparison. Rest the pointer on an element and both light it; **Track** then brings it into view on the other side, so nothing has to be hunted for. A click selects it in both. An element with no pair, removed on the left or added on the right, puts the other half out and says it is not in that version. Filters, collapsed tables, the counts and the stepper are common to both halves, while pan, zoom and layout mode belong to each. On a phone an **A / B** switch flips one diagram between the versions.

A change inside a table now marks the table on both sides, even when the row exists on one. A change in a lifecycle marks its table too, in Diff as well, because a lifecycle is part of the table.

In a room everyone shares the versions, the view, the filters, the layout of each half and the selection. Following is exact: each half is the leader's, zoom included, with the left panel and every card in the half where it stands.

The left panel gained a filter icon in its corner that leaves only what changed, so a new pair of versions can be read top to bottom. The panel also stays as you left it after a reload.

Following on the full graph used to line up the bottom of two screens of different heights; it now lines up the top, as on every other diagram. A follower no longer loses a zoom made while its drawing lands, and the address holds the camera closely enough that a reload at high zoom stays put.

## [2026-11-01] — Maxitor reads from far away: one card for everything, and tables that collapse

Every field, table and line of the ERD, and everything on the full graph, now has one white card. Rest the pointer on an element and it says what the element is, what it is for and, in a comparison, what changed. The old tooltips with their long dotted paths are gone. A click on a name now only copies it, on every field; it used to open a card on changed ones.

The card is built for looking at a big diagram without zooming in. When rows are too small to read, the pointer anywhere on a table opens the whole table: its description, what changed, and a small picture of each lifecycle. Its fields open from one control, and that choice holds for every table in your browser. Rest on a field and its type and description appear below the list; a lifecycle field lights its picture. A click on a picture opens the full lifecycle. On a phone a tap does what the hover does, someone following you in a room sees all of it on the same spot of the diagram, whatever their screen, and another icon switches cards off if you prefer the diagram quiet.

Tables can now collapse. A chevron on the header leaves only the keys and the rows with lines, and in a comparison everything that changed; an icon on the toolbar does it for every table. A collapsed table keeps its width and its lines, the header you clicked stays where it was, though other tables move as the diagram is laid out again. A room shares this, and the address keeps it.

Descriptions now reach the graph. Field descriptions, along with those of lifecycles, roles and `@connection`, used to stop at the code; the Open Gnomon Protocol gained version 1.2 to carry them. Earlier graphs open as before, but comparing a 1.1 graph with a 1.2 one marks those elements as changed once, because their descriptions are new.

A table that moved to another domain now counts as changed in a comparison, and says so. Status disks are one set everywhere, with a grey `=` for unchanged in the filter panels too.

## [2026-11-01] — Maxitor compares two versions on lifecycle diagrams

Lifecycle diagrams now take part in Diff, the last diagram that did not. States and transitions turn green, amber, or red and dashed, everything else goes grey and dim, the version button counts them, and the stepper walks them with a card on each. A lifecycle only one version has opens from the left panel, all green or all red.

The left panel also shows `~` on a lifecycle that exists in both versions and changed, so the changed ones can be found without opening each. This mark belongs to lifecycle rows only.

A transition is known by the state it leaves and the state it enters. Two transitions into one state are told apart, and a transition sent elsewhere reads as one removed and one added. Every property counts, so a state whose order alone changed is marked though it looks the same; its card says what changed.

Lifecycle diagrams got a filter panel with kinds of state and Changes, the gear shift in Diff, 1-hop, on by default, and hover that lights a state, its transitions and what they reach, in One as well. The picture in One is otherwise as it was.

## [2026-11-01] — Maxitor compares two versions on use-case diagrams, and its left panel holds only what opens

Use-case diagrams now take part in Diff. Actions, roles and their links turn green, red and dashed, or amber, everything else goes grey and dim, the version button counts the changes, and the stepper walks them with a card on each, links included. The new thing is **changed inside**: a use-case diagram does not draw an action's parameters, result fields or aspects, so an action could change while looking the same. Now it is marked changed, and its card says the action is the same and lists which parts changed, before and after. What the diagram draws itself, like a role or a parent action, keeps its own mark, and an entity a field points at stays the ERD's to show.

The left panel lost everything that opened nothing. Applications holds the full graph, the ERD of all domains and a new **Use case all domains view**, with every role and every use case on one diagram. Each domain holds its ERD and use cases when it has any, and one row per entity lifecycle; a domain with nothing to draw stays in the list, dim. The Roles, Actions, Entities and Resources sections are gone, and links to a single lifecycle keep working.

Use-case diagrams got the ERD's filter panel: Domains, Changes, and a colourless Elements section for actions and roles. 1-hop is on by default and brings back whatever stands one link from what is left, so to see actions alone switch off Roles and 1-hop. Hovering an element lights it, its links and what they reach, and links are easy to hit at any zoom.

Open pull requests now stand after Live on the version track, oldest first. A pull request is work ahead of what runs, so comparing Live with it reads as progress, where it used to read as a step back. This is the one place Live can be A.

## [2026-10-31] — Maxitor's full graph is a map, and it holds graphs tens of times larger

The full graph now reads like a map. Far away you see named domains and how they connect, closer their entities and actions, closest their fields and states. Zooming only reveals things; nothing ever moves. A graph of about a hundred thousand nodes opens in under a second, because the browser reads an overview first and then only what you look at. A new version is laid out once on the server, domain by domain, so a change in one domain moves nothing in the others. The first opening of a new version takes a moment and says so; every opening after that is immediate. Running Maxitor yourself now needs Graphviz installed; the Docker image already has it.

Comparing two versions works on the map. Domains where nothing changed turn grey and dim, so the top level shows at once where to look, and switching off Unchanged takes them away. A folded domain shows its own count. The version button counts everything drawn, links as well as nodes, and a link that changed is never read as zero. Beside the button, on the ERD as well, a new control walks through the changes one by one or opens a list to pick any of them directly, and each step opens that change's card.

Filters now redraw the picture. Switch something off and the domain's outline closes around what is left and reads, say, `45 of 394 left`. Hiding something takes everything below it: a domain its entities and actions, an entity its fields. A row left with nothing on screen dims, and a small mark says what is switched off above it, with one button to bring it back. The gear shift now opens the section it paints by, on every diagram with the panel. In a room, whoever follows you sees all of it: the filters, the list as you scroll it, your pointer on the same row, the cards.

The mouse moves the map as it moves every other diagram: the wheel pans, and Ctrl or ⌘ with the wheel, or a pinch, zooms. Dragging a single node on the full graph is gone, since nothing on a map moves. A browser without WebGL says so and offers the ERD.

## [2026-10-31] — A domain switched off in the Maxitor ERD stays off

Switching a domain off in the ERD filter now does what it says. Before, with 1-hop off, tables of that domain could stay on the diagram whenever a table of another domain pointed at them, so the filter looked broken. Now they leave together with the domain. Turn 1-hop on and those neighbours come back on purpose, one line away from the tables you kept and no further.

## [2026-10-31] — Maxitor compares two versions of a service's graph, and rooms keep everyone on one picture

Switch the version picker from One to Diff and the track holds two handles: A, the older version, and B, the newer one. Drag either, or the whole stretch between them, and the ERD shows what changed from A to B — added tables green, removed ones red with a dashed frame, changed ones amber, untouched ones faded — and every field carries the same mark. The version button counts the changes on the diagram you are looking at, or says "no changes". A click on a marked table or field opens its card with every property before and after. A Changes section joins the filter panel next to Domains and Kinds, and three points at its foot choose what paints the headers. The two pull request messages stand side by side under the track, the versions between them one click away, and the address keeps both versions, so a link opens the same comparison.

Rooms became steadier for everyone working together. Someone who follows you sees the same zoom and the same top-left corner, your pointer over any panel, your clicks as ripples, the version picker as you drag it, and every change of the picture — a filter, a paint, a layout — in a single frame, with no picture in between, on every kind of diagram. Following someone who follows someone else takes the view straight from the person at the end of the chain. When two screens draw a diagram differently, the room fixes it quietly by reloading the stale side instead of switching pointers off. Diagrams no longer vanish for a follower in Safari, tooltips look the same on every screen, and a refresh reopens exactly what you saw. The [how-to page](how-to/compare-two-versions.md) walks through picking two versions and reading the painted diagram.

## [2026-10-30] — Maxitor opens a service's graph history and shows any version

Maxitor now opens the history a `repo-graph-port` serves. Paste the history's address with its read key after `#key=`, a public GitHub link to a graph file, or a running service's own address as before: Maxitor tells which it is from the answer. A version button at the left of the row above the diagram names what you are looking at and opens a picker with a time axis — every change that reached the branch, oldest at the left, the pull requests still open that would change the graph, and Live, the service running now, always last. Pick any point and every diagram shows that version's graph.

The track reads at a glance. A point's colour says how the change came: purple for a merged pull request, grey for a direct push, and for an open pull request GitHub's colour of its review — waiting, approved or asked to change; drafts are not shown. A point that starts a version is larger and carries its number underneath; a flag marks a release, either published on GitHub or tagged `release…`, which works without GitHub too. Hovering a point shows a card with its title, who made it and who merged it, its size, and what it did to the model — entities, fields and links added or removed — all read from git, so a local or corporate repository shows it as well. When the service runs exactly the newest version, the two are one point. A small "i" explains every mark.

Sharing is copying the address bar: it holds the history, the version and the key, so it opens the same view elsewhere; the key never reaches a server or a log. A room moves together to whatever version anyone picks. A long history scrolls like a page, and on a phone the picker is a sheet from the bottom. The [how-to page](how-to/open-a-graph-history.md) walks through reading the track and every refusal.

## [2026-10-30] — Graph setup remembers its decisions and requires release versions

The graph setup wizard keeps its familiar questions and now checks release versioning every time it runs. Existing working choices are shown as statuses, so a project already connected to graphs is asked about the newly required version instead of repeating its setup. Broken items come first. Every release needs an increasing version tag and checks that reject violations; you choose whether a release tool or a person creates the tags. The first tag is a separate decision, and no tag is created without your consent.

The wizard remembers settled choices in the project and still verifies them against what exists today. Optional integrations can remain deferred, but declining versioning leaves setup explicitly incomplete and brings the requirement back on the next run. Monorepositories keep their release streams separate. Before applying anything, one review shows all items, their evidence and the proposed changes, and the owner receives the exact repository settings still needed to enforce the checks. The existing service dialogue remains in place, and the version rule does not depend on the project's programming language.

## [2026-10-29] — Graph setup explains one decision at a time

Connecting a project's model maps now follows a guided conversation in your language. The wizard first tells you what it found, finishes the choices for one service before moving to another, and then explains how maps will be updated and checked. Each question says what the decision changes, why a particular option is recommended and what choosing differently means. You decide whether to connect a service before discussing where its map belongs; leaving it out removes the questions that no longer matter.

You can ask for an example, look at your choices, go back, change an answer or pause without losing unrelated decisions. An explanation request never counts as acceptance, and working settings do not need to be chosen again. Before applying anything, you see a compact account of the result with the prepared changes and their verification. If you defer automatic checks, the wizard tells you what remains manual. If an audit finds everything working, it finishes without a needless confirmation. Reviewing the skill itself does not start setup, and a failed application is reported with what actually changed rather than presented as success.

## [2026-10-29] — The setup skill talks the choices through with you, and writes the graphs from your own check run

The skill a coding agent follows to connect a project to graph files is now `aoa-graph-builder-setup` (it was `graph-builder-setup`): it sets up AOA projects first. It still finds every model in the code and every graph already saved, writes an exporter where a service has a model and nothing prints it, and proves each build before it changes anything. What changed is how it ends its survey: it tells you what it found, then asks one question at a time, each with a few options and its recommendation — where each graph file goes, how CI checks every graph, and which of your project's check runs writes the graphs. It recommends the run's last step, taken only when every other check passed, so a failing run never rewrites a graph; a project with no CI is offered a ready workflow. With every answer in, it shows one table of each graph as it is and as it will be, and writes nothing until you tell it to go on.

It also pins only what exists: until a `maxitor` release is published, CI uses a commit of this repository instead of a version that is not there yet. And it ends by reminding you to merge into the main branch, because a graph's history begins with its file on that branch. The command `graph-builder skill` prints the renamed skill; to install it, save it in a folder named `aoa-graph-builder-setup`.

## [2026-10-29] — A service's graph history, read straight from its repository

A service that keeps its graph in a file beside its code already has the graph's whole history in git: every merge that changed the file is a version. A new service, `repo-graph-port`, reads that history and serves it. Each version comes with the pull request that made it — its number, title, description and link, or the commit's message when there was none — with the repository's tags and their releases, and with the size of its graph; any version's graph comes back exactly as it was committed. A tag put on a later commit that did not change the graph belongs to the version before it, and a version whose file is not a valid graph is listed with the reason.

A private repository is read through a GitHub App you install on it, with read-only rights, and a reader opens one history with a read key: a key opens that history and nothing else, even in the same repository, and every refusal looks the same, so a stranger learns nothing about what exists. Keys are issued, listed and revoked on the server, printed once, kept only as hashes, and may expire. A public repository needs no key and no setup: a link to its graph file opens its history. GitHub tells the port about every push at once, and git — not the push's own file list — decides which graph files changed, so a push that touches no graph adds no version anywhere. Where GitHub's notifications cannot reach the server, nothing is lost: a read fetches the repository again once ten minutes have passed since the last fetch, so a merge shows within ten minutes, and a port that was down catches up on its first read. The port is the only part of Maxitor that talks to GitHub, and the App's key, its webhook secret and every token stay with it, never on disk or in a log.

Install it with `pip install "maxitor[repo-graph-port]"` and run `repo-graph-port`, or with Docker; the [how-to page](how-to/run-the-repo-graph-port.md) walks through the App, the config and the keys, and keeps each issued key in a file that never enters git. The demonstrator stand runs it at `https://repo-graph-port.aoa.run`. Maxitor's web part is now called `front`: install it with `pip install "maxitor[front]"` and start it with `maxitor` — the extra `viewer`, the command `maxitor-api` and the import `maxitor.viewer` are gone.

## [2026-10-29] — Maxitor is one package for projects in any language, and the graph's format stands apart

The format of a service's graph — the Open Gnomon Protocol — is now a standard of its own, with no code at all: a folder of JSON Schemas, one per version, and the text that explains them. Any project, in any language, can follow it; any JSON Schema validator can tell a graph from anything else. Each schema's address is the schema itself, so a validator can fetch it by name. Its versions are the ones you know, `1.0` and `1.1`, unchanged.

Everything else that was spread over two packages is now one, `maxitor`, and you choose its parts when you install it. `pip install maxitor` installs `graph-builder`, the command that keeps every service's graph in its file and checks it — and nothing else: nothing of AOA, no server, which is all a CI job needs. `pip install "maxitor[viewer]"` adds the viewer, the app that draws the graph, the entity diagrams, use cases and lifecycles; `maxitor[all]` adds everything. A command whose part is not installed says which extra to add instead of failing.

The command is now named for what it does: `graph-builder write` and `graph-builder check`, configured by `graph-builder.toml`, set up by an agent with the `graph-builder-setup` skill. It knows nothing about any language either: a service in Python, Node, Java or 1C plugs in with a command, in its own language, that prints its graph; `graph-builder` runs it, checks what it printed against the protocol's schema, keeps the file, and fails CI when the file is stale. In CI it is one step, `uses: bystrovmaxim/aoa/packages/maxitor/tools/graph_builder@maxitor-v3.0.0`, after the steps that prepare your project's environment; it needs no Python in your project, since it brings its own.

If you used the earlier packages, three things change. Install `maxitor` (with `[viewer]` for the app) instead of `aoa-maxitor` or `maxitor-gnomon`. The app's import is `maxitor.viewer` instead of `aoa.maxitor`, and the command's is `maxitor.graph_builder` instead of `maxitor_gnomon`. A repository's config is `graph-builder.toml`, whose first line is `graph_builder = "1.0"`, and its check is `graph-builder check`; the graph files themselves do not change. AOA no longer depends on any Maxitor package: it carries its own copy of the protocol's schema.

## [2026-10-28] — Each service keeps its graph in a file that every change carries

The graph of a service — the map Maxitor draws of its operations, entities and dependencies — is now kept in the repository, in one file beside the service, and that file changes in the same pull request as the code that changed the graph. Git therefore holds the graph's whole history: what the system looked like at any commit, and which change moved what. In this repository the demo and Maxitor itself do it, in `packages/aoa-demo/graph.json` and `packages/aoa-maxitor/graph.json`.

Nobody has to remember to do it by hand. The check run builds both graphs as its last step and updates their files — only when every other step passed, so no graph is written for a change that is not ready; you commit the updated file with your change. CI checks that the files are current and, if one is not, fails the pull request and says what changed, element by element: a node added, a field of an edge changed. One more commit to the same pull request fixes it. A file whose graph did not change is not touched, and the same graph always gives the same file.

The format of these files is a new package, `maxitor-gnomon`, and it knows nothing about AOA: any project whose services can print a graph by its schema can use it. It holds the schema by version — the first format, `1.0`, and the current one, `1.1`, where every edge has an id — and a published version never changes; AOA now reads its schema from there. Its command, `gnomon`, writes the files, checks them, and tells whether a document is a graph at all. Checking a graph the size of the demo's now takes a fraction of a second.

To set up another project there are three ways, described in the package's README: by hand, in four short steps; by installing a setup skill for your coding agent with `gnomon skill`; or by giving an agent one sentence with the skill's link. The skill finds every service that produces a graph, proves how to build it, asks where each file should go, and adds the check to CI — it never commits. Run again later, it audits the setup. Until the package is on PyPI, it runs straight from this repository with `uvx`. Old hand-kept snapshot folders are not carried over: the history starts with the first saved file.

## [2026-10-28] — The check run's slowest step takes half the time

The check run is shorter again: about a minute instead of a minute and a half. Its slowest step — the one that lays every diagram out in Chromium, Firefox and WebKit and checks that they agree — now takes about half a minute instead of a full one. It still checks every page in every layout mode, in all three browsers, on a phone-sized and a desktop-sized screen, and it still checks pointers and following between browsers with the same tolerances. What changed is that the parts of that step which never needed to wait for each other no longer do: both screen sizes are laid out at once, the pointer checks run beside them, and the six pairs of browsers that check following run together.

The step now says how long each of its parts took, so the next slow part is easy to spot. Two of the client's unit tests, which lay out the whole reference graph, now have room beyond the default five seconds: they check the layout's result, not its speed, and on a busy or battery-starved machine they had run out of time.

The run is now held by two chains of about the same length — the client and its layout step, and the tests of `aoa-action-machine` — so shortening only one of them would gain little. The how-to page *Running the checks* describes the layout step's parts and shows what it prints.

## [2026-10-28] — A check run that shows its time and finishes sooner

The check run that finishes every change in this repository — `bash scripts/run_checks_with_log.sh` — now takes about a minute and a half instead of nearly four. It checks exactly what it checked before, step for step; what changed is that steps which do not depend on each other now run at the same time. On the machine this was measured on, a run went from about 220 seconds to about 85.

Every step now says how long it took, both on screen and in the log, and the run ends with its total time, so a step that suddenly becomes slow is easy to spot. The log reads as it always did: every step in the same fixed order, each with its full output, and the output of two steps never mixed, whatever ran beside what. A failing step still does not stop the others — every step reports, and the run fails if any of them did.

A few things are worth knowing. Some steps still wait for others for a reason: the automatic Ruff fixes run first and alone, because they may rewrite files the other steps read, and the client is built before anything that uses it. How many steps may run at once is limited to the number of cores; `AOA_CHECK_JOBS=1` runs them one at a time, with the same log, when the machine is busy with something else. Ctrl+C now stops the whole run cleanly, browsers and servers included, and the log says the run was interrupted. The new how-to page, *Running the checks*, shows every case with what it prints.

## [2026-10-28] — Every edge of the graph has a name

The graph AOA builds from your code has always named its nodes — each entity, action or role by the qualified name of the class that declares it. Now every line between them has a name too, so two versions of a graph can be compared line by line: what appeared, what disappeared, what changed. This is the first step of graph history in Maxitor.

A line is named by where it starts, what kind of line it is and where it ends. Two cases needed more than that. An entity can hold two relations to the same entity, so a relation is named by its field; this also means that a relation which starts pointing at another table is the same relation, shown as changed rather than as one removed and another added. A lifecycle state can be entered from two different states, so a transition is also named by the state it leaves. If you add a kind of line that can repeat between the same two nodes without saying what tells the repeats apart, the graph refuses to build and names both lines, instead of quietly producing a graph whose versions can no longer be compared.

The graph file is now format 1.1: every line carries its name, and lines are listed in the order of their names, so the same code always writes the same file. Nothing changes in what Maxitor shows. Graph files written before this version have no names on their lines, and they do not need any: the names are computed from what each line already carries, by the same function the new files use, so an old file and a new one compare with each other. If your own tests check graph files against the published schema, those files now need the format 1.1 and a name on each line.

## [2026-10-28] — Rooms that show one picture

A room now shows everyone the same diagram from the first moment. When you open a room, the filters and layout you had become the room's, so the people you invite see exactly what you see; a value someone has already changed in the room is kept. Inside a room a page shows only the room's choices — your own settings never mix in — and when you leave, every page stays as it was in the room.

Following someone now means seeing what they see. The table they point at lights up for you, their tooltip opens, their selection shows, and the filter sections and panel branches they open open for you too — for their followers only, nobody else. The view no longer jumps from place to place: it glides after theirs and stops exactly where they stop. This works between Chrome, Safari and Firefox in every direction. Pointers stay on screen for as long as their person is in the room, however long the mouse stands still, and someone who arrives on a page sees them at once. The room's buttons and circles are now the size of the rest of Maxitor, circles never touch each other, and a long name no longer pushes the buttons of a person's card into each other.

Moving around changed, to work the way design tools and trackpads do. A two-finger swipe on a trackpad, or a plain mouse wheel, now moves the diagram; a pinch, or Ctrl / ⌘ with the wheel, zooms it. If you are used to zooming with the bare mouse wheel, hold Ctrl or ⌘. A swipe counts as moving yourself, so it stops following someone; zooming still does not.

The entity diagram reads more easily. Tables match the new design, with the kind icon and the name on one line, and the tables of one specialization block share one width. A field's type is the name you would write — `str | None`, or the table a relation points to — and the full spelling is in its tooltip. A table always lists all of its fields; the 1-hop switch only decides which neighbouring tables come onto the diagram. The ends of every line tell an optional relation from a mandatory one, and there are no arrows any more: the dashed line from a specialization to its head ends like any other line. The field names at the ends of a line appear only while you hover it, on a small plate that keeps clear of the tables. Hovering a table dims the others; hovering a line or a key field lights only the tables it joins, and the head of a specialization lights up together with its variants. The Kinds filter offers only the kinds that are on the diagram.

Maxitor can now show itself: typing Maxitor's own address into the service field opens its own diagram, rooms included, like any other AOA service. It tells Maxitor cheaply whether its diagram changed, and so does the demo built from this work.

Graphs from services built with this version of AOA carry the clean type names themselves; graphs from older services are cleaned the same way in the browser, so they read the same.

## [2026-10-27] — Look at one service together, on graphs that stay fresh

Maxitor now lets several people look at one AOA service at the same time. **Open room** in the row above the diagram asks for your name and gives you a link; whoever opens that link gives a name and is in. Everyone in the room sees the others' pointers on the very spot of the diagram they point at — on a phone and on a wide screen alike, whatever zoom each of them uses — and a circle for each person at the top, in a colour of their own. Filters and layout modes are shared: switch the entity diagram to another layout and everyone on that page sees it switch; someone who joins later opens the page that way. Zoom, scrolling and the left panel stay your own.

A click on someone's circle takes you to the page they are on, centred on where they point. **Follow** keeps your screen going wherever theirs goes until you move yourself, press Esc or Stop — always at your own zoom, never theirs. Two people cannot follow each other round in a circle: the second one is told why and the button stays off. **Hide pointers** quiets the others' pointers on your screen only, and **Leave room** keeps you on the page you are looking at.

A few things are worth knowing before sharing a link. The link itself is the invitation: anyone who has it can join, and nothing else is checked. Names are not verified either — people are who they say they are, and everyone in the room sees the name you give. A room holds twenty people; it ends two minutes after the last person leaves, and its link then simply opens the diagram on its own. A dropped connection is not leaving: the page reconnects by itself, and coming back within two minutes keeps your place and your colour. A tab left open over an update reloads itself once.

Pointers can land on the same spot because every diagram is now laid out identically in every browser and at every screen size. The full graph is arranged the same way everywhere, which means a graph you had opened before is arranged once more the first time you open it now.

The graphs behind the diagrams keep up with their services. A built graph is no longer dropped after an hour without readers, so the first person in the morning does not wait for a build; it stays until the store is full. While someone is looking at it, Maxitor asks the service whether its model changed — cheaply, when the service says which version it serves — and, when it did, builds the new graph in the background and switches only once the build has succeeded. A service that is down leaves everyone with the graph they already had. Open pages redraw by themselves, keeping the page, the filters, the zoom and the centre, and say *The model was updated* for a moment. **Reload** inside a room rebuilds the graph for everyone, and nobody is sent out.

Entity tables look as in the new design: the header in the domain colour with the name at its left, every second row faintly tinted, `PK` and `FK` in their own colours, the type smaller and grey, and a dashed line for a generalization. The left panel now ends with a link to the project and the version that is running.

For those who run Maxitor: rooms use a WebSocket, so a proxy in front of it must pass WebSocket connections through and keep the page's address — the nginx lines are in the Maxitor README and the tutorial step — or nobody can join. The setting for the old idle hour is gone. For those who build on AOA: the FastAPI adapter can now serve a WebSocket where every message runs an action, and every successful read it answers carries a tag, so a client that already has the content gets a short "not modified" instead of the whole answer again. ([#271](https://github.com/bystrovmaxim/aoa/issues/271))

## [2026-10-27] — Entity kinds travel with the graph, and the ERD shows every line

A graph now says what kinds of entity it holds and what each kind is called. Every kind base names its kind for people — AOA's six are Core, Association, Detail, Specialization, Enumeration and State — and the export writes that name next to the kind word on every entity. A model may add a kind of its own, and a graph from another tool may bring words AOA has never heard of: Maxitor keeps no list of its own and shows whatever the graph says. A kind that arrives without a name is called by its word with a capital letter; an entity that states no kind at all still opens, listed as unknown, so an older graph does not break.

One thing is now required. A kind base of your own must declare its name in its own body as `KIND_LABEL`, a non-empty string; without it the class is refused the moment Python creates it. Ordinary entities declare nothing new — they take the name of their kind.

The ERD has one filter panel instead of the domain legend. Its two sections, Domains and Kinds, fold like an accordion, one open at a time, and each row hides or shows its tables. Kinds appears when a graph has more than one kind; its disks are grey, because colour on this diagram still means the domain. The panel keeps the width the legend had, and a name that does not fit is cut with an ellipsis and shown whole on hover. Each table's header now carries its kind's white icon beside the name, and short tables are no longer drawn as narrow stubs.

Every line between two tables on screen is now drawn, whatever brought each table there — its own domain, a one-hop neighbour, or a second domain shown in the same view. Before, a line could go missing when its two ends were neighbours, or came from two different domains. A relation and its declared inverse are one line, not two, and each end is drawn the way an ERD reader expects: a bar for one, a crow's foot for many, and the name of the field on that side. A specialization head is joined to the dictionary its variants are chosen by, and the specialization frame is a shade darker, with a slightly thicker border.

Reading the diagram is easier too. Hovering a line thickens it and marks in bold the fields at both its ends; hovering a field marks every line it belongs to. Clicking a table or field name copies it, with a short note to say so; dragging the canvas never copies. Hovering a table now works on the live page as well; there it never did before.

Two things look different to anyone who reads the cards closely. A relation field's type is now just the name of the table it points to, without the `FK -> ` in front, and a dictionary field no longer has an arrow and the dictionary's name after its type — the line says it. And the eighth domain colour, which was grey, is now orange: grey is left to entity kinds, so no domain is drawn in it. ([#239](https://github.com/bystrovmaxim/aoa/issues/239))

## [2026-10-26] — A full graph that opens several times faster

The full-graph page used to send everything it had on every visit — 3.06 MB of code, styles and graph data — and kept nothing. It now sends 1.23 MB on the first visit and about 22 KB on the next. On a slow mobile network the first picture appears in about 7.4 seconds instead of 16.5, and the code and the styles are downloaded once and then come from the browser's own cache.

A new release still reaches a returning reader on their next visit. The page itself is always revalidated, so a changed release arrives whole and points at the new files, while the files whose names carry a content hash stay in the cache for a year.

The page also remembers where it put every node of a graph. Opening the same graph again draws it from those positions without working out an arrangement at all; a changed graph, changed layout settings, a private window or a full cache simply means the graph is arranged afresh. At most twenty graphs are remembered, the least recently used dropped first.

One thing that worked no longer does: a node cannot be dragged. Everything else about the picture is unchanged — the same nodes and edges, colours, glyphs, hover cards and domain hulls, the same panning and zooming — but a drag that starts on a node leaves the picture where it was.

The tab still freezes while the graph is drawn. Moving the arrangement off the main thread was built and measured: it did not shorten the freeze at all, and it made the first picture about a third of a second later, so it was not shipped. What is left of that work is the small piece that replays a remembered arrangement. ([#245](https://github.com/bystrovmaxim/aoa/issues/245))

## [2026-10-26] — A graph takes a fraction of the memory

Maxitor used to spend four fifths of a built graph's memory on lookup structures: every node table carried a primary key and every edge table two indexes. The diagram queries never read through them — every plan was already a full scan — so the graph paid tens of megabytes for nothing. The build now creates neither.

The difference is visible in the number an operator watches. A graph of the reference service takes about 13 MiB instead of 43.5, and the demo's graph about 20 instead of 65. In the process, each held graph costs about 24.5 MiB instead of 53.4 on macOS and 16.7 MiB on Linux, so a store holding the full fifty graphs fits in roughly 1.1 GiB instead of 2.7. The build is also a little faster. Nothing a reader sees changes: every diagram and the sidebar answer exactly as before, at the same speed.

A service whose graph lists the same node id twice in one table is still refused, and the message now names the duplicated id and its table instead of quoting the database. A repeated id in two different node tables remains accepted, as it always was.

The stand runs Linux, and there the memory comes back to the system when graphs are dropped: the process fell from about 309 MiB with ten graphs to about 192 MiB after all were dropped, and rebuilding three added only a few megabytes. On macOS the process keeps its peak, as before. Changing DuckDB's allocator settings lowers the Linux peak somewhat but does not change that answer. ([#268](https://github.com/bystrovmaxim/aoa/issues/268))

## [2026-10-26] — One graph per source, and every request names it

Maxitor used to keep a single graph per process. Whoever opened a service last owned it, so the next diagram drawn for anybody else silently showed that other service's graph; and because there was only one place to keep a graph, every open downloaded and rebuilt the whole thing again.

Each open now names the service it belongs to, and the process keeps one graph per service. Two people on two services no longer overwrite each other, and a service that is already built opens without downloading anything. A deep link works exactly as before — same address, same view, one step — and if the service is not built yet it is built by that first open. Opening a link never forces a rebuild, so a shared link stays cheap for everyone who follows it.

Getting a fresh graph on purpose is now a button: **"Reload from service"**, next to the open source, rebuilds only that service and keeps the diagram and the address where they are. Leaving the source and entering its address again still works as it always did, and a failed reload keeps the diagram already on screen and says what went wrong.

The process keeps its memory bounded without asking anyone to manage it. A graph that nobody has read for an hour is removed, and the next click rebuilds it in one slower step, with no error and no prompt; at most fifty graphs are held and at most four are built at once; the hour and both limits are settings. When the server is busy, the page says so and tries again by itself — being busy is never reported as a broken service.

Saved links, the address format and the way a service is opened are unchanged. ([#214](https://github.com/bystrovmaxim/aoa/issues/214))

## [2026-10-25] — A JWT request carries its login session

An authenticated JWT request now identifies two things: who is calling and which login session the call belongs to. The context gains a session id next to the user id, so audit records and access rules can tell two logins of the same user apart. An aspect or an `@access_decide` rule reads it like any other context field, without decoding the token again.

The session claim is required. Every `JwtAuthCoordinator` and `JwtAuthenticator` names it with `session_id_claim` — there is no default and no way to switch it off — and every token issuer must put that claim into its tokens, server-to-server tokens included. One login gets one session id, and a refreshed token keeps it. AOA only carries the value: it stores no sessions and has no logout, so ending a session is a rule the application writes.

The user id and the session id follow one strict rule. A token that fails verification — bad signature, expired, wrong audience or issuer — is still an ordinary refusal. A verified token whose user id or session id is missing, empty, blank or not a string now raises `AuthenticationContractError`, which names the claim and the reason but never its value; over FastAPI the caller gets a server error rather than a 403. Some tokens that used to be refused quietly now raise as well: a missing or numeric `sub` is one of them. A blank `sub` is no longer accepted, and a number in a custom user-id claim is no longer turned into text.

To migrate, add `session_id_claim="sid"` (or your issuer's claim name) to every constructor, make the issuer emit that claim, and emit `sub` as a string. The JWT guide walks through the new rules with runnable examples. ([#263](https://github.com/bystrovmaxim/aoa/issues/263))

## [2026-10-25] — A dictionary is an ordinary card, and its values stay in the graph

A dictionary used to be drawn as a table of everything it accepts: one line per value, with the value's
descriptive fields under it. That reads well for three currencies and badly for a world map — a region
catalogue of ninety-three entries turned one domain's diagram into a column seven screens tall, with the
entities it belongs to pushed out of sight. The dictionary is now an ordinary card: its name, the fields
it declares, and the arrows that point at it. Nothing stands in for the values — no count, no badge, no
hint that the card is a dictionary.

The values did not go anywhere. A graph export still carries every one of them with its code, its label
and its descriptive fields, and the entity endpoint still answers the same typed list it answered before.
Anything that needs to know what a dictionary accepts reads it there; only the picture stopped repeating
it, and a saved graph needs no rebuild to look right.

The rule behind the card is worth knowing when you meet one: two dictionaries that differ only in size
now draw the same card, so a diagram's height says something about its entities and nothing about how
many values its catalogues hold. ([#265](https://github.com/bystrovmaxim/aoa/issues/265))

## [2026-10-25] — Role requirements and object rules have separate jobs

A role declaration now says only who may call an operation. Keep bare roles in `@check_roles`: one role, several alternatives, a guest requirement or an active-role requirement. Replace unconditional `grant(Role)` wrappers with `Role`; the old grant imports and condition keywords are no longer supported.

Move caller, input and object conditions into the operation's optional `@access_decide` method. Related conditions form branches of one rule, and each refusing branch can keep its own reason. Declare the context fields the rule needs. Review role-specific alternatives when combining them so that one caller's condition does not accidentally admit another caller.

Refusals now name one of three steps: authentication, roles or the object rule. The old `WHEN` and `GUARD` values are removed; handle migrated conditions as `ACCESS_DECIDE` and use their reasons to distinguish policies. A guest alternative beside other roles opens the role requirement, while an any-role alternative accepts any active role. Remove such an alternative if that wider admission is not intended.

A migrated condition runs after connection preparation, inside execution. It can stop business work, but cannot prevent that preparation from starting. Guest operations remain open without an object rule; adding one can still refuse the same caller. The updated guide and executed lessons show both outcomes and the migration failures. ([#248](https://github.com/bystrovmaxim/aoa/issues/248))

## [2026-10-25] — Compatible endpoint roles and dictionary collections

A reciprocal relationship now checks what each endpoint means. Two associations may pair; an aggregation or composition needs an association on the opposite side. Specialization and generalization pair only with each other. One/Many changes cardinality, not compatibility. Previously accepted ownership/ownership pairs must migrate: keep ownership on the appropriate side and declare its reverse as an association. Refusals identify both fields, their roles and the correction before the model's graph is published.

An ordinary NoInverse field remains an independent one-way link. Two such fields pointing at each other's types are two links, not a reciprocal pair. An Inverse cannot use a NoInverse field as its reverse. Specialization and generalization now refuse NoInverse and require reciprocal markers, closing the earlier missing-direction check.

Dictionary targets support association, aggregation and composition with both One and Many. Use an explicit wrapper in Python. JSON selection input remains one id object for One and is an array of id objects for Many; export contains the canonical member reference or an array of references. Validation keeps the container class, resolves codes in order and leaves the caller's wrapper unchanged. Empty collections and absent nullable values remain distinct, and graph metadata retains the declared family and cardinality.

The documentation and executed scenarios cover permitted pairs, migrations, refusals and independent directions. Verification also records remaining gaps in custom container subclasses, reciprocal catalogue declarations, typed custom-property export schemas and duplicated dictionary field rows in ERD payloads. These require code corrections and are not alternative supported declarations; see the [verification report](reports/endpoint-role-verification.md). ([#261](https://github.com/bystrovmaxim/aoa/issues/261))

## [2026-10-24] — Complete relationship declarations and explicit dictionary selections

> The dictionary rules in this entry — one association, no inverse, no many or ownership containers — were superseded by the endpoint role compatibility entry above.

Relationships now state their container, direction and description together. Core, association, detail and specialization objects use the complete declaration for their links; selecting a dictionary value uses an explicit single association. Replace bare entity fields and the former embedded-value marker with complete relationships. Raw collections of entity values do not replace relationship declarations. State retains its lifecycle contract.

Ordinary reciprocal links now name each other on both endpoints. Migrate old one-sided inverse declarations by adding the matching marker to the other side, or declare a genuinely unpaired link with `NoInverse()`. Separate declaration modules can use field-only inverse markers and resolve their postponed annotations after both modules are imported.

For a dictionary selection, replace the bare dictionary field with `Annotated[AssociationOne[D], NoInverse()] = Field(description="...")`. Pass an explicit wrapper with its code as `id` in Python, or an id-only object in JSON. Validation selects the shared declared member. Export still returns its code, display name and descriptive properties, so selection input and exported references have different shapes. Many-value containers, ownership containers and inverse markers on dictionary selections are refused.

Rebuild model exports after migrating. At that checkpoint, verification identified gaps in explicit inherited overrides and specialization direction checks, a broad schema for exported association properties, and duplicate dictionary field rows in the entity diagram payload. The later endpoint-role change closes the NoInverse specialization-direction gap. These are documented limitations requiring code corrections, not supported alternatives to the complete form. See the [verification report](reports/complete-relationship-verification.md). ([#259](https://github.com/bystrovmaxim/aoa/issues/259))

## [2026-10-23] — Dictionary selections become visible references

This entry describes the earlier bare-field declaration. The complete association form above supersedes that declaration and its migration advice.

A field selecting a dictionary value now connects the owning object to its dictionary in the model and entity diagram. The existing field and its type hint remain available. Optional selections have the same connection and may hold no value.

Keep existing bare dictionary annotations. Rebuild older graph exports to show their connections. Multiple selections need a separate link object: collections of dictionary values are refused. Relationship containers and embedded-value markers must be replaced by the bare dictionary type.

A reference also requires a nonempty dictionary included in the model. Refusals identify the field and explain the supported declaration. Structural unions, mixed collections and mappings keep their refusals with more precise guidance.

([#256](https://github.com/bystrovmaxim/aoa/issues/256))

## [2026-10-23] — A completed value must be the declared type

A dictionary property now compares the exact type of the value a custom validator returns, not merely that the value belongs to that type in Python's class hierarchy. A `datetime` no longer passes for a `date`, and any subclass of a declared property type is refused, because the exported schema describes the declared type rather than its subclasses. The rule that already refused `bool` for `int` and an integer for a `float` is now the stated rule instead of a side effect of the comparison.

Input is unchanged: a declaration that gives `1` to a `float` property still stores `1.0` before the completed-value check, because Pydantic coerces ordinary input first. A validator that computes a value must return the declared type. The migration table in the dictionary guide lists each refused pair with its accepted neighbour.

([#254](https://github.com/bystrovmaxim/aoa/issues/254))

## [2026-10-23] — Dictionary values keep their declared choices

A shared dictionary value now keeps the choices and types its declaration promises, even after custom validation. A validator cannot publish an unlisted choice or an absent value where one is required. Booleans and integers remain distinct, including choices that Python would otherwise compare as equal.

Existing validators must return a permitted value of the declared type. If absence is part of the vocabulary, declare it alongside the other permitted values or types. A property declared to contain only absence is refused. The same checks apply to tuple items, and refusal messages identify the member, property and failing item.

This resolves the previously reported gaps in checking completed dictionary members. Reference payloads and their schema modes keep their existing form. Four learning scenarios group the refusals with their accepted neighbors: literal choices, union nullability, tuple items and property declarations. Each has one executable script and one notebook that presents the related cases in order.

([#252](https://github.com/bystrovmaxim/aoa/issues/252))

## [2026-10-23] — Entity fields declare their meaning

A field containing another entity now states whether it is a relationship or an embedded value. Ambiguous declarations are refused when the model is assembled, with guidance on the supported forms. Relationship descriptions are field metadata; a relationship value comes from the caller. Existing declarations must move descriptions into field metadata and explicitly choose whether a nullable relationship may be omitted.

A specialization alternative now names only its dictionary value, without repeating the name of the field carrying the declaration. Dictionary values are checked again after custom validation, so a validator cannot publish a list in place of a tuple. Export schemas retain the definitions used by enum properties and require the properties actually written, including null values. At the time of this entry, literal membership and null returned for a non-nullable union remained unchecked. The later entry above records their correction.

Dictionary cards show human labels and descriptive properties. Codes remain available in tooltips, and the inherited identity fields no longer occupy ordinary field rows. The declaration, refusal and export examples are available as executable scripts and notebooks.

([#249](https://github.com/bystrovmaxim/aoa/issues/249))

## [2026-10-23] — Explicit values and consistent references

Dictionaries and lifecycle statuses now declare their members with `value(...)`, keeping
existing codes and lookups. Dictionaries reject mutable property types at declaration;
reference exports apply the declared formatting and carry JSON-compatible descriptions.
Input schemas allow a code-only reference, while output schemas describe the returned
properties. Maxitor preserves those descriptions in dictionary cards and displays each
specialization group's dictionary name once. Existing declarations need the new factory
import and call. ([#244](https://github.com/bystrovmaxim/aoa/issues/244))

## [2026-10-22] — Closed dictionaries and consistent variant choices

A dictionary now declares the complete set of values the model accepts. References keep
the chosen value together with its name and descriptive fields, while unknown or fabricated
values are refused. Specializations use the same vocabulary: every value has one alternative,
and loaded details must match the choice. The separate selector and duplicated code lists
are replaced by one dictionary declaration. Maxitor shows the values inside the dictionary
card, identifies references to it and labels each specialization group with its dictionary.
([#241](https://github.com/bystrovmaxim/aoa/issues/241))

## [2026-10-22] — A lifecycle status belongs to its type

A status used to be declared on the lifecycle axis, with a separate `StateVocabulary`
mixin collecting the status attributes next to it. The status and its catalogue were
two different objects, and a typo in a template was refused late.

Now the state type declares its own statuses in its own body and carries their catalogue:
`members`, `codes()`, `by_code()` and `entity_type` are on the type. The axis names the
type with `Lifecycle[OrderStateEntity]` and keeps only the transition template. Every
status is a typed instance, so a misspelled field is caught where the status is written.
A status from another type, an equal but different instance, and a declared status that
does not appear in the template are refused at class definition, with the type and the
allowed codes named. A status used only as a transition target is still missing.

The declaration surface is the type's own name: inside the body it resolves to the
declaration factory, and it shadows a same-named global. A narrowed axis declares the
narrowed type; a subtype without statuses inherits the catalogue. `members`, `by_code()`
and the other lookups have moved from the axis to the type; `StateVocabulary` and
axis-level status attributes are gone. To migrate, move the status assignments into the
state type, write `Lifecycle[StateType]`, and replace axis lookups with the type. The
demo's 32 axes and the example and test corpus are on the new form; the mixed, empty and
mixin examples were removed because those situations no longer exist.
([#237](https://github.com/bystrovmaxim/aoa/issues/237))

## [2026-10-22] — The model distinguishes what each entity represents

An entity now declares its role: an independent object, a technical connection,
an owned part, variant-specific data, a reference value or a lifecycle state.
Its base class and name must agree. Technical connections contain no business
data; a supplier offer with price and terms is a core object. The graph carries
these distinctions through to Maxitor. To migrate, choose each entity's kind,
update its name and regenerate saved graphs. The documentation explains each
choice with a separate runnable example.
([#210](https://github.com/bystrovmaxim/aoa/issues/210))

## [2026-10-21] — A lifecycle state is an object, and the diagram shows it

A lifecycle state used to be two strings, a key and a label: `.state("paid", "Paid")`. The label
was stored in the template and never left it, so the graph kept the key as the label and Maxitor
drew `paid`; a status had nowhere to keep anything of its own.

A state is now an object with a stable `code`, a human `display_name` and any fields the status
needs. One axis is one class: the statuses are class attributes and the transitions are declared in
the same body, with `StateVocabulary` next to `Lifecycle`:

```python
class OrderStateEntity(BaseStateEntity):
    sort_order: int = Field(default=0, description="Presentation order")
    color: str = Field(default="#9e9e9e", description="Diagram colour")


class OrderLifecycle(Lifecycle, StateVocabulary):
    DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=1)
    PAID = OrderStateEntity(code="paid", display_name="Paid", sort_order=2)

    _template = (
        Lifecycle()
        .state(DRAFT).to(PAID).initial()
        .state(PAID).final()
    )
```

The diagram now shows the label, orders the states as declared (`sort_order`) and uses the declared
colour. The graph state row carries every declared field as attributes; the diagram's own data
carries the presentation fields it draws — `code`, `display_name`, `sort_order`, `color`,
`fill_color` — and the rest stays in the graph, where other consumers read it.

An entity with several status axes has several such classes, one per lifecycle field. The identity
inside the machine is still the `code`, so stored rows, events, graph ids and transitions do not
change.

**Breaking change.** The string form is gone: `.state("paid", "Paid")` and `.to("shipped")` now
raise an error at declaration and name what arrived. The runtime is not affected:
`OrderLifecycle("paid")` and `transition("paid")` still take the code, and `current_state` is still
that code. The instance also offers `current_status` — the declared status object itself, with its
fields.

The demo's 32 declarations were migrated with their codes and transition pairs unchanged.

## [2026-10-19] — A role's mode is checked where it is written

A role declares its lifecycle mode once, with `@role_mode`, and the four members it may carry
are `ALIVE`, `DEPRECATED`, `SILENCED` and `UNUSED`. Until now the decorator accepted anything and
wrote it down: `@role_mode("alive")` — the string the enum carries — was stored as a string, and
the first reader refused it with a message that named the value and not one thing that would
have worked. A role nobody read was never refused at all.

Now the argument is checked at the declaration, while the module is imported. The refusal names
the role, the value that arrived and all four members, so it can be fixed from the message alone:

```
@role_mode(ViewerRole): expected a RoleMode member, got 'alive'. Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
```

`@role_mode` written without parentheses is refused too. It used to bind the class name to the
decorator's inner function and fail much later as `TypeError: issubclass() arg 1 must be a class`;
now it says that the parentheses are missing, and names the class it received.

Nothing about what the four modes mean has moved. `UNUSED` still cannot be required through
`@check_roles`, `DEPRECATED` still warns, `SILENCED` still grants nothing — those rules belong to
the consumers, and a valid member is not a member that is apt in every context. A role that
carries no mode at all is still refused when something reads it.

[The reference page](reference/intents-and-invariants.md) states the invariant, and
[`examples/step_03_authorization_and_roles/17_a_wrong_role_mode.py`](../examples/step_03_authorization_and_roles/17_a_wrong_role_mode.py)
runs each refusal — script and notebook — so the cases can be read and executed side by side.

## [2026-10-18] — A declaration says what it receives

The four methods the machine calls itself — the regular step, the exit point, the error handler
and the rollback — now declare their signature the way the machine calls them: `params`, `state`,
`box`, `connections`, in that order, then `error` for a handler, then a trailing `ctx` only when
the context was asked for. Rename one of them and the class no longer builds; the refusal names
the order the pipeline uses and the order that was written, and says why the order is fixed —
the values are passed by position, so a renamed parameter would quietly receive something else.

Every one of those parameters now carries a type, and so does the answer. The shape is checked
where the method is written; the types are checked when the operation is assembled, because
`params` is the operation's own `Params` and does not exist before then. A regular step returns
the state fragment, a rollback returns nothing, and the exit point returns the operation's
`Result` — or a supertype of it, so `BaseResult` is fine and `Any` is not.

An operation answers once. Two exit points are now refused as what they are, naming both methods;
before this change the second one surfaced as a graph error about a node that was never written.
And the answer itself is compared with the declared `Result` twice: the annotation when the
operation is assembled, and the returned value when the operation runs, so a method that promises
one thing and returns another is caught rather than handed back to the caller as the operation's
result.

The three errors are new names in the public exception namespace: `AspectSignatureError` for the
signature, `DuplicateSummaryAspectError` for a second exit point, and `ActionResultTypeError` —
which existed, was exported and had never been raised — for an answer that is not the operation's
`Result`.

Every example, notebook and page in this repository was migrated to the contract, because a
framework cannot ship declarations its own rules refuse. The
[reference page](reference/intents-and-invariants.md) states the contract, and
[`examples/step_01_Action_and_pipeline/05_aspect_declarations.py`](../examples/step_01_Action_and_pipeline/05_aspect_declarations.py)
runs each refusal — script and notebook — so the cases can be read and executed side by side.

## [2026-10-08] — Access lives in the declaration

An operation can now state who may call it, which restrictions apply to every call, and what
must be true of the particular object. A manager can have permission to cancel orders while
still being limited to their own orders. The checks run in order, and a refusal stops the
operation before its business steps begin.

There are three distinct outcomes: allowed, refused, and unable to decide. A refusal identifies
the check that rejected the call and can carry an explanation chosen by the application. If the
order store is unavailable, the answer is unable to decide: a technical failure is neither a
permission nor a policy refusal. Details of the failure remain available on the server and are
not included in the answer sent to the client. A foreign order and a missing order can share the
same refusal so that the answer does not disclose which orders exist.

Applications can ask about access before offering an operation to a user. This evaluates the
access rules without performing the operation or using its result cache. It still reads the data
needed by the checks, and the answer applies to that moment: execution checks access again.
Authentication happens before these rules, so making an operation public does not override a
service's requirement for valid credentials.

Object checks are explicit declarations. Each operation owns its check, and a check that needs
information about the caller declares which fields it reads. Plugins can observe checks starting
and finishing, and identify a check that failed, without receiving its decision or the failure's
message. Applications using the previous object-check method or batch access query need to move
to the new declaration and ask about one call at a time.

The [authorization tutorial](tutorials/step-03-authorization-and-roles.md) now walks through these
rules with separate, runnable examples. Each shows one capability, its actual result, and why
that result follows. Scripts and notebooks cover the same scenarios; declaration mistakes are
kept in a separate section so that a working rule can be learned before its error cases.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Conventions.** Release headings use `## [version] – YYYY-MM-DD` (en dash). Use `### Breaking changes`, `### Added`, `### Changed`, `### Fixed`, `### Removed`, and `### Documentation` as needed. Each bullet starts with a **bold title** followed by a period and the body.

## [Unreleased]

### Breaking changes

- **`aoa-examples` package renamed to `aoa-demo`; import namespace `aoa.examples` → `aoa.demo`.** The library of reference/demo domain models and the FastAPI + MCP showcase services previously distributed as `aoa-examples` (imported as `aoa.examples`) is now `aoa-demo` / `aoa.demo`. Install `aoa-demo` and update imports: `from aoa.examples.model… ` → `from aoa.demo.model…`. The rename eliminates the collision with the root `examples/` tutorial scripts (the documentation examples) and clarifies that the package is a runnable demo-domain library, not tutorial snippets. The undeclared `aoa-maxitor` → demo coupling was removed in the same change: `maxitor` no longer references `demo` in any form. ([#83](https://github.com/bystrovmaxim/aoa/issues/83) · [aoa-demo CHANGELOG](../packages/aoa-demo/CHANGELOG.md))
- **`NoAuthCoordinator` now requires an explicit `context` argument.** `NoAuthCoordinator()` is no longer valid; pass the `Context` explicitly: `NoAuthCoordinator(context=Context())`. The change makes the context visible at the call site instead of hiding an implicit anonymous default. Semantically `process()` now returns the **same** `Context` instance on every call (was: a new instance each time). Any code that relied on identity (`ctx1 is not ctx2`) must be updated. The class is otherwise compatible — it still satisfies the `AuthCoordinator` protocol and can be swapped with a real coordinator without touching the `Action`. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`AuthCoordinator` now raises `AuthorizationError` when `process()` returns `None`.** Previously `FastApiAdapter` and `McpAdapter` silently fell back to a plain anonymous `Context()` when the coordinator returned `None` (unauthenticated request). This masked auth failures: operations decorated with `@check_roles(GuestRole)` would succeed for any unrecognised credential. Now `None` from `process()` immediately raises `AuthorizationError("Authentication required")`, which the adapters convert to HTTP 403 / MCP `PERMISSION_DENIED` envelope. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`FastApiAdapter` and `McpAdapter` extracted into separate packages; old import paths removed.** `aoa.action_machine.adapters.fastapi` and `aoa.action_machine.adapters.mcp` no longer exist. The `[fastapi]` and `[mcp]` extras on `aoa-action-machine` are also removed. Install the new dedicated packages and update all imports: `pip install aoa-fastapi-adapter` → `from aoa.fastapi import FastApiAdapter`; `pip install aoa-mcp-adapter` → `from aoa.mcp import McpAdapter`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63) · [aoa-fastapi-adapter CHANGELOG](../packages/aoa-fastapi-adapter/CHANGELOG.md) · [aoa-mcp-adapter CHANGELOG](../packages/aoa-mcp-adapter/CHANGELOG.md))
- **OCEL plugin extracted into a separate package; old import paths removed.** `aoa.action_machine.plugin.ocel` no longer exists. The `[ocel]` extra on `aoa-action-machine` is removed. Install the new package and update all imports: `pip install aoa-ocel` → `from aoa.ocel import OcelPlugin, OcelFrame, InMemoryOcelStoreResource, OCEL_FRAMES_KEY`. ([#71](https://github.com/bystrovmaxim/aoa/issues/71) · [aoa-ocel CHANGELOG](../packages/aoa-ocel/CHANGELOG.md))
- **OpenTelemetry plugin extracted into a separate package; old import paths removed.** `aoa.action_machine.plugin.open_telemetry` no longer exists. The `[otel]` extra on `aoa-action-machine` is removed. Install the new package and update all imports: `pip install aoa-otel` → `from aoa.otel import OpenTelemetryPlugin`. ([#70](https://github.com/bystrovmaxim/aoa/issues/70) · [aoa-otel CHANGELOG](../packages/aoa-otel/CHANGELOG.md))
- **`@compensate` now accepts a callable reference instead of a string.** `@compensate("aspect_name", description)` is no longer valid; pass the method object directly: `@compensate(aspect_name, description)`. The target aspect must be defined before the compensator in the class body — the reference is resolved at class definition time, enabling IDE rename support and eliminating stringly-typed coupling. Internally, `_compensate_meta["target_aspect"]` now stores the callable (was: `"target_aspect_name"` string); `CompensatorGraphNode.target_aspect` carries the callable directly; `ActionGraphNode.compensator_graph_node_for_aspect` accepts a callable and matches by identity (`is`). ([#64](https://github.com/bystrovmaxim/aoa/issues/64))

### Added

- **`Connections`: a public name for the mapping every aspect receives.** `from aoa.action_machine.resources import Connections` says `dict[str, BaseResource]` once instead of in every declaration. The alias is an ordinary assignment, so the validator reads the same `__origin__`/`__args__` as before, both spellings stay interchangeable, and the value an aspect receives is unchanged.

- **`aoa-otel` package: OpenTelemetry plugin as a standalone distribution.** A new separate package `aoa-otel` (`pip install aoa-otel`) provides `OpenTelemetryPlugin` under the `aoa.otel` namespace. The package depends on `aoa-action-machine`, `opentelemetry-api`, and `opentelemetry-sdk`. ([#70](https://github.com/bystrovmaxim/aoa/issues/70) · [aoa-otel CHANGELOG](../packages/aoa-otel/CHANGELOG.md))

- **`@env` decorator for declarative environment providers on `Context`.** `@env(key, value_or_callable, ttl=0)` registers a lazy provider on a `Context` subclass. Constants are auto-wrapped; any `Callable[[], T]` is accepted as-is. `ttl=0` caches the value forever; `ttl>0` re-calls the provider after N seconds; `ttl<0` raises `ValueError` at declaration. Subclasses inherit all parent entries and can override individual keys without touching the parent dict. Aspects declare needed keys via `@context_requires("env.<key>")` and read them through `ctx.get(...)` — the same path as `user.*`, `request.*`, and `runtime.*` fields. An undeclared key raises `ContextAccessError`; a key registered in `@env` but absent from `@context_requires` is simply inaccessible, not missing. ([#60](https://github.com/bystrovmaxim/aoa/issues/60))
- **`TestBench.with_env(key, value, ttl=0)` for env constants in tests.** Registers a constant (not a callable) as the env value for `key` on the bench-built context. Successive calls merge by key; the last call for the same key wins. `TestBench` is immutable — each `.with_env(...)` returns a new object. Under the hood a dynamic `Context` subclass is created with `__env_entries__` set so the action receives the same interface it would with a production `AppContext`. ([#60](https://github.com/bystrovmaxim/aoa/issues/60))
- **`context_class` parameter on `AuthCoordinator` for custom `Context` subclasses with `@env`.** `AuthCoordinator(..., context_class=AppContext)` makes `process()` instantiate your `Context` subclass instead of the base `Context`. This is the only way to get `@env`-decorated entries into the context when using real authentication (not `NoAuthCoordinator`): `@env` entries live on the class, not on the instance, so passing `context_class=AppContext` is sufficient — `AppContext(user=..., request=...)` works without any constructor changes. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`aoa-fastapi-adapter` package: `FastApiAdapter` as a standalone distribution.** A new separate package `aoa-fastapi-adapter` (`pip install aoa-fastapi-adapter`) provides `FastApiAdapter`, `FastApiRouteRecord`, and the `query_field_before` helpers under the `aoa.fastapi` namespace. The package depends on `aoa-action-machine`, `fastapi`, and `uvicorn[standard]`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63) · [aoa-fastapi-adapter CHANGELOG](../packages/aoa-fastapi-adapter/CHANGELOG.md))
- **`aoa-mcp-adapter` package: `McpAdapter` as a standalone distribution.** A new separate package `aoa-mcp-adapter` (`pip install aoa-mcp-adapter`) provides `McpAdapter` and `McpRouteRecord` under the `aoa.mcp` namespace. The package depends on `aoa-action-machine` and `mcp`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63) · [aoa-mcp-adapter CHANGELOG](../packages/aoa-mcp-adapter/CHANGELOG.md))
- **`aoa-ocel` package: OCEL 2.0 export plugin as a standalone distribution.** A new separate package `aoa-ocel` (`pip install aoa-ocel`) provides `OcelPlugin`, `OcelFrame`, `InMemoryOcelStoreResource`, `OcelStoreResource`, `OCEL_FRAMES_KEY`, and supporting DTOs under the `aoa.ocel` namespace. The package depends on `aoa-action-machine` and `xxhash`. ([#71](https://github.com/bystrovmaxim/aoa/issues/71) · [aoa-ocel CHANGELOG](../packages/aoa-ocel/CHANGELOG.md))
- **`aoa-langgraph` package: `LangGraphAdapter` for using AOA Actions as LangGraph nodes.** A new separate package `aoa-langgraph` (`pip install "aoa-langgraph"`) provides a fluent builder that registers AOA Actions (and plain async functions) as LangGraph nodes and compiles a standard `CompiledGraph`. `.node()` accepts an Action instance or any `async` function (`name=` required for functions). `.edge()`, `.conditional_edge()`, `.route()`, and `.start()` accept an Action class, instance, or string. An unregistered node reference in any of these methods raises `UnregisteredNodeError` immediately — topology errors surface at build time. A missing `@connection` key is caught at `.compile()` via `MissingConnectionError`. The connection pool is filtered per node by declared `@connection` keys automatically. `Params` fields are extracted from `agentstate` by name (strict). The result is merged back via `result.model_dump()`. `.build_graph()` returns an uncompiled `StateGraph` for native LangGraph continuation. ([#62](https://github.com/bystrovmaxim/aoa/issues/62) · [aoa-langgraph CHANGELOG](../packages/aoa-langgraph/CHANGELOG.md))
- **`params_mapper` and `response_mapper` on `LangGraphAdapter.node()`.** Two optional keyword arguments on `.node()` cover the case where `agentstate` field names differ from `Action.Params` / `Action.Result` field names. `params_mapper(agentstate: dict) -> Params` replaces automatic field extraction by name; `response_mapper(result: Result) -> dict | BaseModel` replaces `result.model_dump()` — if it returns a Pydantic model, `.model_dump()` is called automatically. Both mappers apply only to Action nodes; plain async function nodes manage their own input and output. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`StateFieldMismatchError` raised at `.compile()` when Action Result fields are absent from AgentState.** `_validate()` now checks that every field of each Action's `Result` type (resolved via `ActionSchemaIntentResolver.resolve_result_type`) is declared in `AgentState.model_fields`. Missing fields would silently disappear on merge at runtime — the error surfaces them at build time. The check is skipped when `response_mapper` is provided (the mapper controls what enters the state) and when `agentstate` is not an `AgentState` subclass. Error carries `action_name`, `missing_fields`, and `state_class` attributes for programmatic inspection. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`RouteKeyError` raised when `.route()` on() returns a key absent from paths.** Previously a bare `KeyError` was raised from the dict lookup with no context. Now `RouteKeyError` carries the source node name, the unexpected key, and a sorted list of available path keys — making routing coverage errors immediately actionable. The error is raised at `ainvoke()` time because the key value comes from the live graph state and cannot be validated at `.compile()`. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`AgentState(BaseSchema)` — base class for LangGraph agentstate schemas.** Exported from `aoa.langgraph` alongside `LangGraphAdapter`. Inherits `BaseSchema` (dict-like `__getitem__`/`__contains__`, `populate_by_name`, `arbitrary_types_allowed`); sets `frozen=False, extra="ignore"` appropriate for LangGraph state that is recreated from a merged dict after each node. Pydantic field defaults eliminate the need to pass placeholder values in `ainvoke()`: `ainvoke(TicketState(ticket_id="T-1"))` instead of `ainvoke({"ticket_id": "T-1", "category": "", "resolved": False, ...})`. `LangGraphAdapter` is now `Generic[S]` where `S: AgentState`, giving IDEs full type inference over the state schema. Sits alongside `BaseParams`, `BaseResult`, and `BaseState` in the AOA Pydantic hierarchy, all rooted in `BaseSchema`. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))

- **`CacheCoordinator` created by default in `ActionProductMachine`.** Constructing `ActionProductMachine()` without a `cache_coordinator` argument now creates an in-memory `CacheCoordinator` automatically — caching is available out of the box without any explicit configuration. Pass `cache_coordinator=None` to opt out of caching entirely; pass an explicit `CacheCoordinator` instance to use a custom one. ([#56](https://github.com/bystrovmaxim/aoa/issues/56))
- **Tag-based cache invalidation.** `on_cache_write(result, params, duration_ms)` now returns `list[CacheTag] | None` instead of `bool` — `None` skips the write, a non-empty list writes the entry and indexes it under those tags. A new hook `on_cache_invalidate(params, result)` returns `list[CacheTag] | None`; called after every successful pipeline run regardless of `cache_key`, it evicts all cached entries whose stored tags match any of the returned matchers (wildcard-aware: a `None` field in a `CacheTag` matches any value — e.g. `CacheTag(type=Order)` evicts all orders). Invalidation happens before the write. `CacheCoordinator` gains a tag index (`_tag_to_keys`, `_key_to_tags`) and `evict_by_tags(directive_tags: frozenset[CacheTag])`. `CacheTag` is a frozen dataclass with `type: type[Any] | None` and `key: str | int | None`; at least one field must be non-`None`. `cache_key` remains `str | None` — tags are declared at write time when the result is available, not in `cache_key`. ([#58](https://github.com/bystrovmaxim/aoa/issues/58))

- **`aoa-maxitor`: `LoadAOAServiceAction` — five-aspect DuckDB loader for the AOA coordinator graph.** Accepts a bare base URL or full endpoint URL; empty/whitespace input rejected by Pydantic. Aspects: validate URL format → normalize to canonical `coordinator-json` endpoint → validate HTTP reachability → parse coordinator JSON structure → build `DuckDBGraphResource`. 24 unit tests cover all aspects and Pydantic validation; integration test skipped by default. ([#78](https://github.com/bystrovmaxim/aoa/issues/78) · [aoa-maxitor CHANGELOG](../packages/aoa-maxitor/CHANGELOG.md))
- **`aoa-maxitor`: on-demand graph loading with URL input in the left sidebar.** The server no longer auto-loads a graph on startup. A new `POST /api/load` endpoint accepts a service URL, runs the load + sidebar pipeline, and stores results in `app.state`. The React left sidebar shows a URL input field with a recent-history dropdown (last 10, persisted in `localStorage`) when no graph is loaded, and a thin-stroke switch-service button in the header when a graph is active. ([#78](https://github.com/bystrovmaxim/aoa/issues/78) · [aoa-maxitor CHANGELOG](../packages/aoa-maxitor/CHANGELOG.md))
- **`aoa-maxitor 1.0.0` and `aoa-examples 1.0.0` — first stable releases.** Both packages reach `1.0.0`: `aoa-maxitor` ships the full DuckDB-backed visualization backend + React SPA; `aoa-examples` distributes the complete tutorial and how-to example set as `.py` + Colab `.ipynb` pairs. ([#78](https://github.com/bystrovmaxim/aoa/issues/78) · [aoa-maxitor CHANGELOG](../packages/aoa-maxitor/CHANGELOG.md))
- **`BaseCoordinator` marker base class introduced in `aoa-action-machine`.** All seven coordinator classes (`AuthCoordinator`, `NoAuthCoordinator`, `CacheCoordinator`, `SagaCoordinator`, `NodeGraphCoordinator`, `PluginCoordinator`, `LogCoordinator`) now inherit `BaseCoordinator`; `DebugNodeGraphCoordinator` inherits it transitively. ([#87](https://github.com/bystrovmaxim/aoa/issues/87) · [aoa-action-machine CHANGELOG](../packages/aoa-action-machine/CHANGELOG.md))
- **`BaseObserver`, `BaseIntent`, `BaseStorage`, `BaseGateway`, `BaseController(BaseResource)` introduced; `Lifecycle` is standalone.** Five new AOA primitive classes formalise the ontology in `aoa-action-machine`: `BaseObserver` (side-effect-only marker; `BaseLogger` and `Plugin` inherit it), `BaseIntent` (declarative mixin root; all 13 `*Intent` classes inherit it), and three `BaseResource` subtypes — `BaseStorage` (external data stores), `BaseGateway` (external services), `BaseController` (internal owned dependencies) — distinguished by lifecycle ownership. `Lifecycle` is a standalone primitive with no base class. ([#87](https://github.com/bystrovmaxim/aoa/issues/87) · [aoa-action-machine CHANGELOG](../packages/aoa-action-machine/CHANGELOG.md))
- **`aoa-langgraph`: `LangGraphController` — replaces `LangGraphAdapter`.** State schema declared via `.inp()/.mid()/.out()`; `AgentState` auto-generated. `.node(ActionClass)` registers classes (not instances). `.build()` validates topology + data-contract statically (8 error types). `ctrl.ainvoke(data, box)` returns a `dict` of out-fields. Nodes with `params_mapper` or `response_mapper` are excluded from data-contract checks. New errors: `NoStartNodeError`, `DeadEndNodeError`, `UnreachableNodeError`, `FinishUnreachableError`, `InconsistentFinishOutputError`, `FieldHasNoProducerError`, `OutputHasNoProducerError`, `UnexpectedResultFieldError`, `MissingInputFieldError`. ([#83](https://github.com/bystrovmaxim/aoa/issues/83) · [aoa-langgraph CHANGELOG](../packages/aoa-langgraph/CHANGELOG.md))
- **Per-route/per-tool `auth_coordinator` override in `BaseAdapter`, `FastApiAdapter`, `McpAdapter`.** `BaseRouteRecord.auth_coordinator` is a new optional field; `BaseAdapter.effective_auth_coordinator(record)` returns it when set, else the adapter's default coordinator. `FastApiAdapter.post/get/put/delete/patch(...)` and `McpAdapter.tool(...)` expose it as an `auth_coordinator=` keyword. Lets one route (e.g. a login endpoint) opt out of a strict adapter-wide coordinator without weakening it for every other route. ([#66](https://github.com/bystrovmaxim/aoa/issues/66) · [aoa-action-machine CHANGELOG](../packages/aoa-action-machine/CHANGELOG.md) · [aoa-fastapi-adapter CHANGELOG](../packages/aoa-fastapi-adapter/CHANGELOG.md) · [aoa-mcp-adapter CHANGELOG](../packages/aoa-mcp-adapter/CHANGELOG.md))
- **`aoa-action-machine[jwt]` — ready-made Bearer/JWT `AuthCoordinator`.** New optional extra (`pip install "aoa-action-machine[jwt]"`, adds `PyJWT`) under `aoa.action_machine.auth.jwt_auth`: `BearerCredentialExtractor`, `JwtAuthenticator` (signature/expiry/audience verification; `exp` is mandatory; unknown role-claim strings are dropped, not rejected), `HttpContextAssembler`, and `JwtAuthCoordinator` — a thin `AuthCoordinator` subclass wiring the three together. Issuing tokens (login) stays application code — an app's own `LoginAction` signs tokens with PyJWT directly; this coordinator only verifies them. Never imported from the core `aoa.action_machine.auth` namespace, so installing without the extra never pulls in PyJWT. ([#66](https://github.com/bystrovmaxim/aoa/issues/66) · [aoa-action-machine CHANGELOG](../packages/aoa-action-machine/CHANGELOG.md))

### Removed

- **`CacheKeyMixin` removed.** The mixin (added in [#56](https://github.com/bystrovmaxim/aoa/issues/56)) produced cache entries with no tags, making them impossible to invalidate. With the new tag-based design every action that participates in caching must implement `cache_key` explicitly and declare the tags relevant to its domain. ([#58](https://github.com/bystrovmaxim/aoa/issues/58))
- **`ConsoleLogger` added by default to `ActionProductMachine`.** Constructing `ActionProductMachine()` without any logging arguments now attaches a `ConsoleLogger` automatically. Pass `loggers=[]` for silent mode or `loggers=[MyLogger()]` to use a custom logger instead. When an explicit `log_coordinator` is passed, no default logger is added — the coordinator is used as-is.
- **`loggers` parameter on `ActionProductMachine`.** A new `loggers: list[BaseLogger] | None` keyword argument lets you supply one or more loggers without constructing a `LogCoordinator` manually. Loggers are appended via `add_logger` and compose with an explicit `log_coordinator` when both are provided.
- **`plugins` and `loggers` no longer compete with their coordinators.** Passing both `plugin_coordinator` and `plugins` (or both `log_coordinator` and `loggers`) previously silenced the content arguments. Both coordinators now expose `add_plugin` / `add_logger` and the machine calls them after coordinator resolution, so all arguments take effect regardless of combination.
- **`PluginCoordinator.add_plugin`.** New method appends a plugin to an existing coordinator instance. `plugins` constructor argument is now optional (defaults to empty list).
- **`aoa-langgraph`: `LangGraphAdapter`, `adapter.py`, `node_wrapper.py` deleted.** `LangGraphAdapter` (added in [#62](https://github.com/bystrovmaxim/aoa/issues/62)) is fully removed in favour of `LangGraphController`. Old import `from aoa.langgraph import LangGraphAdapter` will fail. ([#83](https://github.com/bystrovmaxim/aoa/issues/83) · [aoa-langgraph CHANGELOG](../packages/aoa-langgraph/CHANGELOG.md))

### Fixed

- **`F841` false positives suppressed in Jupyter notebooks.** Extended the `"**/*.ipynb"` ruff per-file-ignores to include `F841` (unused variable), which fires on cell-scoped names referenced in later cells — a pattern ruff cannot see across cell boundaries. ([#52](https://github.com/bystrovmaxim/aoa/issues/52))
- **Mypy `no-untyped-def` warnings silenced for example scripts.** The `typecheck` task now targets `src/` directories only (`mypy packages/aoa-action-machine/src packages/aoa-maxitor/src packages/aoa-examples/src`). Standalone scripts in `packages/aoa-action-machine/examples/` are demonstration code and are no longer included in the strict mypy pass. ([#52](https://github.com/bystrovmaxim/aoa/issues/52))
- **`aoa-maxitor`: `LoadAOAServiceAction` accepts arbitrary endpoint URLs.** Previously the URL normalization always appended `/examples/model/graph-json`, making it impossible to load from services with a different path (e.g. `/api/model/graph`). Now any URL with an explicit path is used as-is; the default AOA path is appended only when a bare host URL is supplied. ([aoa-maxitor CHANGELOG](../packages/aoa-maxitor/CHANGELOG.md))
- **`aoa-maxitor`: `GetLifecycleFiniteAutomatonAction` reads FSM from DuckDB instead of local class import.** Previously the endpoint called `importlib.import_module` on the entity class qualname, failing in standalone deployments where the target service's Python packages are not installed. Now queries the already-loaded DuckDB graph — no local entity classes required. ([#101](https://github.com/bystrovmaxim/aoa/issues/101) · [aoa-maxitor CHANGELOG](../packages/aoa-maxitor/CHANGELOG.md))

### Changed

- **Independent versioning: per-package git tags and CI jobs ([#76](https://github.com/bystrovmaxim/aoa/issues/76)).** Each package is now released independently. Tag format: `aoa-<pkg>-v<version>` (e.g. `aoa-fastapi-adapter-v1.0.0`). The publish CI workflow is restructured into one job per package, each triggered only by its own tag push; `workflow_dispatch` accepts a package selector for manual re-runs. The monolithic `v*` tag and the single global release trigger are retired. The `PYPI_API_TOKEN` secret is used for initial publication; migration to OIDC Trusted Publishers is planned after all packages are registered on PyPI.
- **`aoa-maxitor`: `GetLeftMenuSidebarDataAction` rewritten as a four-aspect DuckDB pipeline; `networkx` dependency removed.** The action no longer depends on `networkx`. Four `@regular_aspect` methods build sidebar `NodeCoreEntity` lists in stages — level-1 root buckets → level-2 fixed diagram rows → level-2 interchange nodes from DuckDB → level-3 per-domain ERD and per-entity class/lifecycle rows — with a `@summary_aspect` assembling the final `Result`. String helpers are `@staticmethod` methods on the class; aspect-level unit tests added. Deleted: `api/session.py`, `node_build.py`, `interchange_demo_coordinator.py`, `load_graph_action.py`. ([#78](https://github.com/bystrovmaxim/aoa/issues/78) · [aoa-maxitor CHANGELOG](../packages/aoa-maxitor/CHANGELOG.md))
- **Test distribution into per-package directories — `aoa-maxitor` (first stage).** Maxitor tests moved from the shared root `tests/maxitor/` into `packages/aoa-maxitor/tests/`, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]` so the package owns its test configuration. The skipped integration test stays in the package (skipped by default); the `[tests.zones.maxitor]` boundary zone was removed and dedicated `pytest` steps added to `run_checks_with_log.sh`. Per-package `tests/` directories are excluded from pylint via `ignore-paths` (test code is linted by ruff). ([#82](https://github.com/bystrovmaxim/aoa/issues/82) · [aoa-maxitor CHANGELOG](../packages/aoa-maxitor/CHANGELOG.md))
- **Test distribution into per-package directories — `aoa-examples` (clean subset).** Example model tests moved from the shared root `tests/examples/` — plus the clean `depends`-modes test from the legacy `aoa_examples_tests/` directory — into `packages/aoa-examples/tests/`, with a per-package dev group and pytest config. The two OCEL/pm4py tests were not kept as tests — they were converted into the runnable usage example `packages/aoa-ocel/examples/01_ocel_export.py`, and the root `tests/examples/` zone is now empty; the legacy `aoa_examples_tests/` directory and its stale `testpaths` entry are removed. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))
- **Test distribution into per-package directories — `aoa-otel`.** OpenTelemetry tests moved from the shared root `tests/otel/` into `packages/aoa-otel/tests/`. The cross-package import of `tests/action_machine/scenarios` was replaced by a minimal, self-contained sample domain under `tests/support/` (a faithful trimmed copy of `PingAction`/`TestDomain`) — the first package to use the per-package test-support pattern instead of reaching into another package's test tree. `[tests.zones.otel]` removed. ([#82](https://github.com/bystrovmaxim/aoa/issues/82) · [aoa-otel CHANGELOG](../packages/aoa-otel/CHANGELOG.md))
- **Test distribution into per-package directories — `aoa-langgraph`.** LangGraph adapter tests moved from the shared root `tests/langgraph/` into `packages/aoa-langgraph/tests/`. The cross-package import of `tests/action_machine/scenarios` was replaced by a self-contained `tests/support/` sample domain (a faithful trimmed copy of `PingAction`/`FullAction`/`OrdersDbManager`). The per-package pytest config carries the langgraph deprecation `filterwarnings`. ([#82](https://github.com/bystrovmaxim/aoa/issues/82) · [aoa-langgraph CHANGELOG](../packages/aoa-langgraph/CHANGELOG.md))
- **Test distribution into per-package directories — `aoa-ocel`.** OCEL tests (with their `contracts/`/`plugin/`/`resource/` subtrees) moved from the shared root `tests/ocel/` into `packages/aoa-ocel/tests/`. The cross-package import of `tests/action_machine/scenarios` was replaced by a self-contained `tests/support/` sample domain (`SampleCoreEntity`/`TestDomain`); the `pm4py_validation` helper moved into `tests/support/` and `pm4py` was added to the package dev group. This closes the `aoa-examples` test tail — the `pm4py_validation` helper now lives in `packages/aoa-ocel/tests/support/`, and the remaining OCEL/pm4py coverage was converted into the runnable example `packages/aoa-ocel/examples/01_ocel_export.py`; nothing OCEL-related remains parked in `tests/examples/`. `[tests.zones.ocel]` removed. ([#82](https://github.com/bystrovmaxim/aoa/issues/82) · [aoa-ocel CHANGELOG](../packages/aoa-ocel/CHANGELOG.md))
- **Test distribution into per-package directories — `aoa-fastapi-adapter`.** FastAPI adapter tests moved from the shared root `tests/action_machine/adapters/fastapi/` into `packages/aoa-fastapi-adapter/tests/` (flat). The cross-package imports of `tests/action_machine/scenarios`, the `DummyResourceManager` resource helper, and the shared `entity_projection`/`json_schema` adapter-fixture modules were replaced by a self-contained `tests/support/` package (`domain_model` + `connections` + `adapter_fixtures` + facade); `httpx` added to the package dev group for the FastAPI `TestClient`. ([#82](https://github.com/bystrovmaxim/aoa/issues/82) · [aoa-fastapi-adapter CHANGELOG](../packages/aoa-fastapi-adapter/CHANGELOG.md))
- **Test distribution into per-package directories — `aoa-mcp-adapter`.** MCP adapter tests moved from the shared root `tests/action_machine/adapters/mcp/` into `packages/aoa-mcp-adapter/tests/` (flat). The cross-package imports of `tests/action_machine/scenarios` and the shared adapter-fixture modules were replaced by a self-contained `tests/support/` package (`domain_model` + `adapter_fixtures` + facade). The graph-node FQN assertions in `test_mcp_handler.py` were updated to the sample action's new module path (`tests.support.domain_model.*`). With this, `tests/action_machine/adapters/` retains only the base-adapter tests and the shared fixture modules, which migrate with `aoa-action-machine`. ([#82](https://github.com/bystrovmaxim/aoa/issues/82) · [aoa-mcp-adapter CHANGELOG](../packages/aoa-mcp-adapter/CHANGELOG.md))
- **Test distribution into per-package directories — `aoa-action-machine` (final package).** The `action_machine` and `graph` test trees moved from the shared root `tests/` into `packages/aoa-action-machine/tests/` (subtree preserved, so the hundreds of internal `tests.action_machine.*` imports stay valid). The shared sample domain model moved from `tests/action_machine/scenarios/domain_model/` to `tests/support/domain_model/`; all 112 `tests.action_machine.scenarios.domain_model` import sites were rewritten to `tests.support.domain_model`. The package declares its own pytest config (custom markers `benchmark`/`graph_coverage`, `asyncio_mode`). `[tests.zones.action_machine]` and `[tests.zones.graph]` removed. ([#82](https://github.com/bystrovmaxim/aoa/issues/82) · [aoa-action-machine CHANGELOG](../packages/aoa-action-machine/CHANGELOG.md))

### Documentation

- **Per-package `CHANGELOG.md` files introduced.** Each published package now maintains its own changelog under `packages/<pkg>/CHANGELOG.md`: [`aoa-action-machine`](../packages/aoa-action-machine/CHANGELOG.md) (full monorepo history from `[0.1.0]`), [`aoa-fastapi-adapter`](../packages/aoa-fastapi-adapter/CHANGELOG.md), [`aoa-mcp-adapter`](../packages/aoa-mcp-adapter/CHANGELOG.md), [`aoa-langgraph`](../packages/aoa-langgraph/CHANGELOG.md), [`aoa-otel`](../packages/aoa-otel/CHANGELOG.md), [`aoa-ocel`](../packages/aoa-ocel/CHANGELOG.md). This root file will be rewritten as a cross-cutting overview that links to each package's detailed log. ([#76](https://github.com/bystrovmaxim/aoa/issues/76))
- **LangGraph docs rewritten for `LangGraphController`.** `docs/tutorials/step-14-langgraph_draft.md` and `docs/extensions/langgraph_draft.md` fully rewritten to cover `LangGraphController` API (field tiers, topology methods, build-time error table, three testing patterns). `docs/index_draft.md` step-14 and extensions entries updated to `aoa-langgraph` package. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))
- **`docs/extensions/jwt_draft.md` — Bearer/JWT extension article, with explicit per-adapter support matrix.** New full article for `aoa-action-machine[jwt]` / `JwtAuthCoordinator`: two-phase model (login issuance vs. Bearer verification), a full worked FastAPI cycle (`examples/step_13_fastapi/03_login_action.py` + `04_bearer_auth.py`, both with Colab `.ipynb` siblings), an explicit "does not work with MCP" section with the three-layer explanation (stdio transport can't in principle; HTTP-based MCP transports could via the `mcp` SDK's own Bearer middleware; `aoa-mcp-adapter` itself never forwards request data regardless of transport — [#113](https://github.com/bystrovmaxim/aoa/issues/113)) and a runnable demonstration (`examples/step_14_mcp/02_bearer_auth_limitation.py`), plus a variants section (HS256 vs. RS256/JWKS, `audience`/`issuer`, refresh tokens). `docs/index_draft.md` (Готовые расширения) and `docs/tutorials/step-12-authentication_draft.md` (Четыре готовых метода) link to it. ([#66](https://github.com/bystrovmaxim/aoa/issues/66))

## [1.0.0a5] – 2026-06-20

### Breaking changes

- **`NoneRole` removed; use `GuestRole`.** `NoneRole` expressed absence ("no role"); `GuestRole` expresses intent ("guest / public access, declared explicitly"). The class `aoa.action_machine.auth.none_role.NoneRole` and the file `none_role.py` are deleted. Replace every import and every `@check_roles(NoneRole)` with `GuestRole`. `GuestRole` is exported from `aoa.action_machine.auth` and `aoa.action_machine.intents.check_roles`. ([#46](https://github.com/bystrovmaxim/aoa/issues/46))

## [1.0.0a4] – 2026-06-20

### Fixed

- **`Level.info` no longer forces white foreground in `ConsoleLogger`.** Removed the explicit `#FFFFFF` truecolor entry from `DEFAULT_LEVEL_FG_PREFIX`. The terminal (or notebook environment) now decides the foreground color for info messages, making them readable on both dark terminals and light-background environments such as Google Colab. `warning` (#FFCC00) and `critical` (#FF2222) colors are unaffected.
- **Ruff false positives in Jupyter notebooks.** Added `"**/*.ipynb" = ["F404", "E402", "F401", "RUF005"]` under `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`. Notebook cells share cross-cell scope that ruff cannot see, producing 42 spurious import errors in `examples/`. After the fix `ruff check examples/` passes clean.

## [1.0.0a3] – 2026-06-17

### Documentation

- **First complete documentation set for the whole project.** Introduced a full [Diátaxis](https://diataxis.fr/) documentation tree under `docs/`, navigated from a single hub (`docs/index.md`): a step-by-step **tutorial** (getting started through Maxitor, steps 00–26), **how-to guides** (choosing Action / aspect / resource, migrating a legacy codebase, and eight extension-authoring guides), **reference** (FAQ, glossary, formal model, intents & invariants), **explanation** (philosophy / IOP, comparison with other frameworks, system altitudes, “questions AOA answers with code”), **ready-extension cards** (ConsoleLogger, FastAPI, MCP, OCEL 2.0, OpenTelemetry, PostgreSQL), and a **research note** (what the system knows about itself).
- **Runnable examples in two forms.** Every example under `examples/` now ships both as a plain `.py` and as a Colab `.ipynb` (English, identical logic, `!pip install` cell + top-level `await`), covering the full tutorial set plus the non-tutorial how-to / extension / research examples. Tutorial chapters carry a dual-form “Try in Colab · Open in project” link line.
- **README rework.** `packages/aoa-action-machine/README.md` becomes a focused quick-start that leads into the tutorial; the root `README.md` links are repointed to the new `docs/` chapters and to current example paths.

## [1.0.0a2] – 2026-06-15

### Added

- **OpenTelemetry Traces support (`tracer_provider`).** `OpenTelemetryPlugin(tracer_provider=tp)` emits one root span per `machine.run()` and child spans per aspect, `@on_error` handler, and compensator. Saga rollback events are recorded as timed span events on the root span. Requires `aoa-otel`.
- **OpenTelemetry Logs support (`logger_provider`).** `OpenTelemetryPlugin(logger_provider=lp)` emits a structured log record for every lifecycle event. After-aspect records carry `aoa.state.<field>` attributes with per-field serialization of `aspect_result` (state x-ray). Self-sufficient without `tracer_provider`; when both providers are configured, logs carry OTel-native `trace_id`/`span_id` for automatic backend correlation.
- **`opaque=True` on checkers — exclude complex objects from state x-ray.** All `result_*` decorators (`result_string`, `result_int`, `result_float`, `result_bool`, `result_date`, `result_instance`) accept `opaque: bool = False`. Fields marked `opaque=True` are excluded from `aoa.state.*` log attributes. `CheckerGraphPayload` and `CheckerGraphNode` carry `opaque` as a named field symmetric with `required`; the machine computes `opaque_fields` from the graph at emit time and delivers it on `AfterRegularAspectEvent.opaque_fields` — no runtime introspection in the plugin.
- **`watch_actions` filter on `Plugin`.** `watch_actions=frozenset({MyAction})` limits plugin delivery to the given action classes and their subclasses (`issubclass` check). Implemented in `Plugin` base class; available to all plugins.
- **`watch_events` filter on `Plugin`.** `watch_events=frozenset({GlobalFinishEvent})` limits plugin delivery to the given event types. Implemented in `Plugin` base class; available to all plugins.

## [1.0.0a1] – 2026-06-14

### Fixed

- **`DuplicateNodeError` on Action class re-definition in interactive environments.** `BaseGraphNodeInspector._all_descendant_types` now silently drops stale class objects that `BaseAction.__subclasses__()` keeps alive after a Jupyter / Colab cell re-run. A class is filtered only when its module is present in `sys.modules`, its `__qualname__` resolves to a *different* object in that module, and no `<locals>` segment appears in the qualname (i.e. not a local class). In every other case the class is kept — making the filter a no-op in production and purely additive for notebook environments.

## [1.0.0a0] – 2026-05-22

### Breaking changes

- **Remove standalone `aoa-graph` wheel.** Interchange primitives and coordinators now ship only inside `aoa-action-machine`. The workspace builds **four** wheels (`aoa-action-machine`, `aoa-ocel`, `aoa-maxitor`, `aoa-examples`); `pip install aoa-graph` is gone. Migrate `from aoa.graph…` → `from aoa.action_machine.graph.core…` (e.g. `NodeGraphCoordinator`, `InvalidGraphError`, `exclude_graph_model`, edge relationship constants).
- **Fold `graph_model` into `aoa.action_machine.graph`.** Domain projection modules move under one tree: `graph/core/` (former `aoa.graph`), `graph/nodes/`, `graph/edges/`, `graph/inspectors/`, plus leaf modules `graph/node_graph_coordinator_factory.py` and `graph/graph_json_schema.py`. Replace `aoa.action_machine.graph_model.*` imports with the matching `aoa.action_machine.graph.*` path.
- **Rename `integrations/` to `adapters/` and relocate Postgres.** FastAPI and MCP transport code is `aoa.action_machine.adapters.fastapi` / `adapters.mcp` (was `integrations.*`). `PostgresResource` is `aoa.action_machine.resources.postgres` (was under `integrations.postgres`). Optional extras `[fastapi]`, `[mcp]`, and `[postgres]` are unchanged — only import paths move.
- **Graph package facade is core-only.** `aoa.action_machine.graph` re-exports interchange primitives from `graph.core` only. Import `create_node_graph_coordinator` from `aoa.action_machine.graph.node_graph_coordinator_factory` and `GRAPH_JSON_SCHEMA` from `aoa.action_machine.graph.graph_json_schema` — lazy `__getattr__` re-exports on the package `__init__` are removed.

### Changed

- **Monorepo layout and boundaries.** `scripts/package_boundaries.toml`, packaging smoke, publish workflow, and `task build-packages` no longer reference `packages/aoa-graph`. `action_machine` is self-contained for graph code; cross-package rules for `ocel`, `maxitor`, and `examples` are updated accordingly.
- **Root README repositioned as AOA / IOP.** Installation table lists four wheels; quick-start covers OCEL export and Maxitor; link to `docs/intents-and-invariants.md` for decorator semantics and structural invariants.

### Fixed

- **CI import-boundary checks after graph merge.** Test layer rules for `tests/action_machine/graph/` are satisfied by moving runtime-dependent generalization tests to `graph_host/` and lazy graph export smoke to `tests/action_machine/smoke/`; narrow allowlist entries cover `exclude_graph_model` in model-layer cleanup tests.
- **Maxitor samples public API.** `aoa.examples.model` may import coordinator types from `aoa.action_machine.graph.core.{debug_node_graph_coordinator,exceptions,node_graph_coordinator}` and the factory leaf module — aligned with post-merge paths.

### Removed

- **`packages/aoa-graph`.** Standalone graph wheel and `aoa.graph` namespace package deleted; all graph runtime code lives under `aoa.action_machine.graph`.
- **`aoa.action_machine.integrations`.** Directory removed after adapter/resource relocation; update any out-of-tree imports before upgrading.

## [0.12.8] – 2026-05-22

### Documentation

- **OCEL export policy (v1).** `packages/aoa-ocel/src/aoa/ocel/README.md` documents E2O-only export, loaded-relation reachability, one-hop peer materialization, and aspect-controlled participation via partial entity loading.

### Breaking changes

- **@depends on concrete actions requires `mode`.** Host actions that depend on another `BaseAction` subclass must pass `mode=UseCase.include` or `mode=UseCase.extend`. Dependencies on `BaseResource` must omit `mode`. Call sites that only `box.resolve` a peer action should use `extend` until an unconditional `await box.run(...)` / `machine.run` path exists; then `include` is appropriate where the peer must always run in that root session.

### Added

- **OCEL 2.0 export (`aoa-ocel`).** New wheel `aoa-ocel` with `OcelFrame` aspect contract, `OcelPlugin` on `GlobalFinishEvent`, and E2O-only v1 policy (loaded one-hop FK relations, composite peer qualifiers, no O2O). `InMemoryOcelStoreResource` / `OcelStoreResource` accumulate `OcelEvent` DTOs and persist OCEL 2.0 JSON on `close()`; nested actions receive `OcelStoreWrapper`. `ActionProductMachine` exposes `all_aspect_states` on finish events so plugins can scan aspect pipeline state without mutating it. PM4Py smoke validation helpers live under `tests/ocel/`.
- **Store domain OCEL example.** `aoa-examples` ships StoreDomain lifecycle trace actions (`PublishOrder*OcelAction`), `build_store_ocel_machine` / `run_store_ocel_trace_batch`, and integration coverage writing `archive/logs/ocel.json` with OCPM-friendly `short_names` type labels.
- **UML generalization edges in the interchange graph.** Direct superclass links on the Action, Role, and Domain axes are exported as `parent_action`, `parent_role`, and `parent_domain` edges with relationship `Generalization` (`GENERALIZATION.archimate_name`). `GeneralizationGraphEdge.collect_direct_parents` in `aoa-graph` is the single parent-resolution algorithm; coordinator `to_json()` and `get_edges_by_type` expose the full edge set with no `include_generalization` flag. Maxitor DuckDB stores these in `parent_action_edges` / `parent_role_edges` / `parent_domain_edges` and in the unified `edges` view. **Exception:** `FullGraphAction` omits generalization links in the G6 full-graph payload only, filtering SQL by `relationship <> 'Generalization'` so the visualization stays sparse while data exports remain complete.
- **UML-style `@depends` mode (Use Case stereotypes).** `UseCase` / `VALID_USE_CASE_MODES`, `DependencyInfo.mode`, decorator validation, `DependsGraphEdge` and `resolved_dependency_infos` round-trip, and interchange JSON Schema (`optional` `mode` enum `include` / `extend` on `@depends` edges). `DependsIntentResolver.resolve_include_dependency_types` lists declared `include` targets. Package docs and READMEs describe semantics; **Maxitor DuckDB `depends_edges` in the default v1 path does not add a `mode` column** — consumers read `mode` from the full graph JSON.
- **Include contract on successful root runs.** `ActionProductMachine` tracks action classes that enter `_run_internal` for the current root session (`ContextVar`) and runs `IncludeContractChecker` before `emit_global_finish` when the aspect pipeline ran (including success paths that return only from `@on_error`). Missing `UseCase.include` executions raise `IncludeContractViolationError` with `missing_include_types`. Root cache hits that skip the pipeline skip this check.
- **Entity lifecycle (finite-state) diagram in Maxitor.** The operator SPA can open an entity’s **Lifecycle view**: Graphviz `dot` renders the automaton as SVG with pan/zoom, LR/TB rank direction, and a **Fit to window** control. The backend exposes the lifecycle payload for the viewer (`GET /api/v1/lifecycle-finite-automaton`).
- **UML use-case diagram in Maxitor.** The operator SPA can render a domain-scoped UML-style use-case slice (actions in the Domain boundary, roles, `@check_roles` associations, action/role generalizations, and `@depends` edges including `UseCase.include` / `UseCase.extend` stereotypes) as Graphviz SVG with pan/zoom, Dot LR/TB and Neato/FDP layout presets, **Fit to window**, optional one-hop narrowing, and a sidebar entry per domain (`use_case_domain`). The payload is produced by `**GetDomainUseCaseDiagramAction`** from the DuckDB graph snapshot (`GET /api/v1/domain-use-case-diagram`).

### Fixed

- **Lifecycle Graphviz auto-fit.** Initial fit, resize refit, and LR/TB toggles now measure the correct SVG geometry (no stale markup, no `visibility: hidden` measurement trap), align `hasFittedRef` with successful fits, and apply a follow-up frame fit to match manual **Fit to window** without visible snapping.

## [0.12.5] – 2026-05-08

### Added

- **Optional action result cache.** `ActionProductMachine` accepts an injected `CacheCoordinator` (in-memory store, namespaced keys, optional `max_size` eviction). `BaseAction` gains `cache_key`, `read_cache`, and `on_cache_write`; the machine orchestrates reads after role/connection gates and `emit_global_start`, and writes only after a clean summary path (handled `@on_error` results are never cached). `CacheContractError` enforces hook return contracts; hook or coordinator failures propagate without `emit_global_finish` in v1.
- **JSON Schema fields in results.** Result schemas can declare explicit JSON-shaped fields so adapters expose the intended wire contract instead of relying on implicit Python object structure.
- **Entity JSON Schema projections in results.** `BaseEntity` classes can be referenced from result fields through an explicit JSON Schema projection, preserving the entity relationship while returning only the declared wire fields.
- **Node graph JSON serialization.** `NodeGraphCoordinator.to_json()` exports a stable JSON payload with linear `nodes` and `edges` lists, including node ids/types/labels/properties and edge source/target/type/relationship metadata, so downstream tools can reconstruct the coordinator graph without touching Python runtime objects.
- **NetworkX-friendly graph payloads.** Node and edge JSON is shaped for direct reconstruction into `networkx.DiGraph`: nodes are keyed by stable ids, edges carry `source_node_id` and `target_node_id`, and empty `nodes` / `edges` payloads are valid.

### Changed

- **Maxitor operator UI: React SPA instead of generated HTML as the primary surface.** The main Maxitor experience is now a **Vite** + **React** app (`packages/aoa-maxitor/client`) talking to the Maxitor FastAPI backend, rather than treating standalone Python-built HTML pages as the default workflow. Server-side HTML visualizers remain available where documented for specific interchange exports, but day-to-day graph exploration and diagrams are intended through the SPA.

### Removed

- **rustworkx from the interchange graph stack.** The live coordinator graph is no longer a rustworkx `PyDiGraph`; `aoa-graph` does not depend on rustworkx. Topology uses typed interchange nodes/edges with in-tree DAG checks (`aoa.graph._dag`); **NetworkX** is used where consumers need a `DiGraph` view (e.g. JSON export), not as an embedded rustworkx runtime.

### Breaking changes

- **Multiple PyPI packages and `aoa.*` layout.** Runtime code lives under `packages/aoa-*/src/aoa/{graph,action_machine,maxitor,examples}`. Public imports are `**aoa.graph`**, `**aoa.action_machine`**, `**aoa.maxitor**`, and `**aoa.examples**` only. Install `**aoa-graph**`, `**aoa-action-machine**`, `**aoa-maxitor**`, or `**aoa-examples**` as needed; there are no legacy top-level shims (`graph.*`, `action_machine.*`, …). `**aoa-examples**` does not pull `**aoa-maxitor**` as a dependency.

## [0.11.5] – 2026-05-08

### Changed

- **Interchange graph as the canonical topology.** Coordinators and tooling now pivot on `**NodeGraphCoordinator`** and typed interchange vertices (`**BaseGraphNode`**) and edges (`**BaseGraphEdge`**) — domains, lifecycle/entity meshes, declarative facets, propagated domain membership, and stable edge payloads (DAG flags, attachment / line-style metadata) replace ad-hoc graph sketches for visualization and serializers.

### Added

- **Interchange graph HTML visualizer.** `**maxitor.visualizer.graph_visualizer`** exports standalone **AntV G6** HTML from an already-built coordinator — forced layout seeded from domains, legends and hull overlays, interchange chrome (legend + tooling), hover affordances, **shared right-hand detail drawer** (`InterchangeDetailPanel`), and default artefact `**archive/logs/graph_node.html`**.
- **ERD HTML visualizer from the coordinator graph.** `**maxitor.visualizer.erd_visualizer`** builds relational diagrams per bounded context from the live graph (`erd_graph_data` / `erd_html`): standalone HTML with **Graphviz** wasm, **Cytoscape** + dagre, and **Mermaid** `erDiagram`, plus blended domains and UX aligned with the graph viewer (**shared interchange chrome**, same detail-drawer semantics for entity keys).

### Removed

- **Legacy ERD package split.** Drops the old `**erd_visualizer_1`** / `**erd_visualizer_2`** layout; `**erd_visualizer`** is now the single graph-backed viewer entry point.

## [0.10.0] – 2026-04-12

### Breaking changes

- **MCP tool `TextContent` bodies.** Responses are JSON objects with a uniform envelope: success uses `ok`, `code`, and `data`; errors use `ok`, `code`, `message`, and `details`. Plain action JSON and legacy prefixed strings (`PERMISSION_DENIED: …`, `INVALID_PARAMS: …`, `INTERNAL_ERROR: …`) are removed. Clients must parse the envelope. Unexpected failures return `message: "Unexpected failure"` without echoing exception text; operators use server logs.

### Changed

- `**ValidationFieldError`.** Optional keyword-only `details` (`dict`) for structured context; existing `ValidationFieldError(message)` and `ValidationFieldError(message, field)` calls behave as before. `str(exc)` remains the human `message` only.
- **MCP adapter.** Pydantic tool-arg validation lives in `_validate_tool_request_kwargs`, called from `_execute_tool_call`, so mapping to `ValidationFieldError` is defined in one place and covered by direct unit tests.

### Fixed

- **MCP tool kwargs validation.** Pydantic `model_validate` failures are surfaced as `ValidationFieldError` with `details.errors` and map to `INVALID_PARAMS`, not `INTERNAL_ERROR`.
- **Saga frame when result validation fails.** If a regular aspect `call()` returns but checkers (or declared-field rules) reject the dict, `AspectExecutor` still appends a `SagaFrame` with `state_after=None` when the action has compensators, so rollback invokes that aspect’s compensator (then earlier frames) before surfacing the validation error.

### Tests

- `**test_mcp_handler`.** Envelope assertions, Pydantic edge cases, `details` propagation, and internal-error privacy expectations.
- `**_validate_tool_request_kwargs`.** Direct unit tests (including `field_validator` failures) plus `_execute_tool_call` short-circuit before `machine.run` / auth.
- `**test_scoped_logger_hot_path_bench`.** Wall-clock budgets for bulk `ScopedLogger` / `LogScope` construction (aspect-path parity).
- `**test_saga_checker_rejection_compensate_order`.** Two aspects: first commits; second fails checkers — both compensators run (second first, with `state_after=None`).

## [0.9.0] – 2026-04-12

### Breaking changes

- `**SqlConnectionManager` renames.** `IConnectionManager` → `SqlConnectionManager` (`sql_connection_manager`); `WrapperConnectionManager` → `WrapperSqlConnectionManager` (`wrapper_sql_connection_manager`). No compatibility aliases.
- **Transactional `begin()`.** SQL connection managers implement `async def begin() -> None` after `open()`; `WrapperSqlConnectionManager.begin()` raises `TransactionProhibitedError` (same as `open`/`commit`/`rollback`). `PostgresConnectionManager` runs `BEGIN`.
- **Resource manager modules.** `resource_managers.connection` → `connection_decorator`; `resource_managers.connections` → `connections_typed_dict`. Canonical package: `aoa.action_machine.resources`. The old `resource_managers` package directory was removed; imports use `aoa.action_machine.resources` only.
- **Decorator modules (`*_decorator.py`).** e.g. `regular_aspect_decorator`, `check_roles_decorator`, `depends_decorator`, `on_decorator`; public decorator callables unchanged.
- **GateHost → Intent.** `*GateHost` → `*Intent`, `*GateHostInspector` → `*IntentInspector`, `BaseGateHostInspector` → `BaseIntentInspector`; files `*_intent.py` / `*_intent_inspector.py`.


| Legacy (removed)             | Replacement                  |
| ---------------------------- | ---------------------------- |
| `ActionMetaGateHost`         | `ActionMetaIntent`           |
| `ResourceMetaGateHost`       | `ResourceMetaIntent`         |
| `RoleGateHost`               | `RoleIntent`                 |
| `DependencyGateHost`         | `DependencyIntent`           |
| `CheckerGateHost`            | `CheckerIntent`              |
| `AspectGateHost`             | `AspectIntent`               |
| `CompensateGateHost`         | `CompensateIntent`           |
| `ConnectionGateHost`         | `ConnectionIntent`           |
| `OnErrorGateHost`            | `OnErrorIntent`              |
| `ContextRequiresGateHost`    | `ContextRequiresIntent`      |
| `DescribedFieldsGateHost`    | `DescribedFieldsIntent`      |
| `EntityGateHost`             | `EntityIntent`               |
| `OnGateHost`                 | `OnIntent`                   |
| `RoleModeGateHost`           | `RoleModeIntent`             |
| `BaseGateHostInspector`      | `BaseIntentInspector`        |
| `RoleGateHostInspector`      | `RoleIntentInspector`        |
| (same pattern)               | `*IntentInspector` per facet |
| `SensitiveGateHostInspector` | `SensitiveIntentInspector`   |


- **Described-field snapshots per schema.** `get_snapshot(SomeAction, "described_fields")` is removed. Use `get_snapshot(OrderParams, "described_fields")` and `get_snapshot(OrderResult, "described_fields")`; for the action’s `P`/`R` linkage use `get_snapshot(SomeAction, "action_schemas")`.
- `**GraphCoordinator.get_graph()` payloads.** Raw `rx.PyDiGraph` nodes store only `node_type`, `name`, and `class_ref`. Facet `meta` is not on the node; use `hydrate_graph_node(dict(graph[idx]))` or `get_node` / `get_nodes_by_type` / `get_nodes_for_class`.

### Added

- `**GraphCoordinator.hydrate_graph_node`.** Rebuilds `meta` from facet snapshots. Phase 1 records `graph_key → facet_snapshot_storage_key`; merged structural `action` with both `depends` and `connections` maps to ambiguous hydration (empty `meta`). Stubs without registration fall back to `get_snapshot(cls, node_type)` except for `action`.
- `**ActionTypedSchemasInspector`.** After `DescribedFieldsIntentInspector`; `action_schemas` nodes and `uses_params` / `uses_result` edges to `described_fields`; snapshot key `"action_schemas"`.
- **MCP `system://graph` JSON.** Edges include `source_key` and `target_key` (`node_type:name`); `type` is the string `edge_type` from edge payloads.
- **Adapter mapper guards (`BaseRouteRecord`).** `ensure_machine_params` / `ensure_protocol_response` at FastAPI and MCP boundaries (`TypeError` on mismatch).
- **Runtime action result typing.** Summary and `@on_error` returns checked against declared `R` (`action_result_binding`); `P`/`R` resolution in `action_generic_params`.
- **Tests.** `test_graph_skeleton_and_hydrate.py`, `test_graph_execution_adapters.py`; MCP graph JSON tests in `test_mcp_handler.py`.

### Changed

- **Intents package layout.** Declarative modules live only under `aoa.action_machine.intents.`* (`auth`, `aspects`, `checkers`, `compensate`, `context`, `logging`, `on_error`, `plugins`, `meta`, `described_fields`). Duplicate top-level packages (`auth/`, `aspects/`, … at repo root) and `core/meta_*.py` / `core/described_fields_intent.py` re-export stubs were removed. `DescribedFieldsIntent` is in `aoa.action_machine.intents.described_fields.marker` (re-exported from `aoa.action_machine.intents.described_fields`).
- **Graph package.** `aoa.action_machine.metadata` → `graph` (`GraphCoordinator`, `FacetPayload`, `BaseIntentInspector`, facet snapshots, `graph_execution_adapters`, exceptions, cleanup). All `*IntentInspector` modules live under `aoa.graph.inspectors.`*; imports from `aoa.action_machine.metadata` are removed.
- **Runtime package.** `aoa.action_machine.core` removed. Machines live under `aoa.action_machine.runtime.machines` (`ActionProductMachine`, `SyncActionProductMachine`, `CoreActionMachine`); binding under `aoa.action_machine.runtime.binding` (`action_generic_params`, `action_result_binding`); shared runtime modules and execution components under `aoa.action_machine.runtime` and `aoa.action_machine.runtime.components`. Import `CoreActionMachine` from `aoa.action_machine.runtime` (lazy `__getattr__` so `runtime.navigation` does not eager-load the graph stack during `model` init) or from `aoa.action_machine.runtime.machines.core_action_machine`.
- **Resources tests path.** Tests for connection managers live under `tests/resources/` (formerly `tests/resource_managers`).
- `**DescribedFieldsIntentInspector`.** Follows `DescribedFieldsIntent`; walks `BaseParams` / `BaseResult` / `BaseEntity`; graph `node_meta` key `schema_fields`.
- `**extract_action_params_result_types`.** Single location: `aoa.action_machine.runtime.binding.action_generic_params`.
- **Described-fields validation API.** Removed `validate_described_fields(action_cls, ...)`. Use `validate_described_schema` / `validate_described_schemas_for_action`.
- **Plugin lifecycle events.** The six machine event types are emitted only via `PluginEmitSupport` async helpers; `ActionProductMachine` does not call `plugin_ctx.emit_event` or build those event classes. `PluginRunContext` is passed into each helper and is not stored on `PluginEmitSupport`.
- **README / README-2 glossary.** Intent, coordinator graph skeleton vs snapshots, hydration.

### Fixed

- **Saga rollback on summary contract failures.** If regular aspects ran and pushed `SagaFrame`s and the pipeline then fails with `ActionResultTypeError`, `MissingSummaryAspectError`, or `ActionResultDeclarationError`, `SagaCoordinator.execute` runs before re-raising. `@on_error` is not used for these contract violations.

### Documentation

- **Glossary** at the end of `README.md` and `README-2.md` (Intent, `IntentInspector`, `GraphCoordinator`, decorator, scratch).
- **Repository check (2026-04-12):** no `GateHost` / `gate_host` / `*gate_host`* symbols or filenames under `src/**/*.py` and `tests/**/*.py`; historical names remain in this changelog only where noted.
- **No deprecation aliases.** No `RoleGateHost = RoleIntent` shims and no `aoa.action_machine.compat` package; the public API uses Intent names only while the project is pre-`1.0.0`. Any future temporary aliases would ship in a dedicated release with an explicit removal timeline and `DeprecationWarning` on each alias.

## [0.8.0] – 2026-04-07

### Added

- **Saga compensation (`@compensate`).** Added a compensation mechanism (Saga pattern) to roll back side effects when an error occurs in the regular aspect pipeline. Any regular aspect can have a compensator method declared with `@compensate(target_aspect, description)`. When an error occurs in any aspect, all previously completed aspects are rolled back in reverse order. Compensators can use `@context_requires` and receive two states: `state_before` (state before the aspect) and `state_after` (state after the aspect, `None` if a checker rejected the result). The return value of a compensator is ignored.
- **Local compensation stacks.** Each `_run_internal()` call creates its own local `SagaFrame` stack. There is no global stack, ensuring correct isolation for nested `box.run()` calls. If a parent aspect catches a child action exception via `try/except`, the child stack is already unwound, and the parent aspect is added to the parent stack – subsequent errors in the parent cause only the parent stack to be rolled back.
- **Silent compensator errors.** Exceptions raised inside a compensator are completely suppressed and do not interrupt stack unwinding. All remaining compensators still get a chance to execute. Failure information is available only through the new typed event `CompensateFailedEvent`, which monitoring plugins can subscribe to. This guarantees that a rollback error does not mask the original business error and does not break consistency.
- **New typed compensation events.** Added two levels of events:
  - **Whole‑rollback level:** `SagaRollbackStartedEvent` (contains `stack_depth`, `compensator_count`, `aspect_names`) and `SagaRollbackCompletedEvent` (contains `total_frames`, `succeeded`, `failed`, `skipped`, `duration_ms`, `failed_aspects`).
  - **Single compensator level:** `BeforeCompensateAspectEvent` (contains `error`, `compensator_name`, `state_before`, `state_after`), `AfterCompensateAspectEvent` (contains `duration_ms`), and `CompensateFailedEvent` (contains `original_error`, `compensator_error`, `failed_for_aspect`).
- `**SagaFrame` – compensation stack frame.** An immutable dataclass that stores, for each successfully executed regular aspect: a reference to its compensator (`CompensatorMeta`), the aspect name, and the state before and after the aspect. The stack is accumulated in `_execute_regular_aspects()` and consumed by `_rollback_saga()`.
- `**CompensatorMeta` in `ClassMetadata`.** Added field `compensators: tuple[CompensatorMeta, ...]` and helper methods `has_compensators()`, `get_compensator_for_aspect(aspect_name)`. Compensators are collected from `vars(cls)` (not inherited). Invariants are validated in `MetadataBuilder.build()`: target aspect must exist, must be a regular aspect, and at most one compensator per aspect.
- **Compensator graph in `GraphCoordinator`.** New node type `"compensator"` and edge type `"has_compensator"` (leaf edge, no cycle check). Compensator nodes store metadata `target_aspect`, `description`, `method_name`. If a compensator uses `@context_requires`, additional `"requires_context"` edges are added to `context_field` nodes.
- `**TestBench.run_compensator()` method.** Allows unit‑testing a compensator in isolation by passing `params`, `state_before`, `state_after`, `error`, and optionally `box`, `connections`, `context`. Unlike production, compensator errors are **not** suppressed – this makes it easy to test boundary conditions and verify that a compensator behaves correctly when it must fail. The API is symmetric with `run_aspect()`: method lookup by name, validation of the `@compensate` decorator, and support for `@context_requires`.
- **Naming rule for compensators.** Compensator method names must end with `_compensate` (enforced by `@compensate`, violation raises `ValueError`). The suffix ensures visual identification of compensators in action classes.
- `**rollup=True` skips compensation.** When `box.rollup is True`, the compensation stack is not built and `_rollback_saga()` is never called. Transactional rollback in that mode is handled by `SqlConnectionManager` (which executes `rollback()` instead of `commit()`), while non‑transactional side effects (HTTP requests, email sending) are not compensated in rollup mode.

### Changed

- `**ActionProductMachine._execute_regular_aspects()` now returns a tuple `(state, saga_stack)`.** This allows `_execute_aspects_with_error_handling()` to obtain the stack for later unwinding when an exception occurs.
- **Error handling order:** compensation stack unwinding (`_rollback_saga()`) now happens **before** calling an `@on_error` handler (if any). This guarantees that the error handler works with consistent data after all side effects of previously completed aspects have been rolled back.
- `**ActionProductMachine._execute_aspects_with_error_handling()` declares `saga_stack` before the `try` block.** The stack is accessible in the `except` clause even if the exception originates inside `_execute_regular_aspects()`. Frames for the failed aspect are not added, but frames for all previous successful aspects remain.
- `**_rollback_saga()` never raises exceptions.** Compensator errors are caught, logged via `CompensateFailedEvent`, and the unwinding continues. After the loop, a `SagaRollbackCompletedEvent` is emitted with the final counters. The original aspect error is then propagated (or passed to `@on_error`).

### Fixed

- **Nested `try/except` with `box.run()` now works correctly.** Previously, if a parent aspect caught an exception from a child action, the parent aspect was not added to the parent stack, causing missing compensation for the parent when a later aspect failed. Now the child’s internal stack is unwound independently, and the parent aspect is added to the parent stack as if the child call succeeded (from the parent’s perspective).
- **Compensator `state_after=None` handling.** When a checker rejects an aspect’s result, the aspect may still have performed a side effect (e.g., an HTTP request was already sent). The compensator now receives `state_after=None` and can choose to skip compensation or perform a best‑effort rollback based on available data from `state_before` or other sources.
- `**rollup=True` no longer causes compensator stack to be built.** Previously the stack was built but not used; now the entire stack creation is skipped, improving performance and avoiding misleading `skipped` counters in events.

### Removed

- `**CompensateIntent` (no extra mixin required for compensators).** Compensators rely on `AspectIntent` (already inherited by `BaseAction`). No separate intent mixin is required.

### Security

- **Compensator errors never expose internal state to `@on_error` handlers.** The original business exception is preserved; compensator failures are isolated to monitoring events, preventing information leakage or unexpected error masking.

## [0.7.0] – 2026-04-07

### Added

- **Frozen `BaseState` and `BaseResult`.** Both types are now fully immutable after creation. `BaseState` uses `__setattr__` override to forbid any writes; the only way to modify state is to create a new instance via `BaseState({**old.to_dict(), **new_data})`. `BaseResult` is a frozen Pydantic model (`frozen=True`, `extra="forbid"`), ensuring that result fields are strictly declared and cannot be mutated after the summary aspect returns. This eliminates entire classes of bugs where aspects could silently bypass checkers or mutate results.
- `**@context_requires` decorator for controlled context access.** Aspects and error handlers can now declare exactly which context fields they need using dot‑path strings (e.g., `@context_requires(Ctx.User.user_id, Ctx.Request.trace_id)`). The machine provides a `ContextView` object that only grants access to the requested fields; any attempt to read an undeclared field raises `ContextAccessError`. Without the decorator, an aspect receives **no** context access at all. This implements the principle of least privilege and makes context dependencies explicit and statically verifiable.
- `**Ctx` constant hierarchy.** A structured set of constants (`Ctx.User.user_id`, `Ctx.Request.trace_id`, `Ctx.Runtime.hostname`, etc.) providing IDE autocompletion and compile‑time checks for standard context fields. Custom fields can be passed as plain strings, e.g., `"user.billing_plan"`.
- `**DotPathNavigator` – unified dot‑path navigation.** Centralised the navigation logic previously duplicated between `BaseSchema.resolve()` and `VariableSubstitutor`. The navigator uses duck typing (`__getitem__` detection) to support `BaseSchema`, `LogScope`, `dict`, and any custom object with a dict‑like interface, without creating circular dependencies between core and logging.
- **Strict underscore rule in log templates.** Any template variable whose **any** path segment starts with an underscore now raises `LogTemplateError`. Previously only the last segment was checked, which allowed bypassing private attributes through intermediate segments (`{%context._internal.public_key}`). All segments are now validated.
- `**@on_error` decorator for action‑level error handling.** Actions can declare handlers for exceptions raised by any aspect. Handlers receive the error and can return an alternative `Result`, effectively replacing the action’s outcome. Handlers are checked in declaration order; the first matching exception type (via `isinstance`) is executed. Handlers can also request context via `@context_requires`, receiving their own `ContextView`. Cyclic exception type coverage (e.g., `Exception` before `ValueError`) is detected at metadata build time and raises `TypeError`.
- `**OnErrorHandlerError` exception.** Wraps exceptions that occur inside an `@on_error` handler, preserving the original exception as `__cause__`. Distinguishes between business logic errors (original aspect exception) and bugs in error handling code.
- **Naming invariants (suffix checks).** The framework now enforces naming conventions via `__init_subclass__` and decorator validations:
  - Action classes must end with `Action`.
  - Domain classes must end with `Domain`.
  - Methods with `@regular_aspect` must end with `_aspect`.
  - Methods with `@summary_aspect` must end with `_summary`.
  - Methods with `@on_error` must end with `_on_error`.
  - Plugin methods with `@on` must start with `on_`.
  - Checker classes must end with `Checker`.
  Violations raise `NamingSuffixError` or `NamingPrefixError`.
- `**check_roles` as a function (decorator).** Replaced the old `CheckRoles` class with a plain function `check_roles(spec)`. The `desc` parameter (previously ignored) has been removed entirely. Special values `ROLE_NONE` and `ROLE_ANY` are now module‑level constants.
- **Result checkers as function decorators.** Each checker now has a dedicated function decorator: `result_string`, `result_int`, `result_float`, `result_bool`, `result_date`, `result_instance`. The old class‑based invocation has been removed. Decorators no longer accept a `description` parameter, keeping the API minimal.
- `**SyncActionProductMachine` – synchronous production machine.** A synchronous counterpart to `ActionProductMachine` that wraps the async pipeline in `asyncio.run()`. The public `run()` method is synchronous. Designed for CLI scripts, Celery tasks, and Django views without async support. Both production machines always pass `rollup=False` internally.
- `**TestBench` – immutable fluent testing API.** A single entry point for testing actions across both async and sync machines. Supports `.with_user()`, `.with_mocks()`, `.with_runtime()`, etc., each returning a new immutable instance. Terminal methods (`run`, `run_aspect`, `run_summary`) accept a mandatory `rollup: bool` parameter (no default). Automatically resets mock state between the async and sync runs so that `assert_called_once_with()` works correctly.
- `**validate_state_for_aspect` and `validate_state_for_summary`.** Helper functions that verify that a manually provided `state` dictionary contains all required fields (according to checkers of preceding aspects) before executing a single aspect or summary in tests. Produces clear error messages indicating which aspect should have written which field.
- `**compare_results` for multi‑machine result comparison.** Compares results from async and sync machines, showing field‑level differences when results diverge. Used internally by `TestBench` and available for custom test assertions.
- **Context stub helpers.** `UserInfoStub`, `RuntimeInfoStub`, `RequestInfoStub`, `ContextStub` provide reasonable defaults for testing, reducing boilerplate.
- `**rollup` support in dependency resolution and connection managers.** The `rollup` flag now propagates through `ToolsBox.resolve()` and into connection managers. When `rollup=True`, any `SqlConnectionManager` will execute `rollback()` instead of `commit()`, enabling safe testing on production databases. Managers that do not support rollup raise `RollupNotSupportedError`.
- `**BaseResourceManager.check_rollup_support()`.** A new method that concrete managers can override to declare rollup support (default raises `RollupNotSupportedError`). `SqlConnectionManager` overrides it to return `True`.
- **Context field nodes in the coordinator graph.** `GraphCoordinator` now creates nodes of type `context_field` for every unique dot‑path requested by `@context_requires`. Edges of type `requires_context` connect aspect nodes (or error handler nodes) to these fields. This closes the last gap in the system graph, allowing full introspection of context dependencies.
- **Documentation of graph node key format.** Public methods `get_node()`, `get_children()`, `get_dependency_tree()` now have docstrings explaining the `"type:full_name"` key format, with examples for `context_field`, `action`, `domain`, etc.

### Changed

- `**BaseParams` and `BaseResult` now strictly require `Field(description=...)` for every field** (via `DescribedFieldsIntent`). Previously descriptions were optional; now a missing or empty description raises `TypeError` during metadata assembly. This ensures that all API parameters and results are self‑documented from the start.
- `**@on` decorator now accepts typed event classes instead of strings.** The old string‑based `event_type` and `action_filter` are removed. New signature: `@on(event_class, *, action_class=None, action_name_pattern=None, aspect_name_pattern=None, nest_level=None, domain=None, predicate=None, ignore_exceptions=True)`. Filter order follows cheapest‑first (`isinstance` → regex → predicate). Multiple `@on` decorators on the same method produce OR semantics.
- `**PluginEvent` replaced by a hierarchy of event classes.** `BasePluginEvent` → `GlobalLifecycleEvent` → `GlobalStartEvent`/`GlobalFinishEvent`, `AspectEvent` → `RegularAspectEvent` → `BeforeRegularAspectEvent`/`AfterRegularAspectEvent`, etc. Each class contains only the fields relevant to that event, eliminating the “bag of optional None” anti‑pattern.
- `**Plugin.get_handlers()` now filters by type (`isinstance`) instead of string matching.** The `event_name` string parameter is replaced by the event class itself.
- `**PluginRunContext.emit_event()` now accepts a concrete event object instead of a list of parameters.** The method applies the filter chain described above and executes matching handlers in parallel or sequentially depending on `ignore_exceptions` flags.
- `**ToolsBox` does not store `Context` on the instance.** Aspects cannot access execution context via `box` at all (including mangled attributes). `ContextView` from `@context_requires` is the only aspect-visible path to context data. `ScopedLogger` still receives `Context` for template substitution; nested runs use a machine closure that captures `Context` for `_run_internal`.
- `**ActionProductMachine.gate_coordinator` (read-only property).** Public access to the built `GraphCoordinator` for adapters, tooling, and tests. Prefer this over reading `machine._coordinator`.
- `**BaseAdapter` optional `gate_coordinator` (keyword-only) and `gate_coordinator` property.** Defaults to `machine.gate_coordinator`. `McpAdapter` and `FastApiAdapter` forward the same parameter. MCP graph JSON helpers take a `GraphCoordinator` directly instead of reaching into private machine fields.
- `**PluginEmitSupport` and coordinator decoupling.** `ActionProductMachine` builds a `PluginEmitSupport` instance (public `plugin_emit_support` property) for `base_fields` / `emit_extra_kwargs` used with `PluginRunContext.emit_event`. `SagaCoordinator` takes `PluginEmitSupport` instead of `LogCoordinator` and no longer receives the machine in `execute()`. `ErrorHandlerExecutor` takes `PluginEmitSupport` in its constructor and `handle()` no longer takes the machine as the first argument. Removed private `_base_event_fields` / `_build_plugin_emit_kwargs` from the machine (logic lives on `PluginEmitSupport`).
- `**DependencyFactoryResolver`, `ToolsBoxFactory`, and `AspectExecutor` without `_MachineLike`.** New protocol `DependencyFactoryResolver` with `dependency_factory_for(action_cls)`; `ActionProductMachine` implements it publicly. `ToolsBoxFactory` takes only `LogCoordinator` and `create(..., factory_resolver=..., mode=..., machine_class_name=..., ...)`. `AspectExecutor` is constructed with `log_coordinator`, `machine_class_name`, and `mode`; `call` / `execute_regular` / `execute_summary` no longer accept a machine-shaped first argument.
- `**BaseAction` generic parameters `P` and `R` are now bound to `BaseSchema` instead of `ReadableDataProtocol`.** This reflects the architectural shift: all data structures inherit `BaseSchema`.
- `**WritableMixin` and `WritableDataProtocol` removed.** After freezing `BaseState` and `BaseResult`, there are no remaining consumers of write‑able dict‑like access. The read‑only protocol `ReadableDataProtocol` remains for compatibility.
- `**CheckRoles` class removed; use `check_roles` function.** Old code: `@CheckRoles("admin", desc="...")` → new: `@check_roles("admin")`. The `desc` parameter is no longer accepted.
- **Checker decorators no longer accept a `description` parameter.** Use `@result_string("txn_id", required=True)` instead of `@result_string("txn_id", "Transaction ID", required=True)`.
- `**ResultFieldChecker.__init__` signature changed:** removed `description`, now only `field_name` and `required`. All checkers follow the same pattern.
- `**RoleMeta` and `CheckerMeta` dataclasses no longer contain a `description` field.** The `description` was dead code (never used) and has been removed from metadata.
- `**ActionProductMachine._check_action_roles()` now expects `ROLE_NONE` and `ROLE_ANY` as module‑level constants, not class attributes.**
- `**ActionProductMachine._call_aspect()` and `_handle_aspect_error()` now create `ContextView` and pass it as the last argument when `context_keys` is non‑empty.** The number of parameters in aspect methods is now validated based on the presence of `@context_requires` (5 without, 6 with).
- `**SyncActionProductMachine` moved from `core/` to its own file and made a proper subclass of `ActionProductMachine`.** Previously it was a separate class; now it inherits all pipeline logic and only overrides `run()` to be synchronous.
- `**ActionTestMachine` moved to `testing/async_test_machine.py` and renamed to `AsyncTestMachine`.** A corresponding `SyncTestMachine` was added. Both are instantiated by `TestBench`.
- `**MockAction` moved to `testing/mock_action.py`.** Its behaviour remains unchanged.

### Removed

- `**WritableMixin` and `WritableDataProtocol`.** Completely removed from the codebase. The framework no longer provides any dict‑like write interface for core data types.
- `**CheckRoles` class.** Replaced by `check_roles` function.
- `**regular_aspect` and `summary_aspect` no longer accept a `desc` parameter.** Description is now mandatory and passed as the first positional argument.
- `**PluginEvent` monolithic class.** Replaced by the typed event hierarchy.
- **String‑based event types in `@on`.** All subscriptions must use event classes.
- `**description` parameter from all result checker decorators.**
- `**ResultFieldChecker._build_meta()` inclusion of `description`.**
- **Dead code from `core/action_test_machine.py` and `core/mock_action.py` (moved).**
- `**extra="allow"` and `arbitrary_types_allowed=True` from `BaseResult`.** Results are now strictly typed and forbid extra fields.
- `**__setitem__`, `__delitem__`, `write`, `update` from `BaseState`.** The class is now fully immutable.
- `**ReadableDataProtocol` and `ReadableMixin` are still present** (not removed), but all references in docstrings have been updated to reflect that `BaseSchema` is the primary interface.

### Security

- **Access to private attributes in log templates is now blocked for any path segment, not only the last one.** This prevents bypassing the underscore rule via intermediate segments (`{%context._internal.public_key}`).

## [0.5.5] – 2026-03-31

### Added

- **ScopedLogger in plugin handlers.** All plugin handlers (`@on` methods) now receive a fourth parameter `log` — a `ScopedLogger` instance bound to the plugin's scope. The scope contains fields `machine`, `mode`, `plugin` (plugin class name), `action` (full action class name), `event` (event name such as `global_finish` or `before:validate`), and `nest_level` (call nesting depth). This enables plugins to log with full execution context using all five template namespaces (`{%scope.plugin}`, `{%var.count}`, `{%context.user.id}`, etc.). The handler signature is `async def handler(self, state, event, log)` — all four parameters are mandatory.
- **Nest level in logging scope and templates.** The `nest_level` field is now included in the `LogScope` for both aspects and plugin handlers. Developers can reference it in log templates via `{%scope.nest_level}` to display the current call depth. Root actions have `nest_level=1`, first-level child actions called via `box.run()` have `nest_level=2`, and so on. This makes it easy to trace nested action execution in log output and distinguish between parent and child action logs.
- **Configurable indentation in ConsoleLogger.** `ConsoleLogger` now accepts `use_indent` (bool, default `True`) and `indent_size` (int, default `2`) parameters. When `use_indent=True`, each log line is prefixed with `nest_level * indent_size` spaces, creating a visual hierarchy of nested action calls. When `use_indent=False`, all lines are printed without indentation — useful for production environments where logs are sent to ELK/Loki and indentation interferes with parsing. The indent is calculated from the `nest_level` passed through the logging pipeline.
- **Business domains (`BaseDomain`).** Introduced the `aoa.action_machine.domain` package with `BaseDomain` — an abstract base class for declaring typed business domains. Each domain is a class with a mandatory `name: ClassVar[str]` attribute, validated at class creation time via `__init_subclass__`. Domains serve as typed markers for grouping actions and resources by business area. Unlike string-based identifiers, class-based domains provide IDE autocompletion, import-time error detection for typos, and refactoring support. Domains appear as dedicated nodes in the GraphCoordinator graph with `belongs_to` edges from actions and resources.
- `**@meta` decorator for mandatory class descriptions.** Every Action (with aspects) and every ResourceManager must now have a `@meta(description="...", domain=...)` decorator. The `description` parameter is mandatory and must be a non-empty string. The `domain` parameter is optional and accepts a `BaseDomain` subclass. Two intent markers enforce this requirement: `ActionMetaIntent` (inherited by `BaseAction`) and `ResourceMetaIntent` (inherited by `BaseResourceManager`). MetadataBuilder raises `TypeError` if `@meta` is missing. The description and domain are stored in `ClassMetadata.meta` as a frozen `MetaInfo` dataclass and are used by adapters for OpenAPI summaries and MCP tool descriptions.
- **Domain nodes and `belongs_to` edges in the coordinator graph.** When `@meta` specifies a `domain`, GraphCoordinator creates a node of type `domain` and a `belongs_to` edge from the class to the domain. Domain nodes are idempotent — multiple actions in the same domain share a single node. Action and dependency node payloads are enriched with `description` and `domain` fields from `@meta`, making the graph self-documenting without requiring access to ClassMetadata.
- **Strict mode for GraphCoordinator.** `GraphCoordinator` now accepts a `strict: bool = False` parameter. When `strict=True`, the coordinator additionally validates that `domain` is specified in `@meta` for all Actions (with aspects) and ResourceManagers. If `domain=None` in strict mode, a `ValueError` is raised. The `description` field is always validated regardless of strict mode — it is an unconditional invariant. The coordinator is passed as a parameter to `ActionProductMachine`, not created internally, allowing easy configuration of strict mode for production deployments.
- **Pydantic-based `BaseParams` and `BaseResult`.** `BaseParams` now inherits from `pydantic.BaseModel` with `frozen=True`, providing immutable parameters with automatic type validation, constraints (`gt`, `min_length`, `pattern`), and JSON Schema generation via `model_json_schema()`. `BaseResult` inherits from `pydantic.BaseModel` with `extra="allow"`, supporting both declared fields and dynamic extra fields written through `WritableMixin`. Both classes retain full `ReadableMixin` compatibility (`resolve()`, `keys()`, `values()`, `items()`, `__getitem__`). `BaseState` remains a plain class — it is not converted to Pydantic because its fields are dynamic and determined at runtime.
- `**DescribedFieldsIntent` for mandatory field descriptions.** A marker mixin inherited by `BaseParams` and `BaseResult`. MetadataBuilder validates that every Pydantic field in classes inheriting this mixin has a non-empty `description` in `Field(description="...")`. Fields without descriptions raise `TypeError` at metadata assembly time, ensuring that all API parameters and results are self-documented from the start.
- `**FieldDescriptionMeta` in `ClassMetadata`.** A new frozen dataclass capturing field-level metadata: `field_name`, `field_type`, `description`, `examples`, `constraints` (gt, ge, min_length, max_length, pattern, etc.), `required`, and `default`. ClassMetadata now includes `params_fields` and `result_fields` tuples, populated by collectors that extract generic parameters P and R from `BaseAction[P, R]` and read Pydantic `model_fields`. Adapters use these tuples to generate OpenAPI schemas and MCP inputSchemas without any manual configuration.
- **Base adapter infrastructure (`BaseAdapter`, `BaseRouteRecord`).** `BaseAdapter[R]` is an abstract generic class providing the fluent registration pattern (`_add_route` returns `self`) and abstract `build()` method. `BaseRouteRecord` is an abstract frozen dataclass storing route configuration with automatic extraction of `params_type` and `result_type` from `BaseAction[P, R]` generic parameters via `extract_action_types()`. Mapper invariants are enforced at creation time: `params_mapper` is required when `request_model` differs from `params_type`, and `response_mapper` is required when `response_model` differs from `result_type`. BaseRouteRecord cannot be instantiated directly — only concrete subclasses.
- **FastAPI adapter (`FastApiAdapter`).** Transforms Actions into HTTP endpoints. Protocol methods `post()`, `get()`, `put()`, `delete()`, `patch()` register routes with fluent chaining. `build()` creates a `FastAPI` application with automatic OpenAPI documentation generated from Pydantic Field descriptions, constraints, and examples. Three endpoint generation strategies handle body-based methods (POST/PUT/PATCH), query-based methods (GET/DELETE with path and query parameters), and empty-params methods. Exception handlers map `AuthorizationError` to HTTP 403, `ValidationFieldError` to HTTP 422, and unhandled exceptions to HTTP 500. A `GET /health` endpoint is added automatically.
- **MCP adapter (`McpAdapter`).** Transforms Actions into MCP tools for AI agents (Claude, ChatGPT, Cursor). The `tool()` method registers individual tools; `register_all()` automatically registers all Actions from the coordinator using snake_case names (e.g., `CreateOrderAction` → `create_order`). `build()` creates an MCP server with `inputSchema` auto-generated from Pydantic models and descriptions from `@meta`. Error mapping returns `PERMISSION_DENIED`, `INVALID_PARAMS`, or `INTERNAL_ERROR` as text content. A `system://graph` resource exposes the full system architecture as JSON with nodes (actions, domains, dependencies) and edges (depends, belongs_to, connection).
- **Mandatory `auth_coordinator` in all adapters.** The `auth_coordinator` parameter in `BaseAdapter` and all concrete adapters is a required positional argument. Passing `None` raises `TypeError` with a clear message suggesting `NoAuthCoordinator()` for open APIs. `NoAuthCoordinator` implements the same interface as `AuthCoordinator` — an async `process()` method returning `Context` — but always returns an anonymous context with `user_id=None` and empty roles. This ensures developers cannot accidentally forget authentication; they must explicitly declare the absence of it.
- **Fluent chain API for adapters.** All protocol methods (`post`, `get`, `put`, `delete`, `patch`, `tool`) return `self`, enabling chained registration: `app = adapter.post("/a", A).get("/b", B).build()`. The `_add_route()` method in `BaseAdapter` returns `Self` to support this pattern.
- **Unified example service (`fastapi_mcp_services`).** A single example package demonstrates the same three Actions (PingAction, CreateOrderAction, GetOrderAction) served simultaneously via FastAPI HTTP endpoints and MCP tools. Shared infrastructure (GraphCoordinator, ActionProductMachine, NoAuthCoordinator) is defined once in `infrastructure.py`. Actions use nested Params/Result classes with forward references. Domains (OrdersDomain, SystemDomain) group actions by business area.

## [0.4.5] – 2026-03-28

### Added

- `**metadata` subpackage for structured metadata assembly.** Extracted `MetadataBuilder` from monolithic `core/metadata_builder.py` into a dedicated subpackage `action_machine/metadata/` with four focused modules. `builder.py` contains the `MetadataBuilder` class with a single public method `build(cls)` serving as the only entry point. `collectors.py` provides eight collector functions that read temporary decorator attributes from classes and methods — roles, dependencies, connections, aspects, checkers, subscriptions, sensitive fields, and dependency bound types. `validators.py` contains structural validation functions enforcing invariants that span multiple decorators, such as at most one summary aspect, summary must be declared last, and checkers must reference existing aspects. `cleanup.py` provides `cleanup_temporary_attributes()` for explicit removal of decorator artifacts when needed.
- **Idempotent metadata building.** `MetadataBuilder.build()` no longer auto-cleans temporary attributes from classes. Classes defined at module level are shared across tests and multiple `GraphCoordinator` instances, so auto-cleaning caused data loss on subsequent builds. The builder is now fully idempotent — repeated calls on the same class return equivalent `ClassMetadata` objects. Explicit cleanup remains available via `cleanup_temporary_attributes()` for special scenarios.
- **Comprehensive `_extract_bound` test coverage.** Added exhaustive tests for `DependencyIntent` generic bound type extraction across all inheritance scenarios: explicit bound specification, missing bound fallback to `object`, three-level and four-level inheritance chains, multiple inheritance with mixins, `TypeVar` fallback, bound override in child classes, and diamond inheritance patterns.

## [0.4.0] – 2026-03-21

### Added

- **Intent-based aspect architecture (`AspectIntent`).** Introduced `AspectIntent` as a marker mixin for classes that support `@regular_aspect` and `@summary_aspect` decorators. Decorators write `_new_aspect_meta` metadata directly to methods. `MetadataBuilder` scans MRO to collect aspects into `ClassMetadata.aspects`. This replaces the previous magic-based aspect collection with an explicit, type-safe system where aspects are discovered through decorator metadata rather than method name conventions.
- `**ToolsBox` — unified container for aspect tools.** A single object passed to every aspect as the `box` parameter, replacing the previous separate `deps` and `log` parameters. Provides `resolve(cls)` for dependency injection (checking external resources first, then the factory), `info/warning/error/debug` for logging with automatic scope enrichment (machine, mode, action, aspect), and `run(action_class, params, connections)` for launching child actions with automatic connection wrapping to prevent nested transaction control. Reduces aspect parameter count from 5 to 4: `(params, state, box, connections)`.
- **Explicit nesting level tracking.** Removed the global `_nest_level` field from `ActionProductMachine`. Nesting depth is now passed explicitly as `nested_level` through `_run_internal` and stored inside `ToolsBox`. Each child action increments the level, and the value is accessible via `box.nested_level`. This eliminates shared mutable state between concurrent requests and makes the nesting depth available to logging and plugins.
- `**ActionTestMachine` external resource injection.** The test machine now accepts prepared mocks as `resources` in `_run_internal`, making them available throughout the execution pipeline including child actions. When `ToolsBox.resolve()` is called, it checks `resources` first (returning the mock) before falling back to the dependency factory.
- `**RuntimeInfo` (renamed from `EnvironmentInfo`).** The context component storing runtime information (hostname, service name, version, container ID) is now named `RuntimeInfo` to better reflect its purpose. The context attribute is `context.runtime` instead of the previous `context.environment`.

## [0.3.5] – 2026-03-19

### Added

- `**debug()` function for object introspection in log templates.** Returns a formatted multi-line string listing all public fields and properties of any object, including their types and values. For properties decorated with `@sensitive`, the masking configuration is shown. Output is non-recursive by default (`max_depth=1`) to avoid cluttering logs — to inspect nested objects, call `debug` on the nested attribute directly. Available inside `iif` expressions: `{iif(1==1; debug(obj); '')}`.
- `**exists()` function for safe variable presence checks.** `exists('variable.name')` returns `True` if the variable is defined in the current evaluation context, `False` otherwise. Useful for conditional logging when a variable may not be present: `{iif(exists('var.user'); debug(var.user); 'No user')}`. Works both inside `iif` conditions and as a standalone expression evaluating to the string `"True"` or `"False"`.
- **Color filters in log templates.** ANSI colors can be applied to any substituted value using pipe syntax outside `iif` (`{%var.amount|red}`) or color functions inside `iif` (`red('text')`). Supports foreground colors (`red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `grey`, `orange` and bright variants), background colors (prefixed with `bg_`), and combinations (`{%var.text|red_on_blue}`). The coordinator strips ANSI codes for loggers that declare `supports_colors=False`.
- `**@sensitive` decorator for data masking in logs.** Applied to property getters, it causes the value to be partially masked when substituted in log templates. Configurable via `max_chars` (visible characters from start), `char` (replacement character), and `max_percent` (maximum visible percentage). Example: `@sensitive(max_chars=3)` on an email property makes `{%context.user.email}` output `max`***** instead of the full address.
- **Strict underscore rule in log templates.** Any template variable whose last path segment starts with underscore raises `LogTemplateError` immediately. This prevents accidental logging of private or protected fields. Developers must expose data through public properties if it needs to appear in logs.
- **Asynchronous plugin initialization.** `Plugin.get_initial_state()` is now an `async` method, allowing plugins to perform I/O operations (database queries, API calls) during state initialization without blocking the event loop. The `PluginCoordinator` awaits each plugin's initialization directly instead of using `run_in_executor`.
- **Context as a per-request parameter.** `context` is now passed directly to `machine.run(context, action, params, connections)` instead of being stored in the machine constructor. This reflects the architectural reality that the machine is a long-lived singleton while each request carries its own context containing user identity, request metadata, and runtime information. All internal methods receive `context` as an explicit argument.

## [0.3.0] – 2026-03-19

### Added

- **Cross-cutting logging via `ScopedLogger`.** Every aspect now receives a `log` parameter — a `ScopedLogger` instance that automatically enriches log messages with execution context. The scope includes `machine` (machine class name), `mode` (execution mode), `action` (full action class name), and `aspect` (method name). Logging level is added automatically as the `level` key in the `var` namespace. User data is passed via `**kwargs` and appears in `var`. Templates can reference all scope fields: `[{%scope.machine}.{%scope.action}] Processing {%var.amount}`.
- `**mode` parameter in machine constructors.** `ActionProductMachine` requires a mandatory non-empty string `mode` (e.g., `"production"`, `"staging"`). `ActionTestMachine` defaults to `mode="test"`. The mode value is included in every `LogScope`, enabling filtering of logs by environment and distinguishing production from test output.
- **Level-based coloring in `ConsoleLogger`.** Messages are automatically colored based on logging level: `info` — green, `warning` — yellow, `error` — red, `debug` — gray. The level is extracted from the `var["level"]` field set by `ScopedLogger`. Unresolved variable markers are colored red for immediate visibility.

## [0.2.5] – 2026-03-18

### Added

- **PEP 8 file naming convention.** All 18 source files renamed from PascalCase to snake_case (`AuthCoordinator.py` → `auth_coordinator.py`, `ConsoleLogger.py` → `console_logger.py`, etc.). This resolves ruff N999 errors and aligns the project with Python community standards.
- **Centralized linter configuration.** All ruff, pylint, and mypy settings consolidated in `pyproject.toml` with documented reasons for each disabled rule. Added `lint-fix` and `pre-commit` taskipy commands for automatic formatting. Achieved pylint 10.00/10, zero mypy errors, zero vulture warnings.

## [0.2.0] – 2026-03-17

### Added

- **Conditional logic in log templates (`iif`).** Added `{iif(condition; true_value; false_value)}` construct for dynamic text in log messages. Conditions are evaluated safely via the `simpleeval` library — no access to file system or network. Supports comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`), logical operators (`and`, `or`, `not`), arithmetic (`+`, `-`, `*`, `/`), and built-in functions (`len`, `upper`, `lower`, `format_number`). Variables from all five namespaces are substituted as literals before evaluation, and invalid expressions raise `LogTemplateError` immediately.
- `**VariableSubstitutor` — extracted substitution engine.** All variable resolution and `iif` processing logic moved from `LogCoordinator` into a dedicated `VariableSubstitutor` class. The coordinator now only delegates substitution and broadcasts results to loggers. Supports five namespaces: `{%var.*}`, `{%context.*}`, `{%params.*}`, `{%state.*}`, `{%scope.*}`. Each namespace resolves through dot-path traversal supporting nested objects via `ReadableMixin`, plain dictionaries, and generic `getattr` fallback.
- `**PluginCoordinator` — extracted plugin management.** Plugin lifecycle management (state initialization, handler discovery, concurrent execution) moved from `ActionProductMachine` into a separate stateless `PluginCoordinator`. The coordinator creates isolated `PluginRunContext` for each `run()` call, ensuring complete state isolation between requests. Supports two execution strategies: parallel (`asyncio.gather`) when all handlers have `ignore_exceptions=True`, and sequential when any handler requires strict error propagation.
- **Connection validation chain.** The monolithic `_check_connections` method in `ActionProductMachine` decomposed into four focused validators, each checking one invariant: no declarations but connections passed, declarations but no connections, extra keys, and missing keys. A fifth validator checks that each value is an instance of `BaseResourceManager`. The main method calls validators in sequence with clear error messages.

## [0.1.5] – 2026-03-16

### Added

- **Unified data access protocols (`ReadableDataProtocol`, `WritableDataProtocol`).** Runtime-checkable protocols defining dict-like interfaces for reading (`__getitem`_*, `get`, `keys`, `values`, `items`, `__contains_`*) and writing (`__setitem__`). Any object implementing these methods can serve as `Params`, `Result`, or plugin state, enabling the use of TypedDict, Pydantic models, and custom classes without framework-specific base classes.
- `**ReadableMixin` and `WritableMixin`.** Mixins that automatically implement the data protocols via `getattr`/`setattr`/`vars()`. Adding `ReadableMixin` to any class gives it dict-like read access; adding `WritableMixin` gives write access with optional key validation via `write(key, value, allowed_keys)`. Used by `BaseParams`, `BaseResult`, `BaseState`, `Context`, `UserInfo`, `RequestInfo`, `RuntimeInfo`.
- `**resolve()` method for dot-path navigation.** `ReadableMixin` provides `resolve("user.roles")` for traversing nested objects through a chain of keys separated by dots. Supports three navigation strategies: `ReadableMixin` objects (via `__getitem__`), plain dictionaries (via key access), and generic objects (via `getattr`). Results are cached lazily in `_resolve_cache`, compatible with frozen Pydantic models via `object.__setattr__`.
- **Asynchronous authentication pipeline.** `CredentialExtractor`, `Authenticator`, `ContextAssembler`, and `AuthCoordinator` — all methods are `async def`, enabling I/O operations (token verification, database lookups) without blocking the event loop. `AuthCoordinator.process()` orchestrates the three-step pipeline: extract credentials, authenticate user, assemble request metadata into `Context`.
- **Dict-like access for context components.** `UserInfo`, `RequestInfo`, and `RuntimeInfo` inherit `ReadableMixin`, enabling access as `user["user_id"]`, `request["trace_id"]`, `runtime["hostname"]` in addition to attribute access. This unifies data access patterns across plugins, logging templates, and business logic.

## [0.1.0] – 2026-03-15

### Added

- **Action-Oriented Architecture (AOA) core.** Actions are atomic business operations consisting of a linear sequence of aspects (processing steps). Each action is a class inheriting `BaseAction[P, R]` where `P` is the params type and `R` is the result type. Aspects are async methods decorated with `@regular_aspect` (intermediate steps returning dict) and `@summary_aspect` (final step returning Result). The machine executes aspects sequentially, merging intermediate results into shared state.
- **Declarative dependency injection (`@depends`).** Actions declare dependencies on external services via class-level decorators: `@depends(PaymentService)`. Dependencies are resolved at runtime through `DependencyFactory` — each `resolve()` call creates a new instance via the factory function or default constructor. Singleton pattern is supported through lambda closures: `@depends(Service, factory=lambda: shared_instance)`. A generic bound `DependencyIntent[T]` restricts which types are allowed as dependencies.
- **Connection management (`@connection`).** Actions declare required resource managers (database connections, caches, queues) via `@connection(PostgresManager, key="db")`. The machine validates that passed connections exactly match declared keys — extra keys, missing keys, and non-`BaseResourceManager` values are rejected with descriptive errors. `WrapperSqlConnectionManager` wraps connections passed to child actions, preventing nested transaction control (open/commit/rollback) while allowing query execution.
- `**ActionProductMachine` — production execution engine.** Fully async machine that orchestrates action execution: role checking via `@CheckRoles`, connection validation, dependency factory creation via `GraphCoordinator`, sequential aspect execution with checker validation, plugin event emission, and nested action support. Stateless between requests — all per-request data flows through explicit parameters.
- `**ActionTestMachine` — test execution engine with mocking.** Accepts a `mocks` dictionary mapping dependency types to mock values. Supports four mock formats: `MockAction` instances, `BaseAction` instances (executed through full pipeline), `BaseResult` instances (wrapped in `MockAction`), and callables (wrapped as `side_effect`). Provides `run_with_context()` returning both result and `PluginRunContext` for asserting plugin states in tests.
- **Plugin system (`Plugin`, `@on`, `PluginCoordinator`).** Plugins subscribe to machine events (`global_start`, `global_finish`, `before:{aspect}`, `after:{aspect}`) via `@on` decorators with regex-based action filtering. Each `run()` call creates an isolated `PluginRunContext` with per-plugin state initialized via `get_initial_state()`. Plugin handlers receive `(self, state, event, log)` and return updated state. `ignore_exceptions` controls whether handler errors propagate or are silently absorbed.
- **Role-based access control (`@CheckRoles`).** Mandatory decorator for every action. Supports four modes: `CheckRoles.NONE` (no authentication required), `CheckRoles.ANY` (any authenticated user), a single role string (`"admin"`), or a list of roles (`["admin", "manager"]`). The machine compares the role spec against `context.user.roles` and raises `AuthorizationError` on mismatch.
- **Result field checkers.** Validation decorators applied to aspect methods: `ResultStringChecker`, `ResultIntChecker`, `ResultFloatChecker`, `ResultBoolChecker`, `ResultDateChecker`, `ResultInstanceChecker`. Each checker validates field presence, type, and constraints (min/max length, value range, date format, instance type). Aspects returning non-empty dicts must have checkers for all returned fields — undeclared fields cause `ValidationFieldError`.
- `**GraphCoordinator` — central metadata and graph registry.** Lazily builds and caches `ClassMetadata` for any class on first access. Recursively discovers dependencies and connections. Maintains a directed acyclic graph (rustworkx `PyDiGraph`) with nodes for actions, dependencies, connections, aspects, checkers, plugins, subscriptions, sensitive fields, roles, and domains. Detects cyclic dependencies via `is_directed_acyclic_graph()` after each edge addition.
- **Logging subsystem.** `LogCoordinator` broadcasts messages to registered `BaseLogger` instances. `ConsoleLogger` outputs to stdout with configurable colors and indentation. `VariableSubstitutor` resolves five namespaces (`var`, `state`, `params`, `context`, `scope`) with dot-path traversal. `ExpressionEvaluator` handles `{iif(condition; true; false)}` via `simpleeval`. `@sensitive` decorator masks property values in logs. Strict error policy: invalid templates raise `LogTemplateError` immediately.
- **Exception hierarchy.** `AuthorizationError` (role mismatch), `ValidationFieldError` (checker failure), `HandleError` (resource manager errors), `TransactionError` (base for connection errors), `ConnectionAlreadyOpenError`, `ConnectionNotOpenError`, `TransactionProhibitedError` (wrapper prevents nested transactions), `ConnectionValidationError` (key mismatch), `LogTemplateError` (invalid template syntax), `CyclicDependencyError` (graph cycle detected).
