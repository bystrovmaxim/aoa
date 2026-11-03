# Feature Specification: A history named after what was opened

**Feature Branch**: `feature/issue-394-history-name`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #394, "Maxitor: name a history after the project, package or module that was opened, not the repository".

## Overview

A **public history** is opened from a link to a graph file on GitHub. Maxitor names that history after the repository the file lives in: `bystrovmaxim/aoa`. One repository can hold many graph files, one per package or component, and today every one of them is called the same name.

After this change, a history is named after the folder that holds its graph file. Nothing else is read: the folder is in the link, exists for every language and tool, and cannot drift from the code the way a name copied into a file can.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the name of what was opened (Priority: P1)

A reader opens the link to `packages/maxitor/web/graph.json`. The version picker calls the history `web`. Hovering the name shows its full path, `bystrovmaxim/aoa/packages/maxitor/web`; clicking the name copies that path to the clipboard.

**Why this priority**: It is the whole issue: a reader who opened two graphs of one repository cannot tell them apart.

**Independent Test**: Open the three graph files of this repository one after another; each history carries its own name, and hovering each name shows its own full path.

**Acceptance Scenarios**:

1. **Given** the link to `packages/aoa-demo/graph.json`, **When** it is opened, **Then** the history is called `aoa-demo` and hovering the name shows `bystrovmaxim/aoa/packages/aoa-demo`.
2. **Given** the link to `packages/maxitor/tools/repo_graph_port/graph.json`, **When** it is opened, **Then** the history is called `repo_graph_port`.
3. **Given** the link to a `graph.json` at the root of the repository `bystrovmaxim/gameoffer`, **When** it is opened, **Then** the history is called `gameoffer` and its full path is `bystrovmaxim/gameoffer`.

---

### User Story 2 - The name is the same everywhere (Priority: P2)

Wherever Maxitor names an open history — the version picker, the browser tab, the list of recent histories, its own log lines — it uses one name.

**Why this priority**: A name that changes from one corner of the screen to the other is no name.

**Independent Test**: Open one history and read its name in each of those places; they match.

**Acceptance Scenarios**:

1. **Given** an open history named `aoa-demo`, **When** the reader looks at the tab, the picker and the recent list, **Then** each says `aoa-demo`.
2. **Given** two histories of one repository opened side by side, **When** both are shown, **Then** they carry different names.
3. **Given** the picker of the history `web`, **When** the reader clicks the name, **Then** the clipboard holds `bystrovmaxim/aoa/packages/maxitor/web` and the picker says, for a moment, that the path was copied.

### Edge Cases

- Two graph files in folders of one name (`a/web/graph.json` and `b/web/graph.json`): both histories are called `web`; their full paths differ and are shown on hover.
- The link joins a version file (`version_link`): the name still comes from the graph file's folder, not the version file's.
- A link that points to a branch, a tag or a commit: the name is the same, since the folder is the same.
- A **private history** (opened by its id from a port) is called by its id, as today, and its full path is its address without the key.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The name of a public history MUST be the name of the folder that holds its graph file; a graph file at the repository's root MUST take the repository's name.
- **FR-002**: A public history MUST carry its full path: `owner/repo` followed by the path of the graph file's folder (`owner/repo` alone at the root). The version picker MUST show the full path when the name is hovered or focused, and MUST NOT show it as a line of its own.
- **FR-006**: Clicking the name in the version picker, or pressing Enter on it, MUST copy the full path to the clipboard and show briefly that it was copied; if the clipboard refuses, the picker MUST say the path was not copied.
- **FR-003**: The version picker's header, the browser tab's title, the recent histories list and the log lines about a history MUST use the same name.
- **FR-004**: The name MUST come from the link alone: no file is read and no request is made to find it, and it is the same for every version of the history.
- **FR-005**: A private history's name MUST stay its id.

### Key Entities

- **History name**: what a person reads as the history's name; one string, never empty.
- **History path**: `owner/repo` and the folder path of the graph file in one string, shown on hover and copied on click.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The three graph files of this repository open as three histories named `aoa-demo`, `web` and `repo_graph_port`.
- **SC-002**: Every rule of FR-001 and every edge case is covered by a test that fails when its rule is removed.
- **SC-003**: Opening a history takes no longer than today.

## Assumptions

- A public history's link always names the graph file's path inside the repository, as every link Maxitor accepts today does.
- Saved recent histories keep the name they were saved with until they are opened again.
