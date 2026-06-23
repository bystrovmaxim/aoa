<!-- translated-from: step-12-authentication_draft.md @ 2026-06-16T20:26:43Z · sha256:f4a9bfdfa3a7 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 12 — Authentication

<table width="100%"><tr>
  <td align="left"><a href="step-11-machine.md">← Step 11 — ActionProductMachine</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-13-fastapi.md">Step 13 — FastAPI →</a></td>
</tr></table>

- [Authentication is not authorization](#authentication-is-not-authorization)
- [Context is born at the boundary](#context-is-born-at-the-boundary)
- [The coordinator pipeline](#the-coordinator-pipeline)
- [NoAuthCoordinator](#noauthcoordinator)
- [One mechanism for any transport](#one-mechanism-for-any-transport)
- [Four ready methods](#four-ready-methods)
- [Where it is wired](#where-it-is-wired)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In the [machine chapter](step-11-machine.md) we left one question open: `machine.run(context, ...)` receives `Context` already built — but who builds it? The answer: authentication, and it happens **before** the machine, at the transport boundary. This is a separate layer that turns a raw request (HTTP, MCP, CLI) into a verified `Context` — and only then does the operation begin its work.

So the operation stays clean: it knows nothing about tokens, headers, or the means of entry. All of that is sorted out before its launch.

---

## Authentication is not authorization

Two things that are easy to confuse are kept apart in AOA:

- **Authentication** answers the question "**who** is calling" — it establishes the user's identity and roles, packing them into `UserInfo` (a part of [Context](step-07-context.md)). About this — the current chapter.
- **Authorization** answers the question "**what** are they allowed" — this is [`@check_roles`](step-03-authorization-and-roles.md), which checks roles on every call.

The link between them is `Context`: authentication **produces** it (puts the user's role classes into `UserInfo.roles`), and `@check_roles` **consumes** it (matches the required roles against `context.user.roles`). One does not work without the other, but these are different layers.

## Context is born at the boundary

Authentication is performed not by the machine but by a **coordinator** at the transport boundary. It takes a raw request object and returns a `Context` — or `None`, if entry failed:

```python
context = await auth_coordinator.process(request)
if context is None:
    ...  # rejection: invalid credentials
else:
    result = await machine.run(context, SomeAction(), params)
```

The machine receives `Context` already assembled and verified. That is why an `Action` knows nothing about the transport — the same operations work identically behind HTTP, MCP, or CLI.

## The coordinator pipeline

`AuthCoordinator` is an orchestrator of three swappable components. `process` calls them in turn and assembles `Context`:

```python
class AuthCoordinator:
    def __init__(self, extractor, auth_instance, assembler): ...

    async def process(self, request_data) -> Context | None:
        credentials = await self.extractor.extract(request_data)   # 1. extract
        if not credentials:
            return None
        user = await self.authenticator.authenticate(credentials)  # 2. verify
        if not user:
            return None
        metadata = await self.assembler.assemble(request_data)      # 3. collect metadata
        return Context(user=user, request=RequestInfo(**metadata))  # 4. assemble Context
```

Each component is an extension point (an abstract class):

- **`CredentialExtractor.extract(request)` → `dict`** — pulls credentials out of the request (a Bearer token from a header, a key from the query, a login/password). Empty — entry is aborted.
- **`Authenticator.authenticate(credentials)` → `UserInfo | None`** — verifies them and returns a user with roles; invalid data → `None` (not an exception).
- **`ContextAssembler.assemble(request)` → `dict`** — extracts request metadata (`trace_id`, path, IP, …) for `RequestInfo`.

`Authenticator` is the place where the concrete entry method lives. For example:

```python
class JwtAuthenticator(Authenticator):
    async def authenticate(self, credentials) -> UserInfo | None:
        claims = verify_jwt(credentials["token"])           # your signature verification
        if claims is None:
            return None
        return UserInfo(user_id=claims["sub"], roles=(ManagerRole,))
```

`UserInfo.roles` is a tuple of **role classes** (not strings), which `@check_roles` will then check.

## NoAuthCoordinator

The only coordinator ready out of the box today is `NoAuthCoordinator`. It does not authenticate but always returns a fresh **anonymous** `Context` (`user_id=None`, `roles=()`):

```python
context = await NoAuthCoordinator(context=Context()).process(None)
```

This is the right choice for open endpoints — operations with [`@check_roles(GuestRole)`](step-03-authorization-and-roles.md). Anonymity here is declared explicitly, not obtained "by default".

## One mechanism for any transport

Only `CredentialExtractor` is protocol-dependent — it knows where to take credentials from in this transport. `Authenticator` (verification) and `ContextAssembler` (metadata) are reused. That is why the same authentication logic serves an HTTP service, an MCP tool, a CLI, a cron job, or a queue message — only the extraction changes, while the way of verifying and assembling `Context` stays common.

## Four ready methods

For now you implement `Authenticator` for your own method yourself. Planned (ROADMAP) are ready out-of-the-box implementations for four common schemes:

- **HTTP Basic Auth**,
- **Bearer Token (JWT)**,
- **API Key**,
- **OAuth2** (Google / GitHub / Keycloak).

With their arrival, typical authentication will be wirable without writing your own `Authenticator`. Until then the template is one: implement the three components (or take `NoAuthCoordinator` for open access).

## Where it is wired

The coordinator lives on the transport **adapter**, not on the machine. The adapter calls `process(request)` to build `Context`, and then passes it to `machine.run`:

```python
app = FastApiAdapter(machine=machine, auth_coordinator=auth_coordinator, title="Orders API")
```

How the adapters themselves are built is in the [FastAPI](step-13-fastapi.md) and [MCP](step-14-mcp.md) chapters. Your own authentication scheme is shaped as a [custom authentication coordinator](../index.md#how-to-write-your-own-extension).

## Invariants

- **`Context` is built by the transport, not the machine.** The machine receives a ready `Context` in `run(context, ...)`.
- **A pipeline of three components.** `extract → authenticate → assemble → Context`; empty credentials or an invalid user → `None`.
- **Invalid is `None`, not an exception.** `Authenticator` returns `None` rather than raising.
- **Anonymity is declared.** Open access is `NoAuthCoordinator`, not the absence of a check.
- **Authentication ≠ authorization.** The first puts roles into `Context`; the second (`@check_roles`) checks them in the machine.
- **Only the extractor is protocol-dependent.** Verification and `Context` assembly are reused across transports.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why the environment is built before the operation is in the [Philosophy](../explanation/philosophy.md).

## Summary

Authentication is a separate layer at the transport boundary: `AuthCoordinator` extracts credentials, verifies them, and assembles `Context`, which the machine receives ready. The concrete entry method lives in `Authenticator`; only the extractor is protocol-dependent, so one logic serves any transport. Today `NoAuthCoordinator` (anonymous access) is available out of the box, while four typical methods — Basic, JWT, API key, OAuth2 — are planned. Authentication establishes who is calling; what they are allowed is checked by [`@check_roles`](step-03-authorization-and-roles.md).

Next — **[FastAPI](step-13-fastapi.md)**: how to expose an operation over HTTP, now that `Context` can be built at the transport boundary.

---

## Review questions

1. How does authentication differ from authorization? What links these two layers?
2. Who builds `Context` and at what moment relative to `machine.run`? Why not the machine?
3. Of which three components does `AuthCoordinator.process` consist, and what does each do?
4. Why does `Authenticator` return `None` on invalid data rather than raising an exception?
5. What is `NoAuthCoordinator`, and for which operations is it appropriate?
6. Which of the three components is protocol-dependent, and which are reused across transports? Why does this give "one mechanism for any transport"?
7. Which four authentication methods are planned, and what do you have to do until they arrive?

> **Exercise.** Sketch an `Authenticator` for an API key: `extract` pulls the key from the `X-Api-Key` header, `authenticate` matches it against a "key → (user_id, roles)" dictionary and returns `UserInfo(user_id=..., roles=(...))` or `None`. Run through mentally what `process` returns if the key is missing, if the key is wrong, and if it is correct — and which `Context` the machine receives in each case.

---

<table width="100%"><tr>
  <td align="left"><a href="step-11-machine.md">← Step 11 — ActionProductMachine</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-13-fastapi.md">Step 13 — FastAPI →</a></td>
</tr></table>
