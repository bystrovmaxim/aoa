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

"""

from action_machine.intents.sensitive import sensitive
from action_machine.logging.channel import Channel, channel_mask_label, validate_channels
from action_machine.logging.console_logger import DEFAULT_LEVEL_FG_PREFIX, ConsoleLogger
from action_machine.logging.domain_resolver import domain_label, resolve_domain
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.level import Level, level_label, validate_level
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from action_machine.logging.scoped_logger import ScopedLogger
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
