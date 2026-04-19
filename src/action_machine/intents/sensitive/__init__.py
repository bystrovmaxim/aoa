# src/action_machine/intents/sensitive/__init__.py
"""PII masking: ``@sensitive`` on properties for log template resolution."""

from action_machine.intents.sensitive.sensitive_decorator import sensitive

__all__ = ["sensitive"]
