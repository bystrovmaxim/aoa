<p align="center">
  <img src="../../../../../../../docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <img src="https://img.shields.io/badge/tests-26-brightgreen" alt="26 tests">
  <a href="https://pypi.org/project/aoa-ocel/"><img src="https://img.shields.io/badge/install-aoa--ocel--plugin-blue?logo=pypi&logoColor=white" alt="pip install aoa-ocel"></a>
  <img src="https://img.shields.io/badge/OCEL-2.0-orange" alt="OCEL 2.0">
</p>

# OCEL export (`aoa.ocel`)

This module exports data in [OCEL 2.0](https://ocel-standard.org/) format. Install with ``pip install aoa-ocel``. It turns Action execution logs into object-centric event logs that Process Mining tools can consume.

<p align="center">
  <img src="../../../../../../../docs/assets/ocel-ocdfg.png" alt="Object-centric process graph (OCEL)" width="900">
</p>

### Viewing logs in OC-PM

After ``await store.close()`` writes JSON, open the file in **[Object-Centric Process Mining (OC-PM)](https://www.ocpm.info/ocel.html)** — a browser app for OCEL JSON/XML logs. Upload the export, then use event/object explorers, OCDFG graphs, filters, and conformance views without extra tooling. See also ``examples/07_ocel.py`` and the Store batch export under ``packages/aoa-examples`` (``archive/logs/ocel.json`` in integration tests).

## How it works

The builder (``OcelPlugin.build_ocel_event``) maps domain entities to ``OcelEvent`` DTOs. **v1 uses E2O only; O2O is not exported.**

We do **not** know in advance which questions process-mining users will ask. Export therefore prefers **reachability** (objects appear in event relationships when the aspect loaded them) over a minimal graph. Filters in PM tools can narrow views later; missing E2O cannot be recovered without re-export.

### `OcelFrame` input

Aspects return one or more `OcelFrame` rows in pipeline state:

| Field | Role |
|-------|------|
| `object` | Root domain entity for this participation row |
| `qualifier` | Required E2O role for the root (non-empty string) |
| `attributes` | Optional event-level attributes (merged across frames; name clash with different values → error) |

### E2O (event → object)

**Rule — loaded relations only:** E2O includes **only relation containers that are loaded on `frame.object` at export time** (`BaseEntity.get_foreign_keys(loaded_only=True)`). Scalar FK columns and relations not loaded on the instance are **not** exported. Nothing is read from the database beyond what the aspect already put on the entity.

**Rule — one hop:** From each `OcelFrame.object`, the builder walks **one level** of loaded relation fields only. It does **not** recurse into peers’ relations.

**Rule — no manual peer frames:** Loaded peers do not require separate `OcelFrame` rows. The builder materializes them automatically.

| Object | E2O qualifier |
|--------|----------------|
| `frame.object` (root) | `frame.qualifier` |
| Each loaded peer from a relation field `field_name` | `{frame.qualifier}.{field_name}` |

`AssociationMany` yields one E2O per peer id, same composite qualifier prefix.

### O2O (object → object)

**v1: not used.** `OcelObject.relationships` stays empty. Structural links are represented only through co-occurrence in E2O for the same event.

### Object attributes

| Source on domain entity | OCEL target |
|-------------------------|-------------|
| Loaded scalars on `frame.object` | `OcelObject.attributes` for the root |
| Loaded lifecycle snapshot on root | root attributes (state string, v1) |
| Loaded scalars on a one-hop peer | that peer’s `OcelObject.attributes` |

Event attributes: ``OcelPlugin`` merges ``OcelFrame.attributes`` across frames; not from entity fields.

### Example — “Doctor signed prescription”

Aspect loads on the doctor entity before wrapping `OcelFrame`:

- `patient` — loaded → **E2O** with qualifier `"Signed prescription.patient"`
- `clinic` where the doctor works — **not loaded** → no E2O for clinic (clinic is context, not a participant in this action)

```text
OcelFrame(doctor, qualifier="Signed prescription")
    │
    ├─ E2O  doctor   qualifier "Signed prescription"
    ├─ E2O  patient  qualifier "Signed prescription.patient"   (loaded FK, one hop)
    └─ (clinic omitted — relation not loaded on doctor)
```

If the aspect **did** load `clinic` on the doctor, the builder would add  
`E2O clinic` with `"Signed prescription.clinic"`. That is valid but may add noise in PM graphs; the aspect controls participation via **partial loading**.

### E2O vs “everything in the database”

| In DB | On framed entity at export | In OCEL v1 |
|-------|----------------------------|------------|
| Order → Customer FK | `customer` loaded | E2O + materialized `OcelObject` |
| Order → Customer FK | `customer` not loaded | absent |
| Scalar `customer_id` only | in `get_scalar_fields()` | object attribute on order, not E2O |

Participation is **not** inferred from SQL or undeclared fields — only from what the aspect loaded on the entity inside `OcelFrame`.

## OcelPlugin

Register on ``ActionProductMachine(plugins=[OcelPlugin(store=resource)])``. The store must be opened by the owning action connection; the plugin only calls ``add_event``.

```python
from aoa.ocel import OCEL_FRAMES_KEY, OcelFrame, OcelPlugin

@regular_aspect("Export")
@result_instance(OCEL_FRAMES_KEY, OcelFrame, required=False)
async def ocel_aspect(self, params, state, box, connections):
    order = ...  # partial load: only relations that should participate
    return {
        OCEL_FRAMES_KEY: [
            OcelFrame(
                object=order,
                qualifier="Created order with identifier",
                attributes=[OcelAttribute(name="domain", value="shop")],
            ),
        ]
    }
```

On each trace, ``OcelPlugin`` reads ``GlobalFinishEvent.all_aspect_states`` (and optional frames on ``result``), builds one ``OcelEvent``, and appends to the store. The plugin does not mutate pipeline state.

