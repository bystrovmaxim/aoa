"""Shared test-support fixtures for the aoa-action-machine test suite.

The package's own tests import the sample domain via
``tests.support.domain_model`` (subpackage moved here from the former
``tests/action_machine/scenarios/domain_model``).

The resource lifecycle tests import the connection harness from
``tests.support.fake_pool``: a fake pool and a fake connection that reproduce
the driver's one-operation-at-a-time rule, so that concurrency, exhaustion,
cancellation and finalization are all exercised with no database running.
"""
