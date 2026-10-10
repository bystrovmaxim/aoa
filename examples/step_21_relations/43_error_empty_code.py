"""A code must not be blank.

What does the marker check before any model is built?
Run from the repository root:
    uv run python examples/step_21_relations/43_error_empty_code.py
"""

from typing import Literal

from aoa.action_machine.domain import Classifier


def main() -> None:
    """Run this one learning experiment."""
    try:
        Classifier("media", Literal[" "])
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The invalid marker was accepted")

    marker = Classifier("media", Literal["first"])
    print("Corrected:", marker.code_values)


if __name__ == "__main__":
    main()
