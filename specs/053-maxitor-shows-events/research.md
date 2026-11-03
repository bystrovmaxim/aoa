# Research: Maxitor shows events

## Drawing

- **Decision**: Graphviz through the shell the Use case diagram uses.
- **Rationale**: pan, zoom, rooms and determinism checks already exist there.
- **Alternatives**: Sigma, meant for the large map; a hand-made list, which cannot show links at a glance.

## Comparison

- **Decision**: reuse the graph comparison; #334 already reports events and `@emits` edges like any other element.
- **Rationale**: no second comparison to keep in step.
- **To confirm in phase 1**: how the client marks a diagram's rows from a comparison; the Use case diagram is the model.

## Bands

- **Decision**: "Not emitted" is computed per domain: in `domain_event`, with no `@emits` from a method of this domain.
- **Rationale**: an event of a vocabulary may be emitted elsewhere, and this page speaks of this domain.

## Domains of an event

- **Decision**: domains joined by `domain_event`, plus the domains of the methods that emit it; the card says which of them hold it in a vocabulary.
- **Rationale**: mode 2 events have no `domain_event` edge.
