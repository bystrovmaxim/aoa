# tests/examples/round_trip_runner.py
"""
Run an example as ``python <script>`` would, and read back every Result it builds.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Rule 2 of #399 (issue #409): a Result read back from its own JSON has the same
observable state. Every example runs through this runner, so every Result an
example builds is read back without running the example twice. The runner records
each Result that ``__init__``, ``model_validate`` or ``model_validate_json``
returns; when the script ends it stops recording, reads each one back
(``model_validate_json(model_dump_json())``) and compares them with
``observable_difference``. A difference, or a Result that cannot be written or
read back, is printed to stderr and the runner exits 1. The script's own output
and exit code are otherwise unchanged.

Usage::

    python tests/examples/round_trip_runner.py examples/<chapter>/<script>.py
"""

from __future__ import annotations

import runpy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aoa.action_machine.domain import observable_difference
from aoa.action_machine.model import BaseResult

_RECORDED_CLASSMETHODS = ("model_validate", "model_validate_json")
_INIT = "__init__"


class _Recorder:
    """Record every Result built while it is installed."""

    def __init__(self) -> None:
        self.built: list[BaseResult] = []
        self._original_init: Callable[..., None] = BaseResult.__init__

    def install(self) -> None:
        """Wrap ``__init__`` and the two validating classmethods of ``BaseResult``."""
        original_init = self._original_init
        built = self.built

        def recording_init(result: BaseResult, /, **data: Any) -> None:
            original_init(result, **data)
            built.append(result)

        setattr(BaseResult, _INIT, recording_init)
        for name in _RECORDED_CLASSMETHODS:
            setattr(BaseResult, name, classmethod(self._recording(getattr(BaseResult, name).__func__)))

    def _recording(self, original: Callable[..., Any]) -> Callable[..., Any]:
        built = self.built

        def recording(cls: type[BaseResult], *args: Any, **kwargs: Any) -> Any:
            result = original(cls, *args, **kwargs)
            built.append(result)
            return result

        return recording

    def remove(self) -> None:
        """Put ``BaseResult`` back as it was."""
        setattr(BaseResult, _INIT, self._original_init)
        for name in _RECORDED_CLASSMETHODS:
            if name in vars(BaseResult):
                delattr(BaseResult, name)


def _differences(built: list[BaseResult]) -> list[str]:
    """Read each distinct recorded Result back from its JSON and describe each one that differs."""
    seen: set[int] = set()
    found: list[str] = []
    for result in built:
        if id(result) in seen:
            continue
        seen.add(id(result))
        name = type(result).__qualname__
        try:
            back = type(result).model_validate_json(result.model_dump_json())
        except (TypeError, ValueError) as exc:  # a failed dump or read-back; ValidationError is a ValueError
            found.append(f"{name} does not read back from its JSON: {type(exc).__name__}: {exc}")
            continue
        difference = observable_difference(result, back)
        if difference:
            found.append(f"{name} reads back different: {difference}")
    return found


def main(script: str) -> int:
    """Run ``script`` as ``python script`` would; return 1 when a Result it built reads back different."""
    path = Path(script).resolve()
    sys.argv = [str(path)]
    sys.path.insert(0, str(path.parent))
    recorder = _Recorder()
    recorder.install()
    try:
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise
    finally:
        recorder.remove()
    found = _differences(recorder.built)
    for line in found:
        print(f"round trip: {line}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
