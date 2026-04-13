# src/action_machine/intents/meta/__init__.py
"""@meta decorator and meta marker mixins for actions and resource managers."""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.meta.meta_intents import ActionMetaIntent, ResourceMetaIntent

__all__ = ["ActionMetaIntent", "ResourceMetaIntent", "meta"]
