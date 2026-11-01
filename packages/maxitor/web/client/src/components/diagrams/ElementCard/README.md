# ElementCard

**Role:** The one card of Maxitor (spec 043): what an element is, its description, what changed in it in Diff, a table's fields, and a lifecycle's miniature. It opens on hover, or on a tap on a phone.

## Public exports

**`index.ts`** exports **`ElementCard`** and the types **`CardSubject`**, **`CardField`** and **`ElementCardProps`**.

## Files

| File | Responsibility |
|---|---|
| `ElementCard.tsx` | The card: what the diagram knows at once, the rest read when it opens. |
| `LifecycleMiniature.tsx` | A lifecycle fitted into the card; a click opens the full diagram. |
| `src/lib/useHoverCard.ts` | When a card opens and closes: the rest, the stay. |
| `src/lib/lifecycleMiniature.ts` | Reading, drawing and keeping a miniature. |
