# Implementation Plan: Maxitor shows events

**Branch**: `feature/issue-335-maxitor-shows-events` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

## Summary

Maxitor gains an Events diagram for each domain, built like the Use case diagram: an AOA action reads the graph document and returns a slice; the client draws it with Graphviz in the common shell. Events get an icon and the common card. A comparison marks them through the existing comparison of graphs.

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14); TypeScript, React 19
**Primary Dependencies**: AOA actions, Graphviz WASM, Sigma.js (full graph only)
**Storage**: graph documents, read through the existing resources
**Testing**: pytest, Vitest; browsers through `scripts/check_before_pr.sh`
**Target Platform**: Maxitor web part
**Project Type**: web application
**Constraints**: endpoints only through actions; no language assumptions; documents older than 1.3 keep opening
**Scale/Scope**: one new diagram, one card extension, one icon

## Constitution Check

- I. Nothing is committed without instruction: held.
- II. English in code and history: held.
- III–V. Module headers, AI-CORE blocks, docstrings on new code: planned.
- VI. Last three steps are check run, documentation, changelog: phases 2, 3, 4.
- Version of `maxitor` and its levels raised on the branch before the pull request (house rule).

Gates pass, before and after design.

## Project Structure

```text
packages/maxitor/web/maxitor/web/model/diagrams/actions/   domain_events_diagram_action*.py, list of diagrams
packages/maxitor/web/client/src/api/                       domainEventsDiagram.ts
packages/maxitor/web/client/src/model/                     domainEventsDiagram.ts, diagramSelection.ts
packages/maxitor/web/client/src/components/diagrams/       EventsDiagramViewer/, ElementCard/
packages/maxitor/web/client/src/components/navigation/     LeftSidebar/
packages/maxitor/web/client/src/lib/                       buildDomainEventsDotSource.ts, icons
packages/maxitor/web/client/scripts/                       check-layout-determinism.ts
docs/tutorials/step-26-maxitor.md
```

**Structure Decision**: follow the Use case diagram file by file, so rooms, address, Diff and Side by side come through the same paths.

## Phases

1. The view of events (one commit).
2. Closing check run taken to zero.
3. Documentation: the Maxitor chapter.
4. Changelog.
