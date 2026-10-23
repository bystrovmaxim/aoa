# Completed dictionary values: verification status

Comparison base: `origin/main`, merge-base `69f430de4a156c8ce3b81c234003df89d44ada6e`. The review included the branch history, staged changes, unstaged changes and new example files. Behavior was checked on the current working tree rather than inferred from an issue description.

## Previously reported defects are resolved

The two earlier reproductions no longer publish invalid members: a value outside `Literal` choices and null for a non-nullable union raise `ValueError` while the dictionary class is created. Booleans are distinguished from integers for literal choices and integer properties. Tuple checks preserve the failing item index. A property annotated only `None` is refused during annotation checking; a nullable union or a literal explicitly listing `None` can still accept null.

The old reproducer stopped at its first class definition under the corrected code, so it could no longer demonstrate both outcomes. It has been replaced by [independent executable refusals and accepted neighbors](../how-to/dictionary-validation-and-export.md#migrate-completed-values), with exact outputs and matching notebooks.

## Example organization

Twelve small completed-value examples are consolidated into four scenarios: literal choices, union nullability, tuple-item validation and property declarations. Each script contains its related refusals and accepted neighbors; each notebook presents those cases as sequential cells. The behavior coverage remains, while the reader opens four examples instead of twelve.

## Evidence

The dictionary property and serialization-schema test suites passed: 57 tests. All 47 dictionary scripts and all 47 notebooks executed successfully with matching output. Notebook Python cells were executed in fresh Python processes and their outputs and execution counts were saved; a Jupyter kernel was not used.

Three adversarial checks restored one old function at a time in an isolated process. The literal regression test failed while its accepted neighbor passed; the null-union test failed while its nullable neighbor passed; the bool/int regression test failed while all nine scalar neighbors passed. These mutations never wrote source files.

All 12 complete Python blocks in the dictionary tutorial and how-to were run from clean temporary files and their output matched exactly. All 149 local links in the touched guide, tutorial, invariant reference and report resolved. Existing source changes were preserved. No additional code fix is established by this verification; it is not a claim that every possible annotation combination has been audited. The full repository check runner is outside this scoped verification and was not executed.

See the [dictionary tutorial](../tutorials/step-20-dictionaries.md), [migration and refusals](../how-to/dictionary-validation-and-export.md), and [invariant reference](../reference/intents-and-invariants.md).
