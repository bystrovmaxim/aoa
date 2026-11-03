// src/api/eventsExplorer.ts
import { graphFetch, type GraphRead } from "@/api/client";
import type { EventsExplorerPayload } from "@/model/eventsExplorer";

/** The whole events graph of the explorer (spec 055), of the version ``read`` names when one is given. */
export async function fetchEventsExplorer(read?: GraphRead): Promise<EventsExplorerPayload> {
  const response = await graphFetch("/api/v1/events-explorer", undefined, read);
  if (!response.ok) throw new Error(`Events explorer request failed (${response.status}): ${response.statusText}`);
  const body = (await response.json()) as { events_explorer?: EventsExplorerPayload };
  if (!body.events_explorer) throw new Error("Events explorer response missing events_explorer");
  return body.events_explorer;
}
