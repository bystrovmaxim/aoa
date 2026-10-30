# Open a service's graph history in Maxitor

A service's graph is a file in its repository, so the file's git history is the graph's history. With [`repo-graph-port`](run-the-repo-graph-port.md) serving that history, Maxitor opens it from one address and shows any version on a time axis: every change that reached the branch, the pull requests still open that would change it, and Live — the service running now.

[16_open_a_history.py](../../examples/step_26_maxitor/16_open_a_history.py) ([notebook](../../examples/step_26_maxitor/16_open_a_history.ipynb)) runs every case below against a real port and prints what Maxitor answers.

## Open a history

Paste one of three addresses into the **AOA Service URL** field:

| You have | Paste | Key |
|---|---|---|
| a private history on a port | `https://repo-graph-port.example.com/api/v1/history/orders#key=<key>` | after `#key=`; the owner of the port gives it to you |
| a public repository | `https://github.com/owner/repo/blob/main/graph.json` | none; read through Maxitor's own port (`MAXITOR_PUBLIC_PORT`) |
| a running service, no history | `https://orders.example.com` | none |

Maxitor tells a history from a service by the answer, never by the host name. Recent remembers each address with what it turned out to be — a clock for a history, waves for a service — and shows a key as eight dots; the eye reveals it.

## What the screen shows

| The history has | Version button | Opens on | The picker |
|---|---|---|---|
| Live and several versions | `◷ Live ▾` | Live | the versions, then Live |
| several versions, no Live | `◷ 0.11.0 · #147 ▾` | the newest version | the versions |
| one version | `◷ #12 ▾` | it | one point |
| Live, no version yet | `◷ Live ▾` | Live | Live alone |
| nothing yet | none | — | the workspace says "This history has no version yet." |
| (a running service) | none | its graph | — |

The version button sits at the left of the row above the diagram; a click opens the picker under it, another click closes it. The picker is not modal: the sidebar keeps working, and a click on the diagram or Escape closes it.

## Read the track

The **i** in the picker's head shows this legend on the screen.

**Points.** Each point is a change that reached the branch and changed the graph, oldest at the left. Its colour says how it came, the same on the track, in its card and in the legend:

| Point | Colour | Meaning |
|---|---|---|
| Direct push | grey | pushed straight to the branch, with no pull request |
| Merged | purple | a merged pull request |
| Review required | brown-yellow | a pull request still open, no reviewer has answered yet |
| Approved | green | a pull request still open, approved: it can be merged |
| Changes requested | red | a pull request still open, a reviewer asked to fix it |
| Live | hollow grey, always last | what the service runs now |

The open pull requests stand after the history and before Live, past a dashed line; drafts are not shown. Each stretch of the line takes the colour of the point it leads to.

**Versions and releases.** A point with its own version tag (`v0.8.0`) starts a version: it is larger and its number stands under it. The points after it, up to the next version, belong to it and stay unnamed. Nothing else is named under the track — no dates. A flag above a point marks a release: the tag is published as a GitHub Release, or a tag is named `release…` (`release-1.4`, `release/2026-10-30`), which works without GitHub. A history with no version tags shows its points and nothing under them.

**The chosen point** keeps its colour and carries its name in a chip: `0.11.0 · #147` — its version and pull request — or `#147` without a version, or `#57`, its place in the history, when it had no pull request.

**Live as the newest version.** When the service runs exactly the newest version's graph, the two are one point: Live, with that version's card and message.

**A point's card**, on hover, under the track: how it came (Merged, Direct push or the open pull request's state), its version and Release chips, its number and when, its title, who made it and who merged it, its size in lines and files, and what it did to the graph — nodes added and removed by kind, nodes changed, links added and removed.

**Move along it.** Click a point, or ← → for one step, Home and End for the ends. A long history scrolls like a page: a sideways swipe, the mouse wheel, or a drag; the right edge says how many points are out of view. A chosen point scrolled away stays pinned to its edge; a click brings it back.

**The message.** Under the track: the chosen version's pull request description, or its commit message, line breaks kept; addresses and `#123` are links. Live has no message of its own: a line says when it was last checked.

## Share what you see

The browser's address bar is the link: it holds the history, the chosen version (`b=`) and, for a private history, the key after `#key=`. Copy it as it is to open the same history at the same version elsewhere. What follows `#` never reaches a server, so the key is in no server's log; it is visible in the address bar and in the browser's history.

**Open room** shares the view live: everyone in a room sees the same version, and the last one picked wins.

## When Maxitor refuses

| You see | Why |
|---|---|
| `not found` | a wrong, revoked or expired key, an unknown history, or no key for a private one — the same answer for each, so nothing is given away |
| `Too many wrong keys for this history; try again in a minute` | the port blocked this client after ten wrong keys in a minute |
| `The history cannot be read now.` | the port does not answer |
| `Public histories are not set up on this Maxitor` | a public link, but Maxitor has no port of its own |
| the reason instead of a diagram | the chosen version's file is not a valid graph; the point is hollow and red |

## What the port gives Maxitor

Everything on the card comes from git, so it works for a local or corporate repository with no host to ask:

- a version's pull request — from GitHub, or from its merge commit's message (`Merge pull request #N from …`) or a squash commit's first line (`Title (#N)`);
- who made it — the authors of the merged branch — and who merged it — the merge commit's author;
- its size against its first parent, and what it did to the previous version's graph;
- the open pull requests: on GitHub with their review state, drafts left out; in a local repository, each `refs/pull/<n>/head` not yet in the branch.

[Running the repo-graph-port](run-the-repo-graph-port.md) shows how to set one up.
