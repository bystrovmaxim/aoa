# Changelog

All notable changes to `aoa-client-js` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Conventions.** Release headings use `## [version] – YYYY-MM-DD` (en dash). Use `### Breaking changes`, `### Added`, `### Changed`, `### Fixed`, `### Removed`, and `### Documentation` as needed. Each bullet starts with a **bold title** followed by a period and the body.

## [Unreleased]

### Added

- **New package: `AoaEngine.resolve()` — a minimal, framework-neutral HTTP client for the `/permissions/resolve` protocol.** First release of `aoa-client-js`, a self-contained TypeScript package (structural precedent: `aoa-maxitor/client`) with no dependency on the Python side beyond the network protocol. `AoaEngine.resolve(items)` makes exactly one `POST /permissions/resolve` request per call — no caching, no batching yet (chapters 6/7) — and validates the response before trusting it: `res.ok`, content-type, wire-language `version`, and that `results.length` matches the request, before returning `results` untouched. A malformed or unreachable response throws a typed error instead (`Unauthorized` on `401`, `ProtocolError` on a content-type/version/cardinality mismatch, `NetworkUnavailable` when `fetch` itself throws) — a transport failure never becomes a synthetic denial. `resolve()` returns `Verdict[]`, a discriminated union of the same three outcome classes the server uses (`aoa-action-machine`'s `BaseVerdict` hierarchy): `AllowedVerdict` (success, no `reason` field at all), and `FailSecurityVerdict`/`FailErrorVerdict` (both carry a mandatory `reason`; `FailErrorVerdict` is not a denial and must never be cached as one). Every call carries its own `trace_id` (`crypto.randomUUID()` by default, overridable via `opts.traceId` to correlate several calls under one user gesture) sent as the `x-trace-id` header the server already reads. `AoaEngine`'s identity (`cachePartition`) is fixed at construction and read-only — switching subjects means constructing a new `AoaEngine`, never mutating an existing one. `isRetryableCheckError(reason)` is a client-side judgment call on whether a `FailErrorVerdict` is worth retrying (`TIMEOUT` only) — the wire itself carries no such concept. `fetchImpl` is injected via the constructor rather than read off `window.fetch`, so `AoaEngine` runs in Node (SSR, chapter 10) as well as the browser. ([#137](https://github.com/bystrovmaxim/aoa/issues/137), part of [#130](https://github.com/bystrovmaxim/aoa/issues/130))
