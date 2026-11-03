# Open a service's graph history in Maxitor

A service's graph is a file in its repository, so the file's git history is the graph's history. With [`repo-graph-port`](run-the-repo-graph-port.md) serving that history, Maxitor opens it from one address and shows any version on a time axis: every change that reached the branch, the pull requests still open that would change it, and Live — the service running now.

[16_open_a_history.py](../../examples/step_29_maxitor/16_open_a_history.py) ([notebook](../../examples/step_29_maxitor/16_open_a_history.ipynb)) runs every case below against a real port and prints what Maxitor answers.

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

**The history's name.** A public history is named after the folder that holds its graph file, the repository at the root; a private one, after its id. The same name heads the picker, titles the tab and stands in Recent:

| Link to | Name | Full path |
|---|---|---|
| `…/aoa/blob/main/packages/aoa-demo/graph.json` | `aoa-demo` | `bystrovmaxim/aoa/packages/aoa-demo` |
| `…/aoa/blob/main/packages/maxitor/maxitor-web/graph.json` | `web` | `bystrovmaxim/aoa/packages/maxitor/maxitor-web` |
| `…/gameoffer/blob/main/graph.json` | `gameoffer` | `bystrovmaxim/gameoffer` |

Rest on the name in the picker to read its full path, which tells apart two folders of one name; click it, or press Enter on it, to copy that path.

## Read the track

The **i** in the picker's head shows this legend on the screen.

**Points.** Each point is a change that reached the branch, oldest at the left. A large point changed the graph. A small point changed only the version, and appears only where a history names its version file. Its colour says how it came, the same on the track, in its card and in the legend:

| Point | Colour | Meaning |
|---|---|---|
| Direct push | grey | pushed straight to the branch, with no pull request |
| Merged | purple | a merged pull request |
| Review required | brown-yellow | a pull request still open, no reviewer has answered yet |
| Approved | green | a pull request still open, approved: it can be merged |
| Changes requested | red | a pull request still open, a reviewer asked to fix it |
| Live | hollow grey, always last | what the service runs now |

The open pull requests stand after the history and before Live, past a dashed line; drafts are not shown. An open pull request is followed by its number: when it is merged, a comparison standing on it moves to its merge and says `#378 was merged`; given new commits, to its new head with `#378 was updated`; closed or made a draft, it moves to the nearest point and says `#378 was closed or became a draft`. One that raises only the version, not the graph, is a small point, as it will be once merged. Each stretch of the line takes the colour of the point it leads to.

**Versions and releases.** A history with a version file takes its numbers from that file: a number stands under a point where the version rose, and it takes only the tags of its own versions, so another package's release in the same repository is no flag on it. With no version file, numbers come from tags: a point with its own version tag (`v0.8.0`) has its number under it, and the points after it, up to the next version, belong to it and stay unnamed. Nothing else is named under the track — no dates. A flag above a point marks a release: its tag is published as a GitHub Release. A tag is never a release by its name alone, so a tag such as `release-1.4` with no GitHub Release stays only in the point's card. A history with no version tags shows its points and nothing under them.

**Hiding the small points.** The icon of three points on a line, beside the "i", shows and hides the points that did not change the graph. It is coloured while they are shown and grey while they are hidden, and it appears only where there is something to hide. It is your own setting: it stays in this browser, and it never reaches a room or a link. What you chose stays chosen, and a chosen small point stays on the track until you choose another. The flags of hidden points stand on the nearest point before them, and that point's card lists them.

**Two versions with one graph.** Compared, they say `Both versions have the same graph.` in the picker and `no changes` on the button. The left panel, narrowed to what changed, stands empty with `No changes`.

**A version that cannot be read.** A wrong path or a broken file does not cost you the graph. A dot on the version button and a line at the foot of the picker say what the track shows and why. When no version could be read, the track shows only the commits that changed the graph, with no numbers.

**A new version while you look.** A version or an open pull request that reaches the history changes nothing on screen: the version, the diagram, the filters, the zoom and the position stay. A blue dot on the version button says it is there, with no count, until you open the picker. Reload asks for the list at once and keeps the zoom and position too.

**The chosen point** keeps its colour and carries its name in a chip: `0.11.0 · #147` — its version and pull request — or `#147` without a version, or `#57`, its place in the history, when it had no pull request.

**Live as the newest version.** When the service runs exactly the newest version's graph, the two are one point: Live, with that version's card and message.

**A point's card**, on hover, under the track: how it came (Merged, Direct push or the open pull request's state), its version and Release chips, its number and when, its title, who made it and who merged it, its size in lines and files, and what it did to the graph — nodes added and removed by kind, nodes changed, links added and removed.

**Move along it.** Click a point, or ← → for one step, Home and End for the ends. A long history scrolls like a page: a sideways swipe, the mouse wheel, or a drag; the right edge says how many points are out of view. A chosen point scrolled away stays pinned to its edge; a click brings it back.

**The message.** Under the track: the chosen version's pull request description, or its commit message, line breaks kept; addresses and `#123` are links. Live has no message of its own: a line says when it was last checked.

## Join a public link with its version file

A public history can name its version file in the link's query, with the key when the file is not a `version.toml`:

```text
https://github.com/owner/repo/blob/main/graph.json?version_link=https%3A%2F%2Fgithub.com%2Fowner%2Frepo%2Fblob%2Fmain%2Fpyproject.toml&version_key=project.version
```

The file must be in the same repository and on the same branch. Any other query is refused, and so is `version_key=` with no `version_link=`. The same graph joined with another file is another history.

## Try it on the demo

The demo of this repository has a real history, made of ordinary pull requests, each telling what it changed. Paste this link into **AOA Service URL**:

```text
https://github.com/bystrovmaxim/aoa/blob/main/packages/aoa-demo/graph.json?version_link=https%3A%2F%2Fgithub.com%2Fbystrovmaxim%2Faoa%2Fblob%2Fmain%2Fpackages%2Faoa-demo%2Fpyproject.toml&version_key=project.version
```

| Compare | What you see |
|---|---|
| 3.2.0 → 3.3.0 | one field added, and nothing else |
| 3.3.0 → 3.4.0 | a table, its relations, a lifecycle and an action added together |
| 3.4.0 → 3.5.0 | a field's type and description changed, a transition added |
| 3.5.0 → 3.6.0 | an action changed only inside: its card lists the new parts |
| 3.6.0 → 3.7.0 | a new domain, a role link changed, a field removed elsewhere; 3.7.0 carries a release flag |
| 3.7.0 → 3.8.0 | a relation pointing at another table, a relation removed, a state added |
| 3.8.0 → 3.9.0 | a table moved to another domain, a state removed |
| 3.9.0 → 3.9.1 | a small point: the version rose, the graph did not |
| 3.9.1 → 3.10.0 | a role and an action removed, a transition removed |
| 3.10.0 → 3.11.0 | a domain removed whole, a lifecycle removed |
| 3.11.0 → 3.14.0 | two more releases, a new table, role and action, states added |
| 3.14.0 → 3.15.0 | a field and a final state added to the return's lifecycle |

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
| `A public history's link takes only one 'version_link=' and one 'version_key=' in its query.` | a public link with any other query |
| `'version_key=' names a key of the file in 'version_link=', so it needs one.` | a key with no file |
| the reason instead of a diagram | the chosen version's file is not a valid graph; the point is hollow and red |

## What the port gives Maxitor

Everything on the card comes from git, so it works for a local or corporate repository with no host to ask:

- a version's pull request — from GitHub, or from its merge commit's message (`Merge pull request #N from …`) or a squash commit's first line (`Title (#N)`);
- who made it — the authors of the merged branch — and who merged it — the merge commit's author;
- its size against its first parent, and what it did to the previous version's graph;
- the open pull requests: on GitHub with their review state, drafts left out; in a local repository, each `refs/pull/<n>/head` not yet in the branch.

[Running the repo-graph-port](run-the-repo-graph-port.md) shows how to set one up.
