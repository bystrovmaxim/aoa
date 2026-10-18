"""Probe 1: a renamed, reordered, untyped @summary_aspect is accepted today."""
import asyncio

from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect


@summary_aspect("S")
async def renamed_summary(self, s, p, b, c):
    return None


@regular_aspect("R")
async def reordered_aspect(self, box, params, state, connections):
    return {}


print("summary accepted:", renamed_summary.__name__, "| is coroutine fn:", asyncio.iscoroutinefunction(renamed_summary))
print("regular accepted:", reordered_aspect.__name__, "| is coroutine fn:", asyncio.iscoroutinefunction(reordered_aspect))
