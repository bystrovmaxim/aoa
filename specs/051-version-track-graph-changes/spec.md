# Feature Specification: The version track shows where the graph changed

**Feature Branch**: `feature/issue-345-version-track`

**Created**: 2026-11-02

**Status**: Draft

**Input**: GitHub issue #345, "Versioning 4/5: Maxitor's version track shows where the graph changed". The issue is part of #340 and uses the fields of a history point that #344 delivered.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See at a glance where the model changed (Priority: P1)

A person reading a graph's history sees every version on the track and tells at once which ones changed the graph. A large point means the graph changed, a small point means it did not. The number under a point appears where the version changed there.

**Why this priority**: This is the feature. Everything else protects it.

**Independent Test**: Open a history with a version file, where some commits raised the version without changing the graph.

**Acceptance Scenarios**:

1. **Given** a commit that changed the graph, **When** the track is drawn, **Then** its point is large.
2. **Given** a commit that raised the version and left the graph alone, **When** the track is drawn, **Then** its point is small and shows the new number under it.
3. **Given** a commit that changed the graph and left the version alone, **When** the track is drawn, **Then** its point is large and has no number under it, while the version button and the point's card still show the version in force.
4. **Given** a history with no version file, **When** the track is drawn, **Then** numbers come from tags as they always did, and every point is large because every point changed the graph.
5. **Given** a point with a tag published as a GitHub Release or named `release…`, **When** the track is drawn, **Then** it carries a flag whatever the size of its point.

---

### User Story 2 - Hide the versions that did not change the graph (Priority: P2)

A reader interested only in the model hides the small points with an icon of three points on a line, in the picker's head beside the "i". It is coloured while they are shown and grey while they are hidden. Hiding is only a way of looking: what is chosen stays chosen.

**Why this priority**: A long history gains many small points; without this the track gets harder to read.

**Independent Test**: Choose a small point, as one end of a comparison, then switch the icon off.

**Acceptance Scenarios**:

1. **Given** a history with points that did not change the graph, **When** it opens, **Then** the icon is there, on, with a tooltip saying what it does.
2. **Given** a history with no such points, because it has no version file or the file cannot be read, **When** it opens, **Then** there is no icon.
3. **Given** a chosen small point, **When** the reader hides small points, **Then** the chosen commit, both ends of a comparison, the version, the pull request and the room's state do not change, and that point stays on the track while it is chosen.
4. **Given** a reader following someone who chose a small point, **When** the follower has small points hidden, **Then** that point is on the follower's track.
5. **Given** two viewers in one room, **When** one switches the icon, **Then** the other's track does not change.
6. **Given** hidden points with flags, **When** the track is drawn, **Then** their flags are on the nearest visible point before them, and that point's card lists all its flags.

---

### User Story 3 - Be told plainly what is wrong (Priority: P2)

A reader whose history names a broken version file, or who compares two points with one and the same graph, gets a plain sentence instead of a puzzle.

**Why this priority**: Without it, a wrong path looks like a history with no versions, and a comparison of equal graphs looks like a fault.

**Independent Test**: Open a history whose version file is wrong; compare two points on either side of a small point.

**Acceptance Scenarios**:

1. **Given** a history with a version problem, **When** it opens, **Then** the foot of the picker says what the track shows and why, a scarlet dot marks the version button, and the graph still opens.
2. **Given** a public link with `version_link=` and `version_key=`, **When** it opens and the history is polled, **Then** both stay in its address and in every poll, and the track behaves as for a configured history.
3. **Given** two compared points with the same graph, **When** the comparison opens, **Then** it says the graphs are the same instead of showing an empty picture.

---

### User Story 4 - Learn what the marks mean (Priority: P3)

A new reader opens the legend behind the "i" and finds what large points, small points, numbers, flags and the icon mean.

**Why this priority**: The meaning of a large point changes, so a reader who knew the old one must be able to look it up.

**Independent Test**: Open the legend on a history with a version file and on one without.

**Acceptance Scenarios**:

1. **Given** the track, **When** the reader opens the legend, **Then** it explains large points, small points, numbers and flags as they work now.

---

### Edge Cases

- Every point of a history is small after the first: the first point of a history counts as a graph change, so the track is never empty when small points are hidden.
- A hidden point stops being chosen: it leaves the track as soon as nothing chooses it.
- The nearest visible point before a hidden flag does not exist: the flag goes to the earliest visible point.
- A point has several flags: the track shows that it has them, and the card lists each one.
- A very long history: the track stays readable and responsive with many more points.
- A point's version is empty, because the version file did not exist yet: no number under it, and the button and card show no version.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A point's size MUST follow one rule: large when the graph changed there, small when it did not. The size MUST NOT depend on a release.
- **FR-002**: With a version file, the number under a point MUST be the point's version when the version changed there, and nothing otherwise.
- **FR-003**: The version button and the point's card MUST show the point's version whether or not it changed there.
- **FR-004**: With no version file, numbers MUST come from tags as before.
- **FR-005**: The flag MUST keep its meaning: a tag published as a GitHub Release, or a tag named `release…`.
- **FR-006**: Maxitor's server MUST carry a history's version problem, version file, `version_link=` and `version_key=` from the port to the reader, through the gateway, the history entry, the history's address and the polling.
- **FR-007**: A history with points that did not change the graph MUST offer an icon of three points on a line beside the "i", with a tooltip, on by default, changing its colour and never a background. A history with no such point MUST NOT offer it.
- **FR-008**: The icon MUST be each viewer's own setting and MUST NOT pass through a room.
- **FR-009**: Hiding points MUST NOT change the chosen commit, either end of a comparison, the version, the pull request or the state of a room.
- **FR-010**: A hidden point MUST stay on the track while it is chosen, also for a viewer who follows someone.
- **FR-011**: Flags of hidden points MUST be drawn on the nearest visible point before them, as drawing only, and that point's card MUST list every flag it carries.
- **FR-012**: A comparison of two points with the same graph MUST say so.
- **FR-013**: A version problem MUST be shown at the foot of the picker, saying what the track shows and why, with a scarlet dot there and on the version button, and the graph MUST still open.
- **FR-014**: The legend MUST describe the marks as they work now.

### Key Entities

- **Version point**: a commit on the track, with whether the graph changed, its version, and whether the version changed.
- **History**: a graph's timeline, optionally joined with a version file, and optionally carrying a version problem.
- **Viewer's setting**: whether this viewer shows the points that did not change the graph.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a history with a version file, a reader can name every point that changed the graph from the track alone, with no click.
- **SC-002**: Hiding and showing points changes none of the chosen commit, the comparison, the version or the pull request, in 100% of tried combinations.
- **SC-003**: In a room, 0 changes of the icon reach another viewer.
- **SC-004**: A history with no version file keeps its numbers, flags, choices and comparisons; only the size of its points and the wording of the legend differ, since every point there changed the graph.
- **SC-005**: A history with a version problem opens its graph in every case, with the problem in plain words on the screen.
- **SC-006**: A history of 500 points stays usable: choosing a point and switching the icon respond in under one second.

## Assumptions

- The port already returns `graph_changed`, `version`, `version_changed` and `version_problem`; this feature does not change the port.
- The first point of a history counts as a graph change, as the port reports it.
- The icon's state is remembered for this viewer in the browser, and starts on.
- It is not recorded in a page address.
- Accepted on the local history `erd-full`, extended with a version file for this step.
