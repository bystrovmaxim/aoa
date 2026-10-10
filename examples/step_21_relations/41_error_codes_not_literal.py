"""Codes must be written as a Literal.

What does the marker check before any model is built?
Run from the repository root:
    uv run python examples/step_21_relations/41_error_codes_not_literal.py
"""

from typing import Literal

from aoa.action_machine.domain import Classifier


def main() -> None:
    """Run this one learning experiment."""
    try:
        Classifier("media", ["first"])
    except TypeError as error:
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The invalid marker was accepted")

    marker = Classifier("media", Literal["first"])
    print("Corrected:", marker.code_values)


if __name__ == "__main__":
    main()
