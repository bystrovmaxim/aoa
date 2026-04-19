# src/action_machine/logging/__init__.py
"""
ActionMachine logging package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Single import surface for the logging subsystem: channel/level masks, scoped
emit API, coordinator broadcast, optional per-logger subscriptions, template
substitution, and sensitive-field masking.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every user log call uses ``info`` / ``warning`` / ``critical`` with a
  mandatory ``Channel`` as the first argument. There is no legacy ``debug`` /
  ``error`` log API.
- ``ScopedLogger`` builds one ``var`` dict per message and performs one
  ``LogCoordinator.emit`` per call. Reserved keys ``level``, ``channels``,
  ``domain``, ``domain_name`` are set by the system, not user kwargs.
  ``level`` / ``channels`` are ``LogLevelPayload`` / ``LogChannelPayload``.
- ``LogCoordinator.emit`` validates ``var`` (payload types, level bit count,
  non-zero channels, ``domain`` type or ``None``) before substitution and fan-out.
- Loggers filter with ``subscribe`` / ``unsubscribe`` (``LogSubscription``),
  not regex ``filters=``. No subscriptions means accept all messages.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Developer code
         │
         │  box.info(Channel.debug, "msg", key=val)
         ▼
    ┌─────────────┐
    │ ScopedLogger │─── domain (from caller, e.g. resolve_domain; set at construction)
    │              │─── level  (from method name)
    │  _emit()     │─── channels (from first argument)
    └──────┬──────┘
           │  one emit call
           ▼
    ┌──────────────┐
    │LogCoordinator│─── validate var (level, channels, domain)
    │              │─── substitute templates ({%var.*}, {iif(...)})
    │  emit()      │─── broadcast to all loggers
    └──┬───────┬───┘
       │       │
       ▼       ▼
    ┌──────┐ ┌──────┐
    │Logger│ │Logger│─── subscribe("key", channels=..., levels=..., domains=...)
    │  A   │ │  B   │─── match: any subscription matches (OR) → accept
    └──────┘ └──────┘    no subscriptions → accept all

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS (SHORT)
═══════════════════════════════════════════════════════════════════════════════

- ``LogCoordinator`` — bus; substitution; validates ``var``; calls all loggers.
- ``ConsoleLogger`` — stdout; indent; optional ANSI; base truecolor by
  ``LogLevelPayload.mask``, re-applied after full SGR resets inside the line;
  override via ``level_fg_prefixes``; filtering via ``subscribe``.
- ``BaseLogger`` / ``LogSubscription`` — OR across subscriptions, AND inside one rule.
- ``ScopedLogger`` — aspect/plugin logger; ``domain`` from constructor.
- ``LogScope`` — kwargs-backed coordinates for ``{%scope.*}``.
- ``VariableSubstitutor`` / ``ExpressionEvaluator`` — ``{%namespace.path}``, ``{iif}``.
- ``sensitive`` — property decorator for masking in templates.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Nest level in templates::

    from action_machine.logging import Channel

    await box.info(
        Channel.business,
        "[nest {%scope.nest_level}] payment step",
    )

Plugin handler with ``log``::

    @on("global_finish", ".*")
    async def on_finish(self, state, event, log):
        await log.info(
            Channel.debug,
            "[{%scope.plugin}] action {%scope.action} done at {%scope.nest_level}",
        )
        return state

Handlers with signature ``(self, state, event)`` do not receive ``log``.

═══════════════════════════════════════════════════════════════════════════════
CHANNEL × LEVEL MATRIX (REFERENCE)
═══════════════════════════════════════════════════════════════════════════════

**Levels (``Level``)**

+----------------+----------+-----------------------------+------------------------------------------+
| Value          | Name     | Console (``level_label``)   | Meaning                                  |
+================+==========+=============================+==========================================+
| ``Level.info`` | info     | INFO                        | Normal event                             |
+----------------+----------+-----------------------------+------------------------------------------+
| ``Level.warning`` | warning | WARNING                  | Needs attention, not urgent              |
+----------------+----------+-----------------------------+------------------------------------------+
| ``Level.critical`` | critical | CRITICAL             | Needs fast response                      |
+----------------+----------+-----------------------------+------------------------------------------+

**Channels (``Channel``)**

+-------------------+--------+---------------------------+---------------------------+
| Value             | Mask   | Topic                     | Typical audience          |
+===================+========+===========================+===========================+
| ``Channel.debug`` | 00001  | Debug, tracing            | Developers                |
+-------------------+--------+---------------------------+---------------------------+
| ``Channel.business`` | 00010 | Orders, payments, users | Product, analytics        |
+-------------------+--------+---------------------------+---------------------------+
| ``Channel.security`` | 00100 | Auth, roles, attacks    | Security, SOC             |
+-------------------+--------+---------------------------+---------------------------+
| ``Channel.compliance`` | 01000 | Audit, PII              | Compliance, legal         |
+-------------------+--------+---------------------------+---------------------------+
| ``Channel.error`` | 10000 | Failures, infra           | Developers, SRE           |
+-------------------+--------+---------------------------+---------------------------+

**Expanded matrix (channel × level — guidance)**

+------------+------------+----------------------------------------+----------------------------------------+
| Channel    | Level      | Message type / intent                  | Recipients / action                    |
+============+============+========================================+========================================+
| DEBUG      | INFO       | Technical detail (SQL ms, entry)       | Dev console                            |
+------------+------------+----------------------------------------+----------------------------------------+
| DEBUG      | WARNING    | Suspicious slowness, suboptimal query  | Log file + team alert                  |
+------------+------------+----------------------------------------+----------------------------------------+
| DEBUG      | CRITICAL   | Broken invariant / bad internal state | Log + alerts in test envs             |
+------------+------------+----------------------------------------+----------------------------------------+
| BUSINESS   | INFO       | Business events (order created, paid)  | Queues → analytics                     |
+------------+------------+----------------------------------------+----------------------------------------+
| BUSINESS   | WARNING    | Stuck order, uncertain payment         | Product alerts                         |
+------------+------------+----------------------------------------+----------------------------------------+
| BUSINESS   | CRITICAL   | Mass checkout failure                  | Pager / on-call manager                |
+------------+------------+----------------------------------------+----------------------------------------+
| SECURITY   | INFO       | Successful login, role change          | SIEM audit                             |
+------------+------------+----------------------------------------+----------------------------------------+
| SECURITY   | WARNING    | Many failed logins from one IP         | SOC alert, ticket                      |
+------------+------------+----------------------------------------+----------------------------------------+
| SECURITY   | CRITICAL   | Exploit attempt                        | CISO alert, block IP                   |
+------------+------------+----------------------------------------+----------------------------------------+
| COMPLIANCE | INFO       | PII export on request                  | Immutable log (GDPR/PCI)               |
+------------+------------+----------------------------------------+----------------------------------------+
| COMPLIANCE | WARNING    | Large export (>1000 rows)              | DPO notification                       |
+------------+------------+----------------------------------------+----------------------------------------+
| COMPLIANCE | CRITICAL   | Access without consent                 | DPO + legal                            |
+------------+------------+----------------------------------------+----------------------------------------+
| ERROR      | INFO       | Handled error (e.g. retry recovered)   | Log aggregator                         |
+------------+------------+----------------------------------------+----------------------------------------+
| ERROR      | WARNING    | Partial outage, degradation            | Ticket automation                      |
+------------+------------+----------------------------------------+----------------------------------------+
| ERROR      | CRITICAL   | Service down, 500 in prod              | Pager / SRE + restart                  |
+------------+------------+----------------------------------------+----------------------------------------+

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Template resolution raises ``LogTemplateError`` on unknown variables or bad
  ``iif``; treated as developer bugs.
- Logger ``write`` failures are not swallowed by the coordinator.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public logging package entrypoint.
CONTRACT: Exports channel/level/subscription/coordinator/scoped logging APIs.
INVARIANTS: Channel required on emit; coordinator validates var; subscriptions not regex.
FLOW: ScopedLogger → LogCoordinator → BaseLogger.match_filters → write.
FAILURES: template errors immediate; logger errors propagate.
EXTENSION POINTS: custom BaseLogger subclasses; coordinator.add_logger.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.logging.channel import Channel, channel_mask_label, validate_channels
from action_machine.logging.console_logger import DEFAULT_LEVEL_FG_PREFIX, ConsoleLogger
from action_machine.logging.domain_resolver import domain_label, resolve_domain
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.level import Level, level_label, validate_level
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.intents.sensitive import sensitive
from action_machine.logging.subscription import LogSubscription
from action_machine.logging.variable_substitutor import VariableSubstitutor

__all__ = [
    "DEFAULT_LEVEL_FG_PREFIX",
    "Channel",
    "ConsoleLogger",
    "ExpressionEvaluator",
    "Level",
    "LogChannelPayload",
    "LogCoordinator",
    "LogLevelPayload",
    "LogScope",
    "LogSubscription",
    "ScopedLogger",
    "VariableSubstitutor",
    "channel_mask_label",
    "domain_label",
    "level_label",
    "resolve_domain",
    "sensitive",
    "validate_channels",
    "validate_level",
]
