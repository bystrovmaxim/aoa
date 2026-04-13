# tests/scenarios/__init__.py
"""
Cross-layer test scenarios and shared sample domains/actions.

Heavy fixtures that exercise multiple ``action_machine`` packages live under
``tests/scenarios/`` (see ``domain_model/``) so narrow layer tests stay clean.

Subpackages:

- ``dependencies/`` — factory + ``CoreActionMachine`` integration.
- ``graph_with_runtime/`` — coordinator/graph tests that need ``runtime`` or ``integrations``.
- ``intents_with_runtime/`` — intent-layer flows that need ``graph`` or ``runtime``.
"""
