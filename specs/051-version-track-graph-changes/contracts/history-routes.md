# Contract: Maxitor's history routes

Both routes keep their shape and grow fields.

`GET /api/history/open?history=<name>` and `GET /api/history/versions?history=<name>` answer also:

```json
{"version_file": "packages/x/version.toml", "version_problem": null}
```

Each version passes as the port sends it, with `graph_changed`, `version` and `version_changed`.

`<name>` of a public history may be:

```text
https://github.com/o/r/blob/main/graph.json?version_link=https%3A%2F%2Fgithub.com%2Fo%2Fr%2Fblob%2Fmain%2Fpyproject.toml&version_key=project.version
```

| Address | Answer |
|---|---|
| Any other query parameter | Refused, the message naming what is allowed |
| `version_key=` with no `version_link=` | Refused |
| `version_link=` the port cannot use | Opens, with `version_problem` |
| A private history with a query | Refused, as today |

`GET` to the port passes `link`, `version_link` and `version_key` on the description, the list and each version's graph.
