# Contract: WebSocket routes of the FastAPI adapter

Package: `aoa-fastapi-adapter`. A WebSocket route turns one connection into action runs, exactly as an HTTP route turns one request into one. It holds no domain logic (research R1, R5).

## Registration

```python
FastApiAdapter(machine=..., auth_coordinator=...).websocket(
    path: str,                                   # may carry path parameters, e.g. "/rooms/{room_id}/live"
    *,
    on_open: type[BaseAction],                   # run once after accept; its refusal closes the socket
    messages: Mapping[str, type[BaseAction]],    # message "type" → action
    on_close: type[BaseAction] | None = None,    # run once when the connection ends, for any reason
    relay: frozenset[str] = frozenset(),         # message types relayed without an action
    relay_key: str | None = None,                # connection key of the resource that relays them
    connections: Mapping[str, BaseResource] = {},
    max_message_bytes: int = 4096,
    max_messages_per_second: int = 40,
    tags: Sequence[str] = (),
    description: str = "",
) -> FastApiAdapter
```

Returns the adapter for chaining, like `get` / `post`. `build()` registers the route on the same app.

## One connection

1. **Accept**, then create `SocketChannel` (below) for this connection.
2. **Open**: run `on_open` with params built from the path and query parameters plus `origin` (the request's `Origin` header, or empty), the auth coordinator's context, and connections `{**connections, "socket": channel}`. Whether an origin is acceptable is the action's decision, not the adapter's.
3. **Loop**: each text frame must be a JSON object with a string `type`.
   - Over `max_message_bytes`: close `4413`, reason `message too large`.
   - More than `max_messages_per_second` in any one-second window: close `4429`, reason `too many messages`.
   - `type` in `relay`: `connections[relay_key].relay(channel, message)`; no action runs, nothing is logged.
   - `type` in `messages`: validate the remaining fields as that action's params; run it with the same connections. Messages of one connection run one at a time, in arrival order.
   - Any other `type`, or params that do not validate: send `{"type": "error", "reason": ...}`; the connection stays open.
4. **Close**: on any end of the connection, run `on_close` with the same params and connections. Errors in it are logged by the machine, never sent.

## Refusals

An action refuses the connection by raising `ConnectionRefused(code: int, reason: str)` (new, exported by the adapter). Raised by `on_open`, it closes the socket with that code and reason; raised by a message action, it sends `{"type": "refused", "code": ..., "reason": ...}` and keeps the socket open. Codes `4000–4999` are the application's; the adapter itself uses `4413`, `4429`, `4008` and `1011` (internal error, reason `internal error`).

## SocketChannel

A per-connection resource (`BaseController`), created by the adapter, passed as `connections["socket"]`.

| Member | Meaning |
|---|---|
| `id` | a random id of this connection |
| `send(event: dict)` | queue a durable event; events reach the client in order. The queue is bounded (256); when full, the connection is closed with `4008`, reason `client too slow` |
| `send_volatile(kind: str, event: dict)` | replace the pending event of that kind, if any; the newest wins (pointer, viewport) |
| `close(code, reason)` | close the connection |
| `closed` | whether the connection has ended |

## Guarantees

- No action runs for a relayed message; every other message runs exactly one action.
- The adapter never reads or writes application state; resources do.
- The route works with any auth coordinator the adapter already supports.
