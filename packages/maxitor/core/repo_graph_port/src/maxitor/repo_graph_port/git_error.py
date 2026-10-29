# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/git_error.py
"""
GitError — a git command that did not do what it was asked.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The mirror runs ``git``; when a command fails or runs out of time, the caller
learns which command it was and what git said, in one exception.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``GitMirror`` ──git exits non-zero or times out──► ``GitError(command, said)``.
The command is named by its git subcommand only, never by its arguments or
environment, so nothing that authenticates a call reaches a message.
"""

from __future__ import annotations


class GitError(RuntimeError):
    """
    AI-CORE-BEGIN
    ROLE: A failed or timed-out git command.
    CONTRACT: ``command`` is the git subcommand (``log``, ``fetch``…); ``said`` is git's standard error, trimmed.
    AI-CORE-END
    """

    def __init__(self, command: str, said: str) -> None:
        """Keep the subcommand and what git said, and say both in one line."""
        self.command = command
        self.said = said
        super().__init__(f"git {command} failed: {said}")
