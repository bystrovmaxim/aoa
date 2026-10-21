"""A template has no current status.

Run: uv run python examples/step_22_lifecycle/20_template_current_status.py
"""

from aoa.action_machine.domain import Lifecycle

template = Lifecycle()

for attribute in ("current_state", "current_status"):
    try:
        getattr(template, attribute)
    except RuntimeError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("A template unexpectedly has a current state")
