# Contract: Events explorer

`GET /api/v1/events-explorer` answers `{"events_explorer": EventsExplorer}` ([data-model](../data-model.md)) through `GetEventsExplorerAction` (`DiagramsDomain`, `GuestRole`, the DuckDB graph connection), reading the same graph versions as the other diagrams (`?version=` as they do).

Removed: `GET /api/v1/domain-events-diagram`, `GET /api/v1/events-diagram`.

Sidebar rows `events_all` and `events_domain` keep their ids and page keys (`events-all`, `events` with `domain`); both open the explorer, the domain row with `domain:<id>>events` in `opened`.

Address and room: the page settings of [data-model](../data-model.md) "Screen state", each checked by `rooms/pages.py`.
