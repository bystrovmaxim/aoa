# Contract: the room's range

Extends spec 037's `version` message (research R14). One message carries mode, A and B, so two changes at once end with the last.

| Direction | Message | Meaning |
|---|---|---|
| client → server | `{"type": "version", "b": "<sha>"|"live", "a": "<sha>"|null}` | `a` absent or `null` → One on `b`; else Diff A→B |
| server → room | `{"type": "version", "b": …, "a": …, "by": "<participant>"|null}` | the room's range now |
| server → sender | `{"type": "error", "reason": "<why>"}` | refused; the room does not move |
| `welcome.room` | + `"version_a": "<sha>"|null` | the room's A for a newcomer |

Refused, with the reason: `a` equal to `b`; `a` = `live`; `a` newer than `b` on the history's track; `a` or `b` not in the history or refused; `b` = `live` where there is no Live. A client normalises before sending (swaps a reversed pair), so a refusal means a stale client.

The room link carries `mode=diff`, `a`, `b` like the address bar.
