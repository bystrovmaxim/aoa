# Contract: Events diagram

`GET /api/v1/domain-events-diagram?domain_id=<id>` answers `{"domain_events_diagram": EventsDiagram}` (see [data-model](../data-model.md)), through an AOA action, reading the same graph versions as the other diagrams. An unknown domain answers as the Use case endpoint does.

Sidebar row of type `events_domain` beside `use_case_domain`. Address: `view=events&domain=<qualifier>`.
