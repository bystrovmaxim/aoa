# src/action_machine/exceptions/aspect_pipeline_error.py
"""AspectPipelineError."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.model.base_state import BaseState


class AspectPipelineError(Exception):
    """
    Internal aspect-pipeline failure wrapper carrying the state active at failure.

    The original exception is stored as ``__cause__``. ``pipeline_state`` is the
    state passed into the aspect call, or the merged state after a successful
    regular aspect when post-aspect plugin emission fails.
    """

    def __init__(self, pipeline_state: BaseState) -> None:
        super().__init__()
        self.pipeline_state = pipeline_state
