# Data model: spec 043

- **ErdField** gains `lifecycle_id?: string | null`.
- **ElementCardRead**: `{id, type, label, description: string|null, lifecycle_id: string|null}`.
- **HoverCardSubject** (client): `{title, detail, description, status, elements, lifecycleId, fields, copyName}`, plus its `at`.
- **Collapse state**: `fields_collapsed: boolean` (default `false`), `fields_except: string[]` (default `[]`). A table is collapsed when `fields_collapsed` differs from its presence in `fields_except`.
- **A collapsed table keeps** a row when it is a primary key, a foreign key, has a drawn line, or in Diff is marked.
