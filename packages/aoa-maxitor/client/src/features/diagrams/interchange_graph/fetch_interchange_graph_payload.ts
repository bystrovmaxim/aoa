// packages/aoa-maxitor/client/src/features/diagrams/interchange_graph/fetch_interchange_graph_payload.ts
import { apiUrl } from "../../../shared/config/api";
import type { InterchangeGraphG6Payload } from "./types";

type InterchangeGraphApiBody = {
  payload?: InterchangeGraphG6Payload;
};

/** Load interchange topology JSON for the AntV G6 workspace. */
export async function fetchInterchangeGraphPayload(): Promise<InterchangeGraphG6Payload> {
  const url = apiUrl("/api/v1/full-graph");
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Interchange graph request failed (${response.status}): ${text || response.statusText}`);
  }
  const body = (await response.json()) as InterchangeGraphApiBody;
  if (!body.payload || typeof body.payload !== "object") {
    throw new Error("Interchange graph response missing payload");
  }
  return body.payload;
}
