# Specification Quality Checklist: Maxitor Rooms — Looking at One Service Together

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-27
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Named mechanisms are contracts, not implementation.** The spec names `ETag`, `If-None-Match` and `304`, the four `Math` functions, the `room` address parameter and the `MAXITOR_*` settings. Each is an interface a service, a browser or an operator sees, or the very thing a test must catch, as in specs 025–027. The *Context* section cites files only to record what was checked on 2026-10-27. No framework, library or code structure is prescribed for building the feature.
- **Three statements of the issue did not hold against the code** and the spec follows the code: node dragging was removed by #245, so shared dragging (issue §4.4) is not specified; the node-type filter of the full graph (the issue's #246) does not exist, so it joins the room later by FR-030; the layout centre does depend on the canvas size, as the issue says.
- **AOA actions, resources and `box` are a requirement, not an implementation detail.** FR-066 to FR-069 and the assumption on older code state the project's most critical architectural rule, confirmed by the maintainer on 2026-10-27: an endpoint works only by running an action, a store or a service is reached only through a resource, and logging goes through `box`. They stay in the specification so that planning cannot fall back to a hand-written handler.
- **Two details moved to the plan** (maintainer, 2026-10-27): which script runs the cross-engine step and how it installs the browsers (FR-006), and the one-slot outgoing queue that keeps a slow connection on the newest position (FR-043, FR-068). The specification keeps only the behaviour; `plan.md` must name both.
- **The mockup is normative.** Visual details the text does not state are decided by `mockup/index.html`; the screen numbers in the acceptance scenarios refer to its list.
- Validation passed on the first iteration; the spec is ready for `/speckit-clarify` or `/speckit-plan`.
