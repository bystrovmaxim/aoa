# Contract — the refusals, in the words a developer reads

**Feature**: `specs/010-aspect-declaration-invariants` | **Version**: 1 | **Date**: 2026-10-18

The refusal is this feature's only user-visible output, so the wording is part of the contract. Each block below is the exact shape of a message; the tests assert on the quoted fragments, and the documentation in phase 5 shows the same text.

## R-1 — a renamed or reordered parameter

Fires while the class body executes, from the decorator.

```text
AspectSignatureError: @summary_aspect: method 'create_order_summary' must declare its
parameters as (self, params, state, box, connections), got (self, p, state, box, connections).
The pipeline hands them over in that order and Python binds by position, so a renamed or
reordered parameter receives something other than it says.
```

Asserted fragments: `must declare its parameters as`, the expected order, the written order, `binds by position`.

## R-2 — the trailing `ctx` disagrees with `@context_requires`

Three cases, one rule, two directions:

| What was written | What the message adds |
| --- | --- |
| takes `ctx`, no `@context_requires` | `put @context_requires(...) under the @summary_aspect decorator, not above it` |
| declares `@context_requires`, no `ctx` | `asked for context, so it must take the trailing ctx parameter` |
| declares it above the decorator | the first message: the decorator cannot see what sits above it |

## R-3 — a signature the engine cannot call positionally

```text
AspectSignatureError: @regular_aspect: method 'validate_aspect' must be callable with
positional arguments; the pipeline passes (self, params, state, box, connections) by
position, so keyword-only parameters, *args and **kwargs are refused.
```

## R-4 — an annotation is missing

```text
AspectSignatureError: @on_error: method 'charge_on_error' must annotate every parameter it
receives; (state, connections) carry no annotation.
```

and for the return:

```text
AspectSignatureError: @on_error: method 'charge_on_error' must annotate what it returns
(-> Charge.Result).
```

## R-5 — the annotations do not resolve at assembly

```text
AspectSignatureError: @summary_aspect: CreateOrder.create_order_summary annotates its
signature with names that cannot be resolved (name 'CreateOrderParams' is not defined); the
signature is part of the contract, so its annotations must be importable.
```

## R-6 — an annotation names the wrong type

```text
AspectSignatureError: @summary_aspect: CreateOrder.create_order_summary annotates 'box' as
str, but the pipeline hands over (self, params, state, box, connections) in that order: it
must be ToolsBox or a subclass of it.
```

## R-7 — a summary's return is not its `Result`

```text
AspectSignatureError: @summary_aspect: CreateOrder.create_order_summary annotates its return
as Any, but a summary answers with the operation's Result — CreateOrder.Result.
```

## R-8 — a second summary

```text
DuplicateSummaryAspectError: CreateOrder declares more than one exit point
(create_order_summary, second_summary); an operation answers once.
```

This one is asserted on the **absence** of the phrase `missing target_node_id`: the old failure named a graph node, and the new one must never do so.

## R-9 — the answer is not a `Result`

```text
ActionResultTypeError: CreateOrder.create_order_summary returned dict, but the operation
declares Result CreateOrder.Result.
```

## Wording rules

1. **One sentence per fact.** The rule, the written form, the required form, and why — in that order.
2. **The names are quoted exactly.** A reader greps the message against their code.
3. **`@access_decide`'s shape is the reference**: "must declare its parameters as", "annotates 'X' as", "the engine hands over … in that order". The aspect messages use the same phrasings so that the five declarations read as one family.
4. **The moment is named only where it is not obvious**: an assembly refusal says the class body already executed, because a developer who wrote the class may not know that resolution happened later.
