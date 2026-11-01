# Contract: Room Protocol Additions

All additions are optional: a message without them means what it means today.

## Client → server

```jsonc
{"type": "version", "b": "459e3be2de3d", "a": "39f03ff4be5a", "view": "split"}
{"type": "pointer", "kind": "mouse", "x": 1, "y": 2, "half": "a"}
{"type": "click", "x": 1, "y": 2, "half": "b"}
{"type": "viewport", "cx": 1, "cy": 2, "w": 3, "h": 4, "half": "a"}
{"type": "setting", "page": "…", "name": "layout_a", "value": "gv-dot-tb"}
{"type": "setting", "page": "…", "name": "selected", "value": {"kind": "table", "id": "…"}}
```

Refused with `error` to the sender: `view` unknown; `split` or `diff` without `a`; `one` with `a`.
A `half` other than `a` or `b` is dropped from the relay.

## Server → client

`version` gains `view`; `welcome`'s room gains `view`. `pointer`, `click` and `viewport` pass `half` on.

## Comparison answer

Gains `sha_a` and `sha_b`: the sha256 of each graph.
