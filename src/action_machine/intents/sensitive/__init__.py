# src/action_machine/intents/sensitive/__init__.py
"""
PII masking: ``@sensitive`` on properties for log template and graph interchange rows.
"""

from action_machine.intents.sensitive.sensitive_decorator import sensitive
from action_machine.intents.sensitive.sensitive_intent import SensitiveIntent
from action_machine.intents.sensitive.sensitive_intent_resolver import SensitiveIntentResolver

__all__ = ["SensitiveIntent", "SensitiveIntentResolver", "sensitive"]
