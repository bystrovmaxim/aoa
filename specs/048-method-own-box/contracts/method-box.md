# Contract: what a method of an action receives as `box`

This is the behaviour an action's author and a logger's author can rely on. No signature changes.

## The rule

Every method that receives `box` receives one of its own, carrying its own name. There are no exceptions.

| Kind of method | `{%scope.aspect}` | What `{%state.x}` reads |
|---|---|---|
| `@regular_aspect` | the method's name | the current `state` |
| `@summary_aspect` | the method's name | the current `state` |
| `@compensate` | the method's name | the snapshot before its step |
| `@on_error` | the handler's name | the same `state` the handler receives |
| `@access_decide` | the method's name | nothing: it has no `state`, so naming a field fails |

## Promises

1. `{%scope.action}:{%scope.aspect}` is the id of the method's node in the graph, for all five kinds.
2. `@access_decide` reports the same name on a normal run and in `check_access_decide`.
3. Naming an absent field in a log template fails, for every kind. In a handler this is reported as `OnErrorHandlerError`; in `@access_decide` as `Undecided` naming the object step.
4. Apart from its name and `state`, a method's `box` does what the shared one did: nested runs, dependencies, resources, nesting level and rollup are unchanged.

## What a logger sees differently

Lines from `@on_error` and `@access_decide` carry a method name where they carried an empty string. Nothing else in `LogScope` changes.

## What does not change

`ToolsBox` gains no public member. An action cannot choose or change the name its `box` carries.
