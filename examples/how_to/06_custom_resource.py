"""A custom resource releases its handle, not its data.

The external storage is represented by a list supplied by the caller. The resource controls access to it for one call.

Run: uv run python examples/how_to/06_custom_resource.py
"""

import asyncio
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection

class NotesDomain(BaseDomain):
    """Group the custom resource example."""
    name = "notes"
    description = "Notes transport"

@meta(description="Append notes to a supplied store", domain=NotesDomain)
class NotesResource(BaseResource):
    """Expose storage access with an explicit usable interval."""
    def __init__(self, storage, events):
        """Remember the external storage and lifecycle log."""
        self.storage = storage
        self.events = events
        self.opened = False
    def get_wrapper_class(self):
        """Allow direct use of this non-transactional teaching store."""
        return None
    async def open(self):
        """Make the handle usable."""
        self.opened = True
        self.events.append("open")
    async def append(self, note):
        """Write through the open handle."""
        if not self.opened:
            raise RuntimeError("Resource is not open")
        self.storage.append(note)
        return len(self.storage)
    async def close(self):
        """Release this handle without deleting stored data."""
        self.opened = False
        self.events.append("close")


async def main():
    """Run this case and verify its observable result."""
    storage = []
    events = []
    async with connection_scope({"notes": PerCallConnection(
        lambda: NotesResource(storage, events), lambda resource: resource.close(),
    )}) as connections:
        count = await connections["notes"].append("hello")
        print("written:", count)
    assert storage == ["hello"]
    assert events == ["open", "close"]
    print("stored after close:", storage)
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
