# Contract: the example checks

What a writer of a page or an example can rely on, and what fails a pull request.

## Fragment mark

````markdown
```python
# Fragment: the method of an action; the action is in examples/step_01_Action_and_pipeline/01_hello_world.py.
async def greet_summary(self, params, state, box, connections): ...
```
````

The first line of the block, `# Fragment: ` and a reason ending with a period. A block with this line is not run; one without it must run.

## Shown output

````markdown
```python
print(order.total)
```

```text
1500.0
```
````

Between the two blocks: nothing, or one sentence ending with a colon.

## Colab button

```markdown
[▶ Try in Colab](https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/examples/step_01_Action_and_pipeline/01_hello_world.ipynb)
```

## Install cell

The first code cell of every notebook:

```text
!pip install aoa-action-machine aoa-fastapi-adapter
```

## What a failure names

| Check | A failure names |
| --- | --- |
| Scripts | the script, its exit code, its output |
| Notebooks | the notebook and the failing cell; or the first line it prints that its script does not; or the import its install cell misses |
| Page blocks | the page and the block's line, and the error or the differing output |
| Links | the page, the line and the address |

## Where they run

`uv run --extra dev pytest tests/examples -n auto`, a step of `scripts/check_run.py`, and so of CI's check run.
