<!-- translated-from: step-10-logs_draft.md @ 2026-06-17T17:53:37Z · sha256:35c13bb3906a -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 10 — Logs as business events

<table width="100%"><tr>
  <td align="left"><a href="step-09-plugins.md">← Step 09 — Plugins</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-11-machine.md">Step 11 — ActionProductMachine →</a></td>
</tr></table>

- [box versus print](#box-versus-print)
- [Channels and levels](#channels-and-levels)
- [Templates](#templates)
- [Masking the sensitive](#masking-the-sensitive)
- [Delivery is decided by loggers](#delivery-is-decided-by-loggers)
- [box and plugins](#box-and-plugins)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

"Payment declined by the limit" is a business event, and [plugins](step-09-plugins.md) do not see it: they observe the mechanics of execution, not the meaning of the domain. For such events the operation has `box` — a structured logger we briefly met back in the [first chapter](step-01-action-and-pipeline.md). This is the second half of observation: plugins record *how* execution went, `box` records *what meaningful thing happened* in the domain.

The key difference from the usual `logger.info()` — a `box` event carries a **level** and is addressed to a **channel**, and who delivers it where is not decided by the operation code.

[▶ Try in Colab](https://drive.google.com/file/d/18-WlAwBhToJNkGoGiXYTYgQsrgVTiSQm/view?usp=drive_link) · [Open in project](../../examples/step_10_logs/01_logging_sensitive.py)

---

## box versus print

`print` puts a context-free string into a stream: which operation and step wrote it, how important it is, whether it can be filtered — all unknown. `box.info/warning/critical(...)` gives birth to an **event** — it carries the channel, level, domain, operation name, and aspect name. Such an event can be filtered, routed to different stores, exported. That is why inside aspects you write through `box`, not `print`.

The level is chosen by the method name: `box.info`, `box.warning`, `box.critical`.

## Channels and levels

The first argument to `box` is the **channel**, the semantic address of the event. There are five channels, and they can be combined with `|`:

| Channel | Meaning |
|---------|---------|
| `Channel.business` | a domain business event |
| `Channel.security` | a security event |
| `Channel.compliance` | a regulatory trail |
| `Channel.debug` | diagnostics |
| `Channel.error` | an error event |

```python
await box.info(Channel.business | Channel.security, "Login from new device: {%var.user}", user=params.username)
```

The channel and level are the **address and importance**: by them loggers decide what to pick up (for example, only `business` events at `critical` level). *(A `client` channel for end-user notifications is planned, see ROADMAP.)*

## Templates

The second argument is a template with substitution. `{%var.name}` inserts the passed value, `{%var.name|cyan}` also colors it in the terminal. Besides `var`, other namespaces are available — for example, `{%params.field}`. There are also conditional inserts `iif` with color functions:

```python
await box.info(
    Channel.business,
    "Info: {iif({%var.amount} > 1000; red('large transaction'); green('normal transaction'))}",
    amount=params.amount,
)
```

One restriction is privacy: any path segment starting with `_` is blocked in a template at any nesting level (`{%params.user._secret}` → `LogTemplateError` on render). Need to show a value in a log — declare a public `@property`.

## Masking the sensitive

A public property can be shown in a log **masked** — with the `@sensitive` decorator on its getter (which is why `@property` is on the outside, `@sensitive` inside):

```python
class LoginParams(BaseParams):
    username: str = Field(description="Username")
    amount: float = Field(description="Transaction amount")
    _api_token: str = PrivateAttr(default="")     # private — won't reach a template

    @property
    @sensitive(True, max_chars=3, char="*", max_percent=50)
    def api_token(self) -> str:
        return self._api_token
```

When the logger renders `{%params.api_token}`, the value is masked: a short prefix is shown, the rest is hidden. The `@sensitive` parameters: `enabled`, `max_chars` (how many chars to show), `char` (the mask character), `max_percent`. So you get two independent protection layers: the `_` block guards against accidentally printing internal attributes, while `@sensitive` is an explicit intent to show a field, but in masked form (in detail — in [Intents and invariants](../reference/intents-and-invariants.md)).

**Run:**

```bash
uv run python examples/step_10_logs/01_logging_sensitive.py
```

**Output:**

```text
Sample 03 logging sensitive

  Login: user=alice, amount=500.0
  Info: normal transaction
  Warning: amount 500.0 requires review
  Critical: amount 500.0 requires review
  Token: tok*****
```

All the techniques are visible: substitution (`user=alice`), the conditional `iif` (amount 500 ≤ 1000 → "normal transaction"), the `warning`/`critical` levels, and the masked token `tok*****` — three chars shown, the rest hidden, although `params` holds the full secret.

## Delivery is decided by loggers

Where an event ends up — the console, a queue, Telegram — is not decided by the operation. Loggers are wired to the machine through a coordinator, and each filters the stream by channels and level:

```python
machine = ActionProductMachine(
    log_coordinator=LogCoordinator(loggers=[
        ConsoleLogger(),                       # everything — to the console
        TelegramLogger(                        # only business-critical — to the owner
            channels=[Channel.business],
            min_level=Level.critical,
        ),
    ]),
)
```

The same `box.critical(Channel.business, ...)` goes to both places at once: to the console — like everything, and to Telegram — because it passed the channel and level filter. The operation code knows nothing about either the console or Telegram — it only recorded the fact. And if a coordinator is not wired, `box` events are silently dropped, and the code does not change because of it: logging can be switched on and off from the outside. Your own delivery (Kafka, Slack, PagerDuty) is wired as a [custom logger](../index.md#how-to-write-your-own-extension).

## box and plugins

It is worth separating the two layers of observation once more, so as not to confuse them:

- **`box`** — business events the **operation itself** writes: "what meaningful thing happened in the domain". Addressed to channels, filtered by loggers.
- **[Plugins](step-09-plugins.md)** — technical observation of the **mechanics**: which steps ran, how long they took, where it failed.

They do not replace each other. We saw the same distinction in the [`state` x-ray](step-02-state-as-x-ray.md): a business event answers the question of meaning, a plugin's observation — the question of mechanics.

## Invariants

- **Inside aspects — `box`, not `print`.** The event carries the channel, level, domain, operation, and aspect.
- **Channel and level are mandatory.** The first argument is a `Channel` (combined with `|`); the level comes from the method name (`info`/`warning`/`critical`).
- **Template privacy.** A path segment starting with `_` is blocked → `LogTemplateError` on render.
- **Masking is explicit.** `@sensitive` on a `@property` getter (order: `@property` outside, `@sensitive` inside); shows a prefix, hides the rest.
- **Delivery is separated.** Loggers filter by channels/level; without a coordinator events are silently dropped; the operation code knows nothing of delivery.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why logs are separated from observing the mechanics is in the [Philosophy](../explanation/philosophy.md).

## Summary

`box` is the operation's own voice about business events: a structured event with a channel, level, and context instead of a context-free `print` string. Templates substitute and color values, `iif` branches the text, private names are blocked, and `@sensitive` masks what may be shown only in part. Where to deliver is decided by loggers, by channel and level, and the operation code does not know about it. Together with plugins this gives two independent layers of observation: meaning (`box`) and mechanics (plugins).

With this the core — the **Business logic** part — is assembled: the operation, state, access, sagas, dependencies, context, cache, plugins, and logs. Next — **[Service](../index.md#iii-service)**: how to expose the same operation outward over HTTP and MCP.

---

## Review questions

1. How does `box.info` differ from `print` and `logger.info`? What does a `box` event carry?
2. What are a channel and a level, and what are they for? How do you combine channels?
3. What happens to `{%params._api_token}` in a template and why? How do you correctly show a value?
4. How does `@sensitive` mask a field, and why is `@property` on the outside and `@sensitive` inside?
5. Who decides where an event goes? What happens if you do not wire a log coordinator?
6. How do `box` and plugins differ as observation layers? Why does one not replace the other?

> **Exercise.** In `01_logging_sensitive.py` change `amount` to a value greater than 1000 and watch the `iif` branch switch to `red('large transaction')`. Then wire a second logger filtered to only `Channel.security` and the `critical` level, add `box.critical(Channel.security, ...)` to the aspect, and confirm that only the right event reaches that logger, while everything reaches the console.

---

<table width="100%"><tr>
  <td align="left"><a href="step-09-plugins.md">← Step 09 — Plugins</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-11-machine.md">Step 11 — ActionProductMachine →</a></td>
</tr></table>
