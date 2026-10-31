# Research: Maxitor's Full Graph as a Map

Measured on 2026-10-31 on an M3 Max, Chromium with the real GPU, on a generated graph: 30 copies of the stand's graph with links across copies, **96 361 nodes, 146 010 drawn links, 571 areas**. The prototype lived outside the repository. It drew bare circles and lines: no icons, rings, hulls or marks.

## The prototype's numbers

| Step | Measured | Threshold | State |
|---|---|---|---|
| Layout of every area, one thread, WebAssembly | 8.2 s, the largest 0.1 s | | |
| Placing the areas | 0.6 s | | |
| New version laid out, whole | about 9 s | under 1 min | met |
| Overview read | 68 kB, 15 kB gzipped | under 1 MB | met |
| All detail | 16 MB of JSON, against 83 MB for the full graph's answer | | |
| Overview on screen, cold | 1.33 s, one block of 1 047 ms | under 1 s, no block over 100 ms | **missed** |
| Overview on screen, warm | blocks of 91–278 ms | no block over 100 ms | **missed** |
| Zoom and pan, about 1 400 nodes | 120 frames a second, worst frame 33 ms | 60 frames, none over 100 ms | met |
| Zoom and pan, 10 592 nodes and 18 660 links | 120 frames a second, worst 9 ms | | met |
| Zoom and pan, 96 932 nodes and 141 690 links | 120 frames a second, worst 9 ms | | met |
| A domain opens | 27 ms, local server | under 200 ms | met |
| Filter, about 1 400 nodes | 15 ms | under 50 ms | met |
| Filter, 10 592 nodes | 192 ms | under 50 ms | **missed** |
| Filter, 96 932 nodes | 1 511 ms | under 50 ms | **missed** |
| Firefox, headless, 10 592 nodes | opened, 8 ms a frame | | no errors |
| WebKit, headless, 10 592 nodes | opened, 17 ms a frame | | no errors |
| Real Safari | not tested | | **open** |
| Comparison of two versions | 1.8 s, once per pair | | |
| Building the DuckDB of one version | 23.6 s, peak 1.4 GB | | too heavy for the map |

The frame numbers at 97 thousand were taken with the whole graph zoomed out and no labels.

**To measure again.** The prototype passed its settings to Sigma in the wrong place, which the look prototype found: Sigma 4 takes them under `settings`, and hides an element through `visibility`. So the prototype ran with Sigma's default sizes, and its filter timings are of a full refresh, not of a real filter. The frames are unlikely to get worse, but the filter numbers above are estimates until they are taken again in phase 4.

## R1. Sigma.js 4

- **Decision**: draw with Sigma.js 4 (4.0.4, stable, MIT) over graphology, with `@sigma/node-border` for rings and `@sigma/node-image` for icons. Bundle: 115 kB gzipped before those two.
- **Rationale**: frames are met with a large margin. Labels are on the GPU, a click finds its element, and arrows, shadows and custom shader layers are there.
- **Alternatives**: cosmos.gl was not prototyped: its strength, layout on the GPU, is unused here because the server lays out, and its Safari float-blend question is unanswered. Plain WebGL is the fallback for one layer if Sigma misses a threshold.

## R2. Layout: Graphviz on the server, per area

- **Decision**: `sfdp` with `overlap=scale`, each area on its own, using the native Graphviz binary called from a resource. The Docker image installs it, and developers install it with Homebrew. An area's result is stored under the hash of its content, so a version changing one domain lays out one area.
- **Rationale**: measured stable: of 571 areas, only the two whose content changed moved inside. `overlap=scale` matters: without it the picture is a blob.
- **Measured** on the generated graph with native `sfdp`, areas in parallel, with places, assembling and writing: first version **23.2 s**, next version with one domain changed **3.0 s**, one area laid out; a ready overview read in 12 ms, an area in 1 ms. The threshold of 1 minute holds.

## R3. Places of the areas: a registry, not a layout per version

- **Decision**: where each area stands is kept per history. Largest first, each area takes the nearest free spot beside what it links to, on a spiral, in plain Python; a new area does the same; a removed area keeps its place, so a domain only in A stands in free space; an area that outgrows its place moves alone.
- **Rationale**: running `sfdp` on the areas per version fails FR-016. One removed field moved 571 of 571 areas, and rounding the sizes into classes did not help.
- **Consequence**: a place depends on the history, not on the version alone. Inside an area, positions still depend only on its content, as the clarification says.
- **Tested**: a kept area keeps its place to the digit, no rooms overlap, a removed area keeps its place, one that outgrows its room moves alone.
- **Open**: the map is still loose (extent 154 000 on the generated graph). Tighter packing is settled with the look, in phase 5.

## R4. The map does not stand on DuckDB

- **Decision**: the map is built from the graph document and stored; its reads come from what is stored, through a resource, by AOA actions. DuckDB stays for the diagrams that use it.
- **Rationale**: 23.6 s and 1.4 GB per version is the wrong price for reading positions, and the read would not need it.

## R5. Reading in parts

- **Decision**: one read for the overview, one per area, JSON, gzipped. A node's detail stays with the existing reads.
- **Rationale**: JSON was enough: all 571 areas arrived in 125 ms locally, so a binary format would not pay for itself yet.

## R6. Filters

- **Decision**: keep only what is near the view in the browser, about 3 000 nodes, letting the rest go; the panel works from the overview's counts.
- **Rationale**: a filter costs in proportion to what is loaded: 15 ms at 1 400 nodes, 192 ms at 10 600. Sigma's data textures may allow updating one attribute without a full refresh; the first viewer task tries that before anything else.
- **Open**: **SC-003 is not met yet at 10 thousand loaded nodes.**

## R6a. Outlines that follow the filters

- **Decision**: a smooth field over what is left, contoured in the browser. Away from the detail, the browser has no nodes, so the overview carries a **sketch** per area: how many nodes of each type, and in a pair of each status, stand in each cell of a coarse grid. The outline is drawn from the sketch at the far level and from the loaded nodes up close.
- **Rationale**: in the mockup, outlines from the stand's real nodes took 23–95 ms for all 21 areas. The sketch is what lets this work with no node in the browser; it is small because a cell only holds counts, and bundles are recounted the same way, from links per pair of areas and types.
- **Open**: **the sketch is designed, not measured.** Outlines add to the filter's 50 ms, so they may run after the picture has hidden the nodes, within the next frames.

## R6b. Phones and Next.js

- **Decision**: stay with the client as it is. Next.js renders pages on a server and splits bundles; the time here goes into the graph and its drawing, both already moved to the server and the GPU, so it would change neither, and it would add a Node server to run.
- **Phones**: levels help them most, because little is on screen. The browser keeps fewer nodes there, about 1 500 against 3 000 on a desktop, and a simple label layer. **Nothing has been measured on a phone yet**; SC-018 is taken on a real device in T047. The simulator does not stand for a phone's GPU.

## R7. First paint

- **Decision**: the overview's areas are painted at once by a plain canvas layer, and Sigma takes over when ready, so the page shows the map before the WebGL program is compiled.
- **Rationale**: the block is Sigma's start: 91–278 ms warm, about 1 s the first time.
- **Open**: **SC-001 and SC-006 are not met yet.** If this does not reach them, the maintainer decides whether the first opening in a browser may take longer.

## R8. Levels

- **Decision**: the level follows the visible width of the map: thresholds of 9 000 and 2 200 units in the prototype, tuned on the stand.
- **Rationale**: at these thresholds a walk across the map held about 1 400 nodes at most.

## R9. The look

- **Decision**: what today's picture has, and how it is kept:

| Today | On the map |
|---|---|
| Soft coloured domain hulls with name tags | a custom layer (`@sigma/layer-webgl`) or a canvas below the nodes |
| Disks with the type's icon | `@sigma/node-image` |
| Rings of Diff | `@sigma/node-border` |
| Dashed removed nodes and links | custom shader layers |
| Hover label with its stripe | the existing HTML overlay |
| Neighbour glow | node and edge attributes on hover |
| Dotted background | the page's own background |

- **Rationale**: the prototype's picture was bare, and Sigma's defaults are plainer than today's. The look is a task and a gate of its own (FR-009a), before the viewer goes further.
- **Open**: blur and soft hull edges are the riskiest part.

## R10. Rooms and checks

- **Decision**: a new diagram surface for rooms, in the map's own coordinates, as the G6 surface does today. The cross-engine check compares the positions the server gave, which makes it simple, and draws the map in every engine.

## R11. The generated graph

- **Decision**: the generator goes into the repository next to the measuring script, and the measurements run by hand, because their thresholds depend on the machine. The check run keeps the cross-engine check.

## R12. The branch of #291

- **Decision**: taken over: the rules of the comparison, the filter panel's `kindsTitle`, the filters in the address, `edgesMarked` on the counts, `MARK_LOOK`, the stand. Rewritten: the union, on the server. Left behind: the G6 marks, and `@antv/g6` itself once nothing imports it.
