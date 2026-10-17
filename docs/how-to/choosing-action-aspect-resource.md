# Action, aspect or resource: choose by responsibility

[Contents](../index.md)

Suppose a request reserves stock. It needs to read the current quantity, decide
whether the request is allowed, and update storage. These tasks belong together
in the scenario, but they have different responsibilities.

A **resource** provides access to storage: read the quantity and perform the update.
An **action** defines the business operation: accept or refuse the reservation and
return a result. An **aspect** is one named step inside that action, such as checking
the available quantity. Splitting one action into aspects describes its execution;
extracting another action creates an independently callable operation.

## A resource is not defined by how long it lives

Choose a resource for database, file, queue or API access. It may hold a session for
one call or wrap a shared client. A temporary database session is still a resource.
A long-lived arbitrary object is not automatically a resource: first identify which
external access it provides.

Then choose its owner. A per-call database resource is created inside
`PerCallConnection(factory, finalize)` and released after the call. A shared pool
belongs to service startup and shutdown. These lifetimes are separate from the
business decision. [Step 17](../tutorials/step-17-connections.md) demonstrates them.

## Keep the decision in the action

In [the inventory example](../../examples/step_19_resource/01_resource.ipynb), the
resource exposes get_stock and take. ReserveStockAction compares the available
quantity with the request. With stock 10, reserving 3 returns
`{'reserved': True, 'remaining': 7}`. In the [refusal case](../../examples/step_19_resource/02_refusal.ipynb),
reserving 11 returns `{'reserved': False, 'remaining': 10}` without changing storage.
The two cases run independently so each explains one outcome.

A resource may still validate transport arguments and report database errors.
“Business decisions belong in actions” does not prohibit every if statement in a
resource. It separates domain policy, such as who may reserve stock, from enforcing
an access contract, such as refusing to use a closed connection.

## Choose an aspect or another action

Use an aspect for a step that belongs to this operation's sequence and uses its
current state. Use a separate action when the work has its own useful input and
result, is invoked independently or reused in other scenarios. Call a child action
through box.run and declare that dependency. Do not extract every small calculation
into an action merely because it can be named.

If a child receives a parent's transactional resource, it receives a restricted
wrapper: it may call only what the resource's own wrapper delegates, and it cannot
commit, roll back or close the parent's connection. The standard SQL wrapper has no
`execute()` method; the resource's own wrapper exposes the methods a child needs. This is ownership,
not a different kind of business logic.
See [the actual nested-call example](../../examples/step_19_resource/07_nested_action.ipynb).

Before adding a class, state its job in a sentence. “Read from the database” points
to a resource; “reserve the requested stock” points to an action; “check the available
quantity during reservation” points to an aspect. Then decide how its resources
are acquired and released rather than inferring lifetime from the class name.
