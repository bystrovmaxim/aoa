# Data Model: Typed events, `@emits` and the domain vocabulary

Nothing here is stored. These are the types of the feature and the rules on them.

## `BaseEvent`

A descendant of `EventMarker` and `BaseSchema`. Immutable, extra fields forbidden.

| Field | Type | Set by | In a dump |
|---|---|---|---|
| `level` | `LogLevelPayload \| None` | `box` | no |
| `channels` | `LogChannelPayload \| None` | `box` | no |
| `domain` | `type[BaseDomain] \| None` | `box` | no |
| `domain_name` | `str \| None` | `box` | no |
| fields of the subclass | as declared | the author | yes |

Rules:

| Rule | Refused when | Error |
|---|---|---|
| The name ends with `Event` | the class is defined | `NamingSuffixError` |
| No field named after a system field | the class is defined | `EventContractError` |
| No field named `get`, `keys`, `values`, `items`, `resolve` | the class is defined | `EventContractError` |
| The author sets no system field | the event is built | `ValidationError` |

Life of an instance: the author builds it with the system fields empty. `box` makes a filled copy, and the copy is `var`. The author's instance never changes.

## `var`

| The call has | `var` is | Read by key |
|---|---|---|
| an event | the filled copy, of the event's own class | `var["level"]`, `var.get("domain")`, `"level" in var`, `var.items()` |
| `kwargs`, or no variables | a dictionary, as it is now | the same |

Writing into `var` or merging it as a dictionary works only on the dictionary.

## `@emits`

`_emits_events`: a tuple of event classes on the function. At least one, no repeats, no `BaseEvent` itself, and written once per method. Read on the five kinds of method only. An action's emitting methods are those of its own class, so a declaration never comes from a parent action.

## `events` on a domain

An optional class attribute, a tuple of distinct subclasses of `BaseEvent`. Absent means no vocabulary, and `()` means a vocabulary that allows nothing. A domain inherits it, and declaring its own replaces it. One class may be in several domains, and an unused class is allowed.

## `EmissionRules`

Internal, frozen, one per method call. It exists only when a switch is on.

| Field | Meaning |
|---|---|
| `action_name`, `method_name` | who is emitting, for the error |
| `declared` | the method's `@emits`, or `None` |
| `vocabulary` | the domain's `events`, or `None` |
| `domain_name` | which domain, for the error |

`check(event)` where `event` may be `None`:

| `declared` | `vocabulary` | No event | Event in `declared` | Event not in `declared` |
|---|---|---|---|---|
| set | `None` | refused | passes | refused |
| set | set | refused | passes if also in `vocabulary` | refused |
| `None` | set | refused | not applicable | refused |

## `EventContractError`

A `TypeError`. Its message names what was refused, and, for an emission, the action, the method and the switch that refused it.
