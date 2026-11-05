# Quickstart: check the change

From the repository root.

1. Declaration cases 2.1–2.3, 2.5, 2.6:

   ```bash
   uv run pytest packages/aoa-action-machine/tests/action_machine/intents/entity/test_entity_resource_decorator.py -q
   ```

2. Relations across resources (2.4), every link kind and the state type:

   ```bash
   uv run pytest packages/aoa-action-machine/tests/action_machine/graph/test_entity_resource_validator.py -q
   ```

3. The graph: the edge, the domain from the resource, protocol 1.6, the graph-build refusals:

   ```bash
   uv run pytest packages/aoa-action-machine/tests/action_machine/graph/test_entity_resource_graph.py tests/scripts/test_schema_copies.py -q
   ```

4. The demo: every entity has one `entity_resource` edge, none crosses resources, `graph.json` is current:

   ```bash
   uv run --extra dev python -m aoa.demo.build_graph > /tmp/g.json && python3 -c "import json,collections;g=json.load(open('/tmp/g.json'));print(g['schema_version'],collections.Counter(e['type'] for e in g['edges'])['entity_resource'],sum(n['type']=='Entity' for n in g['nodes']))"
   ```

   Expected: `1.6 N N` — as many edges as entities.

5. The tutorial: `uv run python examples/step_22_entity/13_resource_required.py` prints the refusal of case 2.1, and every example still runs.

6. Everything: CI's closing check run on the pull request.
