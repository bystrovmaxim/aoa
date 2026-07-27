# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/forbidden_object.py
"""The one refusal for both "no such object" and "this object is not yours"."""

from __future__ import annotations

from typing import Final

from aoa.action_machine.intents.access_control.fail_security_verdict import FailSecurityVerdict

# The two cases must be indistinguishable: if they differ, someone can try IDs one by one
# and learn which objects exist for other people.
#
# Decide both in a single condition, not in two steps:
#
#     if order is None or order.owner != caller:
#         return FORBIDDEN_OBJECT
#
# Two separate branches would return the same verdict today but leak later. They get
# edited at different times, so one of them eventually gets a more specific message;
# and the "missing" branch returns without doing the ownership lookup, so it answers
# faster -- the same leak, measured on the clock instead of read in the text.
#
# Once ownership is confirmed, a specific reason is safe: the caller already proved
# the object is theirs, so a precise message tells them nothing about anyone else.
FORBIDDEN_OBJECT: Final = FailSecurityVerdict("FORBIDDEN_OBJECT")
