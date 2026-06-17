<!-- translated-from: step-18-converters_draft.md @ 2026-06-17T17:53:37Z · sha256:f27bcf43b95f -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 18 — Schema converters

<table width="100%"><tr>
  <td align="left"><a href="step-17-connections.md">← Step 17 — Connections at the boundary</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-19-resource.md">Step 19 — Resource →</a></td>
</tr></table>

- [Translation at the boundary](#translation-at-the-boundary)
- [Two versions side by side](#two-versions-side-by-side)
- [A mapper is mandatory when the model differs](#a-mapper-is-mandatory-when-the-model-differs)
- [What goes where](#what-goes-where)
- [The same in MCP](#the-same-in-mcp)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

The external schema does not always match the operation's contract: a new API version ships, the frontend renames a field, a partner asks for amounts in cents rather than a float. Changing the `Action` for this is unnecessary and harmful — it is one for all versions. The translation is placed at the **adapter boundary**: an incoming request is brought to `Params`, and a `Result` to the needed external shape. We [touched on](step-13-fastapi.md#when-the-external-schema-diverges-from-the-contract) this in the FastAPI chapter; here it is in full, on the example of API versioning.

This is done by a pair of arguments on each route/tool:

- `request_model` + `params_mapper(body) -> Params` — external request → contract;
- `response_model` + `response_mapper(result) -> response_model` — contract → external response.

> The arguments are named `params_mapper` / `response_mapper`. The older names `params_converter` / `result_converter` from the README are out of date — they are not in the code.

[▶ Try in Colab](https://drive.google.com/file/d/1yt4eN9ojuCjvrvR-3C5DyuzTtlOac3LL/view?usp=drive_link) · [Open in project](../../examples/step_18_converters/01_versions.py)

---

## Translation at the boundary

Without converters the adapter validates the body straight into the operation's `Params` and serializes the `Result` as is — this is the "effective" schema by default. A converter swaps one of the sides:

```python
# v1 — native contract: Params and Result go through as-is
.post("/api/v1/orders", CreateOrderAction, tags=["orders"])

# v2 — a different schema outside, the same operation inside
.post(
    "/api/v2/orders",
    CreateOrderAction,
    request_model=OrderV2Request,    # external request shape (client, sum_cents)
    response_model=OrderV2Response,  # external response shape (id, total_cents)
    params_mapper=lambda body: CreateOrderParams(customer=body.client, amount=body.sum_cents / 100),
    response_mapper=lambda r: OrderV2Response(id=r.order_id, total_cents=round(r.total * 100)),
)
```

A route's "effective" schema is `request_model`/`response_model` if set, otherwise the operation's `Params`/`Result`. It is exactly the effective schema that validates the body, lands in OpenAPI and the MCP `inputSchema` — the client sees precisely the version it came to.

## Two versions side by side

`CreateOrderAction` knows nothing of v1 or v2 — both versions exist side by side as two routes, and all the difference between them lies at the boundary:

**Run:**

```bash
uv run python examples/step_18_converters/01_versions.py
```

**Output:**

```text
v1 (native contract):
  POST /api/v1/orders {customer, amount}  -> 200 {'order_id': 'ord-1', 'total': 99.5}

v2 (external schema, same Action):
  POST /api/v2/orders {client, sum_cents} -> 200 {'id': 'ord-1', 'total_cents': 4200}

Registration guard (differing model without its mapper):
  .post(response_model=...) without response_mapper -> ValueError: response_model (OrderV2Response) differs from result_type (CreateOrderResult); response_mapper is required.
```

v1 returns `order_id`/`total` as a float; v2 accepts `client`/`sum_cents` and returns `id`/`total_cents` in cents — the field renaming and the unit change went entirely into the mappers, while the operation stayed untouched.

## A mapper is mandatory when the model differs

A converter cannot be set up halfway — this is checked at two boundaries:

- **At registration.** If `request_model` (or `response_model`) differs from the operation's `Params`/`Result` and the matching mapper is not set, `.post(...)` fails immediately with `ValueError` (seen in the output above). You cannot declare an external schema and forget the translation.
- **At runtime.** What `params_mapper` returned must be an instance of the operation's `Params`, and `response_mapper` — an instance of `response_model`; otherwise `TypeError`. The translation must land in the contract, not "roughly" into it.

## What goes where

To not confuse the directions:

| Argument | What it describes | Where it translates |
|----------|-------------------|---------------------|
| `request_model` | the external **request** shape | (validates the body; visible in OpenAPI/`inputSchema`) |
| `params_mapper(body)` | — | external request → `Params` |
| `response_model` | the external **response** shape | (the response schema in OpenAPI) |
| `response_mapper(result)` | — | `Result` → `response_model` |

A model and its mapper are set as a **pair**: a `response_model` without a `response_mapper` (when the shape differs) will not pass registration, and a `response_mapper` without a `response_model` will return a value that does not match the declared response contract.

Converters are worth distinguishing from [result by schema](step-15-schema-results.md) and [accepting complex input](step-16-complex-input.md): those describe data **inside** the operation's contract, while converters translate **between** a version's external contract and the operation's contract.

## The same in MCP

The same four arguments are on `McpAdapter.tool(...)` too — the mechanism is common to both adapters. For a tool, `request_model` becomes its `inputSchema`, and `response_mapper` shapes the data in the response envelope. So one operation is given to the agent in the needed contract version, without changing itself.

## Invariants

- **Translation at the boundary, not in the operation.** The `Action` is one for all versions; the version difference lives in the route's `request_model`/`response_model` and mappers.
- **The effective schema.** The external model if set, otherwise `Params`/`Result`; it is what validates and lands in OpenAPI / `inputSchema`.
- **A model and a mapper as a pair.** A differing model without its mapper → `ValueError` at registration.
- **The translation must land in the contract.** `params_mapper` → an instance of `Params`, `response_mapper` → an instance of `response_model`; otherwise `TypeError` at runtime.
- **One mechanism for FastAPI and MCP.**

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

When the external schema diverges from the operation's contract, the translation is placed at the adapter boundary: `request_model`/`params_mapper` bring the request to `Params`, and `response_model`/`response_mapper` bring the `Result` to the needed response. So several API versions live side by side, while the `Action` stays one and unchanged; the version's "effective" schema is meanwhile honestly reflected in OpenAPI and the `inputSchema`. The model and the mapper are linked: the machine will not let you declare an external shape and not provide the translation.

With this the **Service** part is fully assembled: the machine, authentication, two transports, result and input by schema, connections, and version converters. Next — the **Data model** part, and its first hero is **[Resource](step-19-resource.md)**: an operation's boundary with the external world, pure transport separated from logic.

---

## Review questions

1. Why translate schemas at the adapter boundary rather than change the operation's `Params`/`Result`?
2. What is a route's "effective" schema, and what does it affect (validation, OpenAPI, `inputSchema`)?
3. What happens at registration if you set a `response_model` that differs from `Result` but do not set a `response_mapper`?
4. Which check does the result of `params_mapper` pass at runtime, and why?
5. Why are a model and its mapper set as a pair? What is wrong with a `response_mapper` without a `response_model`?
6. How do converters differ from the topics "result by schema" and "accepting complex input"?

> **Exercise.** In [01_versions.py](../../examples/step_18_converters/01_versions.py) add an `/api/v3/orders` route where `response_mapper` returns a `dict` rather than an `OrderV2Response`, and trace at which boundary this is rejected and with which exception. Then remove `params_mapper` from v2 and confirm that registration fails with a `ValueError` before the server even starts.

---

<table width="100%"><tr>
  <td align="left"><a href="step-17-connections.md">← Step 17 — Connections at the boundary</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-19-resource.md">Step 19 — Resource →</a></td>
</tr></table>
