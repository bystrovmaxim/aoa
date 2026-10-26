# Contract: what the server sends

Applies to every answer of `create_app` (`packages/aoa-maxitor/src/aoa/maxitor/api/app.py`). Verified by `packages/aoa-maxitor/tests/test_api_compression_and_cache.py`.

## Compression

| Request | Answer body | Result |
|---|---|---|
| `Accept-Encoding: gzip` | ≥ 500 bytes | `Content-Encoding: gzip`, `Vary: Accept-Encoding`, body gzip-compressed |
| `Accept-Encoding: gzip` | < 500 bytes | sent as is, no `Content-Encoding` |
| no `Accept-Encoding`, or one without `gzip` | any | sent as is |
| any | a range request (`206`) or `text/event-stream` | sent as is |

Decompressing a compressed body gives exactly the bytes the uncompressed answer carries.

## Cache lifetime

| Path | `Cache-Control` |
|---|---|
| `/assets/<name>-<hash>.<ext>` (any file under `assets/` in the built client) | `public, max-age=31536000, immutable` |
| `/` and `/index.html` | `no-cache` (the `etag` stays, so a repeat open gets `304`) |
| any other static file | none (unchanged from today) |
| `/api/...` | none (unchanged from today) |

## Refusals keep their shape

`GraphSourceMiddleware`'s answers — `400` without `source`, `422` for a source that cannot be built, `503` with `Retry-After` when the store is busy — keep their status, their JSON `detail` and their headers, including `Access-Control-Allow-Origin` and `Access-Control-Expose-Headers: Retry-After`. If such a body reaches 500 bytes and the request accepts gzip, only the encoding is added.

## Order of the middleware

```
request ─► GZipMiddleware ─► CORSMiddleware ─► GraphSourceMiddleware ─► routes / mounts (StaticFiles → CachedStaticFiles)
```

`GZipMiddleware` is added last, so it is outermost and sees every answer, the refusals included.
