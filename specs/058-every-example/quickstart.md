# Quickstart: proving every example runs

Run from the repository root.

1. All example checks at once:

   ```bash
   uv run --extra dev pytest tests/examples -n auto
   ```

   Expected: every test passes; none is skipped or marked as an expected failure.

2. One kind at a time: `tests/examples/test_examples_run.py`, `test_notebooks.py`, `test_page_blocks.py`, `test_example_links.py`.

3. Adversarial checks — each must fail and name the example, then be undone:

   - remove the `Connections` import from the first code cell of `examples/step_01_Action_and_pipeline/01_hello_world.ipynb`;
   - change one line of a shown output in `docs/tutorials/step-23-dictionaries.md`;
   - remove the `# Fragment:` line of a fragment on any page;
   - point one "Try in Colab" button at a notebook that does not exist;
   - drop a package the notebook imports from its install cell.

4. In Colab, open any button of `docs/tutorials/step-01-action-and-pipeline.md` and run all cells: the install cell installs the packages and the notebook finishes.
