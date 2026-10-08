<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 03 — Verifying the caller and their permissions

<table width="100%"><tr>
  <td align="left"><a href="step-02-state-as-x-ray.md">← Step 02 — State</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-04-saga-and-compensations.md">Step 04 — Saga and compensations →</a></td>
</tr></table>

Two managers work with a store's orders. Knowing their names does not establish that either may cancel any order. The system must determine who is calling, what that person may do, and whether permission covers the selected order. A cancellation may also be subject to a shared refund limit.

This chapter develops those questions into AOA code. It assumes basic Python variables, functions, classes, and conditionals, but introduces access-control and AOA terminology as needed. Each example follows a concrete call: where its data comes from, what is checked, and why the shown answer follows.

Examples can be run independently. Each has a standalone script and a notebook with the same actions. The chapter presents shared preparation once, then shows each experiment's complete operation, additional declarations, and invocation. Method bodies and result handling are not replaced with ellipses. Linked files already include their preparation and require no assembly from the chapter.

**Where this sits in the usual vocabulary.** The industry names access control by what a decision is based on, and one AOA cascade covers three of those flavours in one place. **Authentication** establishes *who* is calling; **RBAC** (role-based access control) decides by the roles a caller holds, hierarchy included; **ABAC** (attribute-based access control) decides by attributes of the caller — which is what `when=` is; `guard=` is a shared condition that may read the caller *and* the call's own data, so it can be either an attribute rule or a **precondition** — a limit that applies to everyone alike, such as a refund ceiling, which decides nothing about who is calling; and the declared object rule is **per-object authorization**, a decision about *this* order rather than about orders in general, which systems that follow relationships between objects call ReBAC. What AOA adds is not another flavour but one place for all of them: declared in a single header, answered by a single cascade, observable as one event stream.

**Chapter sections**

- [Authentication and authorization: two different questions](#authentication-and-authorization-two-different-questions)
- [Preparation: the objects involved in a call](#preparation-the-objects-involved-in-a-call)
- [RBAC: a role requirement decides the call](#rbac-a-role-requirement-decides-the-call)
- [A check without execution: asking about a call before making it](#a-check-without-execution-asking-about-a-call-before-making-it)
- [Authentication: where the caller's identity comes from](#authentication-where-the-callers-identity-comes-from)
- [The registry: how a role name becomes a role object](#the-registry-how-a-role-name-becomes-a-role-object)
- [RBAC: which roles may call the operation](#rbac-which-roles-may-call-the-operation)
- [ABAC: conditions on the caller and on the input](#abac-conditions-on-the-caller-and-on-the-input)
- [Authorization and preconditions: where the line is](#authorization-and-preconditions-where-the-line-is)
- [Per-object authorization: may this caller touch this order](#per-object-authorization-may-this-caller-touch-this-order)
- [Two outcomes: a refusal is not a failure](#two-outcomes-a-refusal-is-not-a-failure)
- [The cascade: the order every check runs in](#the-cascade-the-order-every-check-runs-in)
- [Observability: what a plugin sees](#observability-what-a-plugin-sees)
- [Invariants: how a wrong declaration is caught](#invariants-how-a-wrong-declaration-is-caught)
- [Migration: if you used the previous API](#migration-if-you-used-the-previous-api)
- [Check your understanding](#check-your-understanding)

---

## Authentication and authorization: two different questions

A person usually interacts through a client, such as a web interface or mobile application. The client sends a request to a server: “cancel this order.” The server must decide whether to act on it.

The first question is who sent the request. Verifying credentials and establishing the caller's identity is authentication. Merely reading a supplied name would not suffice: any client could claim to be an administrator.

The second question is whether that established caller may make this particular request. That is authorization. The system may know that manager m-1 is calling without yet knowing whether m-1 may cancel ord-001. Successful authentication alone grants no such permission.

Applications group authority into roles, such as manager, auditor, or administrator. Users are assigned roles; operations declare which roles they require. The application defines the roles and their relationships. The word “administrator” has no automatic unlimited authority: declarations and requirements determine its effect.

A matching role may still be insufficient. A manager can work with orders in general while a particular order belongs to someone else. We will begin with role matching, then introduce conditions about the caller, proposed input, and stored order. After those individual rules are understood, we will examine their execution order together.

## Preparation: the objects involved in a call

An operation here means one application action: cancelling an order. AOA describes it with a class derived from BaseAction. ActionProductMachine, called the machine below, reads its declarations, checks access, invokes its steps, and returns a result.

First prepare the input, output, and role. This is the shared portion of the cancellation examples. It serves no requests and cancels nothing yet.

```python
from __future__ import annotations
import asyncio
from pydantic import Field
from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    """Group the order operations."""

    name = "store"
    description = "Order management"


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


class OrderParams(BaseParams):
    """Identify the order to cancel."""

    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    """Report the cancelled order."""

    order_id: str = Field(description="Cancelled order identifier")
```

StoreDomain groups operations in a subject area: order management. AOA calls that group a domain and requires an operation to name one. name and description describe it; the Domain suffix is required.

ManagerRole describes the manager role. Business roles inherit ApplicationRole, provide name and description, and have class names ending in Role. This is a role type, not a user. Different users may hold the same class.

OrderParams defines the input order_id string. OrderResult defines the output, here the same identifier after successful execution. The annotation order_id: str describes a string field; a function annotation such as -> OrderResult describes its expected answer type. An annotation describes data rather than performing an action. These are data models based on Pydantic, which builds objects from supplied fields and validates their description. Field(description=...) documents a field; OrderParams(order_id="ord-001") constructs one call's input.

Caller information is separate from order information. UserInfo contains the user's identity and roles. Context is the call's context: information about the user, request, and surrounding execution conditions. The first experiments set only its user field. The selected order goes in OrderParams; the established caller goes in Context.

For each cancellation experiment, combine this shared portion with that experiment's listing. The listing includes a complete replacement operation and main function; do not accumulate different versions in one file. Standalone listings needing no shared portion are identified explicitly. Run commands refer to repository files that already contain everything.

A Python decorator is the @-prefixed construct before a class or method. It processes that declaration; these AOA decorators record information the machine later reads. @meta binds an operation to a domain and describes it. @summary_aspect marks the final step returning its result. AOA calls steps aspects and their execution sequence a pipeline; initially there is only one step. The machine passes params, state, box, and connections: input, intermediate step state, execution tools, and connections to external resources. The first operation uses only params but retains the required method shape.

BaseAction[OrderParams, OrderResult] binds input and output types. async def and await support operations that may wait for resources. asyncio.run(main()) runs the asynchronous main function from a script; await inside it waits for a completed machine call.


<a id="roles-first"></a>

## RBAC: a role requirement decides the call

### The first operation: a manager and an administrator

The examples explicitly use cache_coordinator=None to disable reuse of previously saved results, so each experiment observes a new call. print makes the experiment visible; the operation itself returns an OrderResult object.

Start with one rule: a manager may request cancellation of an order. An administrator should have the same permission. Declare AdminRole as a subclass of ManagerRole. Python then treats the administrator class as a specialized manager class, and AOA uses that relationship when matching roles.

The listing below is the complete remainder of the first file. Put it after the shared definitions above. It declares the administrator role, the operation, and a main function making two calls. The final two lines run that asynchronous function from an ordinary Python script.

The @check_roles(ManagerRole) line is a Python decorator: it attaches information to the class declaration. Here that information means “the caller must have the manager role.” The machine reads it before calling cancel_summary, so the method does not repeat the access check.

```python
class AdminRole(ManagerRole):
    """Include every manager permission."""

    name = "admin"
    description = "Includes manager permissions"


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """An administrator inherits the manager role."""
    machine = ActionProductMachine(cache_coordinator=None)
    manager = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    admin = Context(user=UserInfo(user_id="a-1", roles=(AdminRole,)))

    result = await machine.run(manager, CancelOrderAction(), OrderParams(order_id="ord-001"))
    print("manager:", result.model_dump())
    result = await machine.run(admin, CancelOrderAction(), OrderParams(order_id="ord-001"))
    print("admin:", result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/01_roles.py) · [Notebook](../../examples/step_03_authorization_and_roles/01_roles.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/01_roles.py
```

Actual output:

```text
manager: {'order_id': 'ord-001'}
admin: {'order_id': 'ord-001'}
```

Read machine.run(manager, CancelOrderAction(), OrderParams(order_id="ord-001")) from left to right: caller information, an operation instance, and its input. await waits for completion. On success the machine returns OrderResult; model_dump converts that model to a dictionary for printing.

manager and admin hold separate Context objects. Each contains UserInfo with the caller's identifier and role classes. The tuple (ManagerRole,) stores the class itself, not the string "manager" or a ManagerRole instance; the comma makes it a one-element tuple. Constructing a Context does not authenticate anyone. Here we deliberately supply the two users as test inputs.

Both calls succeed. The first matches ManagerRole directly; the second succeeds because issubclass(AdminRole, ManagerRole) is True. The reverse is false: a manager does not satisfy an AdminRole requirement. Use role inheritance only when the child role should include all permissions of its parent.

Cancellation is a teaching operation here: its summary returns the order identifier without changing a database. This shows that execution reached the method while keeping storage out of the experiment. The capability demonstrated is inheritance of a role requirement.


<a id="ask-first"></a>

## A check without execution: asking about a call before making it

### Check permission without performing the cancellation

So far we have learned whether access is allowed by actually calling the operation. An interface needs something different: it must decide whether to offer a Cancel button before changing the order.

The machine's check_access_decide method takes the caller, an operation class, and the proposed input. It evaluates access and returns a decision object. Allowed means that the checks permit the call; its dictionary representation contains kind: 'allowed'. This describes permission, not the operation's business result.

Make the distinction observable with a CANCELLED list. The summary method appends an order to that list. This stands in for a database write: if the method runs, the list changes. First ask about access, then execute the same request.

model_dump(mode="json") converts a decision model to a dictionary of simple values suitable for JSON, a text data-exchange format. print below displays the Python dictionary, hence single quotes and None.

```python
CANCELLED = []


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        CANCELLED.append(params.order_id)
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """Checking access does not cancel the order."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("check:", answer.model_dump(mode="json"))
    print("cancelled after check:", CANCELLED)

    await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    print("cancelled after run:", CANCELLED)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/05_machine_check.py) · [Notebook](../../examples/step_03_authorization_and_roles/05_machine_check.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/05_machine_check.py
```

Actual output:

```text
check: {'kind': 'allowed'}
cancelled after check: []
cancelled after run: ['ord-001']
```

The first answer permits the call, but the next line still shows an empty list. The access query did not call cancel_summary. After run, the list contains ord-001: execution has now reached the summary. That difference is the subject of this example.

Notice the parentheses: check_access_decide receives CancelOrderAction, whereas run receives CancelOrderAction(). One argument is a class, the other an instance. The caller and input describe the same proposed call.

A preliminary query skips the operation's pipeline and result cache, but evaluates the access rules themselves. When we later add an ownership rule, asking about access will read the owner as well. Such a rule must not also cancel the order or change other data.

An Allowed answer reserves no permission for later. The order or the user's roles may change between showing a button and clicking it. run evaluates access again, and its caller must handle a refusal even after an earlier Allowed.


<a id="authentication"></a>

## Authentication: where the caller's identity comes from

### How a request becomes a known caller

Now consider where a real application's Context comes from. A client sends a request. The receiving application must verify the client's credentials before recording an established identity in that context.

This example uses a token: a string presented to the server after sign-in. Its format is JWT, which carries data fields and a cryptographic signature used to verify that a trusted party signed the data. Here sub identifies the user, roles lists role names, and exp gives the expiry time. Reading these fields is insufficient; the signature and expiry must first be checked.

The client sends the token in the HTTP Authorization header using the Bearer scheme. HTTP is the request/response protocol, and a header carries additional request information. The Request object below constructs that input in memory, so no server is omitted from the example.

An authentication coordinator organizes this work in AOA: it extracts credentials, verifies them, and builds a Context. JwtAuthCoordinator provides that sequence for JWT. Its role_registry maps role-name strings from a verified token to application role classes: "manager" maps to ManagerRole.

This listing is a complete, separate file and needs no shared definitions. Its demonstration key is used only to create and verify a token within the example.

```python
from __future__ import annotations


import asyncio


import time


import jwt


from starlette.requests import Request


from aoa.action_machine.auth import ApplicationRole


from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


DEMO_KEY = "local-tutorial-key-not-for-production-123456"


async def main() -> None:
    """A verified token becomes a user with role classes."""
    auth = JwtAuthCoordinator(secret_key=DEMO_KEY, role_registry={"manager": ManagerRole})
    token = jwt.encode({"sub": "m-1", "roles": ["manager"], "exp": int(time.time()) + 60}, DEMO_KEY, algorithm="HS256")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/orders/cancel",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
            "query_string": b"",
            "server": ("localhost", 80),
            "scheme": "http",
        }
    )
    context = await auth.process(request)
    print("user:", context.user.user_id)
    print("roles:", [role.__name__ for role in context.user.roles])

    invalid = Request({**request.scope, "headers": [(b"authorization", b"Bearer invalid-token")]})
    print("invalid token:", await auth.process(invalid))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/12_authentication.py) · [Notebook](../../examples/step_03_authorization_and_roles/12_authentication.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/12_authentication.py
```

Actual output:

```text
user: m-1
roles: ['ManagerRole']
invalid token: None
```

jwt.encode first creates a signed token for m-1. int(time.time()) + 60 sets its expiry one minute ahead. The token is placed in a request, and await auth.process(request) returns a context. Printing its user identifier and role-class names produces m-1 and ManagerRole.

The second request replaces the token with invalid-token. The coordinator returns None: it could not establish a caller. This is neither an anonymous Context nor an order-access decision. Current adapters turn this result into AuthorizationError("Authentication required") before calling the machine.

An adapter connects an external protocol to an operation: it receives the request, obtains a context, invokes the machine, and constructs a response. Authentication configured on that adapter therefore happens before an operation's own rules. GuestRole on the operation cannot override mandatory credential verification.

A service intentionally operating without authentication can use NoAuthCoordinator(context=Context()). It returns exactly the supplied context. This is an explicit service configuration, not a fallback that turns invalid credentials into an anonymous user.

See the [FastAPI chapter](step-13-fastapi.md) for HTTP integration. The current [MCP adapter](step-14-mcp.md) passes None to its coordinator rather than an HTTP request, so this Bearer-header extractor cannot be connected to it unchanged.


<a id="role-choices"></a>

## The registry: how a role name becomes a role object

Outside this framework roles travel as names — a token claim, a row, a header from an identity provider. Inside it roles are classes, because the check is `issubclass(user_role, required_role)` and inheritance is what makes "an admin is a manager" true without a second list. The crossing happens in the authenticator, and what does it is a **registry**: a mapping from the name the provider uses to the class this codebase declared.

```python
raw_roles = payload.get(self._roles_claim)
roles = (
    tuple(self._role_registry[name] for name in raw_roles if name in self._role_registry)
    if isinstance(raw_roles, list)
    else ()
)
return UserInfo(user_id=str(user_id), roles=roles)
```

The claim holds strings; what leaves that line, and what every later check sees, is a tuple of classes. The registry is not discovered and not guessed — the application states it, and the coordinator passes it to the authenticator:

```python
auth = JwtAuthCoordinator(
    secret_key=JWT_SECRET,
    role_registry={"admin": AdminRole, "manager": ManagerRole, "auditor": AuditorRole},
    credential_extractor=BearerCredentialExtractor(),
)
```

Three things are worth knowing before relying on it. **A name the registry does not know is dropped, not rejected**: the caller simply does not hold that role, the refusal arrives as `CHECK_ROLES`, and it says nothing about the real reason — so a role that exists in the provider but not here looks exactly like a caller who never had it. **The token itself is fail-closed**: one that cannot be decoded yields no identity at all, and the transport answers for "no identity" instead of entering the engine. And **hierarchy lives in the classes, not in the registry** — mapping `"admin"` to `AdminRole` is enough for a manager requirement to pass when the class subclasses it.

Before deploying, compare the two lists: every name the provider can put in a token has a class here, and every class here has the name the provider uses.

---

## RBAC: which roles may call the operation

### Allow everyone or require a role

A named role is not the only possible requirement. A catalog may be public, while another area requires a user with any assigned role. Neither case needs an artificial business role.

AOA supplies two special requirement classes. GuestRole lets any caller pass the role check, including an anonymous caller. AnyRole requires at least one active role, without specifying which. These classes describe requirements; they are not assigned to users.

Both operations below return the identifier of a viewed order. Only their role requirement differs. Context() supplies an anonymous caller with no roles; member holds ManagerRole. We ask about access three times. A refusal converts to a dictionary with kind='refused', a gate identifying the refusing check, and an optional reason. CHECK_ROLES names the role check.

```python
from aoa.action_machine.auth import AnyRole, ApplicationRole, GuestRole


@meta(description="View an order", domain=StoreDomain)
@check_roles(GuestRole)
class PublicAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(self, params, state, box, connections):
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


@meta(description="View an order", domain=StoreDomain)
@check_roles(AnyRole)
class ProfileAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(self, params, state, box, connections):
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """GuestRole and AnyRole express different requirements."""
    machine = ActionProductMachine(cache_coordinator=None)
    anonymous = Context()
    member = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(anonymous, PublicAction, params)
    print("guest, anonymous:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(anonymous, ProfileAction, params)
    print("any, anonymous:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(member, ProfileAction, params)
    print("any, manager:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/14_guest_and_any.py) · [Notebook](../../examples/step_03_authorization_and_roles/14_guest_and_any.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/14_guest_and_any.py
```

Actual output:

```text
guest, anonymous: {'kind': 'allowed'}
any, anonymous: {'kind': 'refused', 'gate': 'CHECK_ROLES', 'reason': None}
any, manager: {'kind': 'allowed'}
```

The first query is allowed because PublicAction requires no role. The second refuses the same anonymous caller because ProfileAction requires one. The third succeeds because member holds ManagerRole. reason=None means that no additional reason text was supplied; the gate already identifies the unmet role requirement.

AnyRole therefore checks for a role, not merely a nonempty user_id. An identified user with no roles does not qualify. We will also see that silenced roles do not count.

GuestRole does not disable other operation rules: shared conditions and an object check still apply. It also does not bypass the adapter's credential verification.

GuestRole and AnyRole cannot be subclassed or placed in UserInfo.roles. They declare an operation's requirement. That declaration is mandatory: omitting @check_roles causes MissingCheckRolesError when the machine is built. Public access must be chosen explicitly.

### Accept one of several independent roles

A manager and an auditor both need to view orders, but an auditor should not automatically gain the manager's other permissions. Inheritance would express the wrong relationship.

Declare AuditorRole directly from ApplicationRole and give @check_roles the list [ManagerRole, AuditorRole]. Read the list as “manager or auditor.” One matching role is sufficient. Each user in this experiment has only one role so that the alternative nature of the requirement is visible.

```python
class AuditorRole(ApplicationRole):
    """Permit reviewing order operations."""

    name = "auditor"
    description = "Can review orders"


@meta(description="View an order", domain=StoreDomain)
@check_roles([ManagerRole, AuditorRole])
class ViewOrderAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(self, params, state, box, connections):
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """Either listed role is sufficient."""
    machine = ActionProductMachine(cache_coordinator=None)
    manager = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    auditor = Context(user=UserInfo(user_id="a-1", roles=(AuditorRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(manager, ViewOrderAction, params)
    print("manager:", answer.kind)
    answer = await machine.check_access_decide(auditor, ViewOrderAction, params)
    print("auditor:", answer.kind)
    answer = await machine.check_access_decide(Context(), ViewOrderAction, params)
    print("anonymous:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/15_alternative_roles.py) · [Notebook](../../examples/step_03_authorization_and_roles/15_alternative_roles.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/15_alternative_roles.py
```

Actual output:

```text
manager: allowed
auditor: allowed
anonymous: {'kind': 'refused', 'gate': 'CHECK_ROLES', 'reason': None}
```

Both identified callers are allowed even though neither holds both roles. The anonymous caller receives CHECK_ROLES because none of the alternatives matches. The list expresses alternatives, not a requirement to collect every role.

Choose inheritance when a child role should satisfy the parent's requirements everywhere. Choose a list to admit independent roles to this particular operation. Empty lists and strings such as "manager" in place of role classes are rejected.

### Temporarily stop a role from granting access

Sometimes users already hold a role that must temporarily stop granting access. Temporary managers may be suspended while permanent managers keep working. A role mode is a mark on the role class describing how that role is used.

@role_mode(RoleMode.SILENCED) marks a role as silenced. The machine removes it from the user's roles before matching requirements. TemporaryManagerRole below inherits ManagerRole but is silenced; the operation still requires ManagerRole. This isolates the effect of silencing despite valid inheritance.

```python
from aoa.action_machine.intents.role_mode import RoleMode, role_mode


@role_mode(RoleMode.SILENCED)
class TemporaryManagerRole(ManagerRole):
    """Suspend temporary manager permissions."""

    name = "temporary_manager"
    description = "Temporary manager access"


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A silenced role grants no access."""
    machine = ActionProductMachine(cache_coordinator=None)
    active = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    suspended = Context(user=UserInfo(user_id="t-1", roles=(TemporaryManagerRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(active, CancelOrderAction, params)
    print("active:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(suspended, CancelOrderAction, params)
    print("silenced:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/16_silenced_role.py) · [Notebook](../../examples/step_03_authorization_and_roles/16_silenced_role.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/16_silenced_role.py
```

Actual output:

```text
active: {'kind': 'allowed'}
silenced: {'kind': 'refused', 'gate': 'CHECK_ROLES', 'reason': None}
```

The regular manager passes. The temporary manager receives CHECK_ROLES because removing the silenced role leaves no matching role. The user identifier still exists; it is the role's participation in authorization that changes. A silenced role cannot satisfy AnyRole either.

The mode belongs to the role class, so it affects every user holding that class. Restricting one person instead calls for another rule, which the next section introduces.

There are four modes. ALIVE is the default for business roles. DEPRECATED still grants access, but requiring the role emits a warning so declarations can migrate. SILENCED excludes a user's role from matching. UNUSED rejects attempts to require the role with ValueError. Silencing affects a caller's available roles; UNUSED detects an invalid operation declaration.


<a id="conditions"></a>

## ABAC: conditions on the caller and on the input

### Add a condition to a particular role

A role groups users by authority, but it does not describe every difference between members of that group. Suppose the service belongs to the European division: a manager must also belong to the EU team.

A conditional grant expresses this: grant(ManagerRole, when=..., reason=...). grant associates a role with a further rule. when is a function taking the user and returning True or False; it is evaluated only after the role matches. reason declares the explanation returned if that condition refuses.

The teaching data encodes team membership in the user identifier. lambda user: user.user_id.startswith("eu-") creates a short function checking the identifier's prefix. A real application should base membership on trusted information. With no other restrictions in this example, only that condition distinguishes the two callers.

```python
from aoa.action_machine.intents.check_roles import check_roles, grant


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(grant(ManagerRole, when=lambda user: user.user_id.startswith("eu-"), reason="EU_TEAM_ONLY"))
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A condition applies to one role."""
    machine = ActionProductMachine(cache_coordinator=None)
    eu = Context(user=UserInfo(user_id="eu-m1", roles=(ManagerRole,)))
    us = Context(user=UserInfo(user_id="us-m1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(eu, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("EU manager:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(us, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("US manager:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/02_grant.py) · [Notebook](../../examples/step_03_authorization_and_roles/02_grant.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/02_grant.py
```

Actual output:

```text
EU manager: {'kind': 'allowed'}
US manager: {'kind': 'refused', 'gate': 'WHEN', 'reason': 'EU_TEAM_ONLY'}
```

eu-m1 has the required role and a true condition, so access is allowed. us-m1 has the role but a false condition. Its refusal therefore names WHEN rather than CHECK_ROLES, distinguishing a failed condition from a missing role.

EU_TEAM_ONLY comes directly from reason. An interface can use that application-defined value to select an explanation. A condition must declare a nonempty reason; omitting it is a declaration error.

when receives only UserInfo, not the operation parameters. It suits caller-specific restrictions, but cannot inspect a requested amount or determine ownership of the selected order. Those need the checks introduced next.

### Try another grant after a condition refuses

Refine the rule: managers need EU membership, but a global administrator may work regardless of team. Give the operation two ways to grant access: the conditional manager grant and a plain AdminRole requirement.

The administrator has user_id us-a1 and inherits ManagerRole. It therefore matches the first role but fails its condition. That false result must not end the search while another grant can still allow the caller.

A bare role class in @check_roles means a grant without a condition; AdminRole is equivalent to grant(AdminRole). Alternatives are evaluated in declaration order until one allows the call.

```python
from aoa.action_machine.intents.check_roles import check_roles, grant


class AdminRole(ManagerRole):
    """Include manager permissions with an additional grant."""

    name = "admin"
    description = "Global administrator"


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(grant(ManagerRole, when=lambda user: user.user_id.startswith("eu-"), reason="EU_TEAM_ONLY"), AdminRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A later grant may allow a caller."""
    machine = ActionProductMachine(cache_coordinator=None)
    manager = Context(user=UserInfo(user_id="us-m1", roles=(ManagerRole,)))
    admin = Context(user=UserInfo(user_id="us-a1", roles=(AdminRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(manager, CancelOrderAction, params)
    print("US manager:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(admin, CancelOrderAction, params)
    print("US admin:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/17_grant_fallback.py) · [Notebook](../../examples/step_03_authorization_and_roles/17_grant_fallback.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/17_grant_fallback.py
```

Actual output:

```text
US manager: {'kind': 'refused', 'gate': 'WHEN', 'reason': 'EU_TEAM_ONLY'}
US admin: {'kind': 'allowed'}
```

us-m1 fails the team condition and cannot match AdminRole, so it receives WHEN with the first grant's reason. us-a1 fails the same condition but matches the second requirement, which has no condition, and is allowed.

The demonstrated property is that a false condition rejects its own grant, not all remaining routes to permission. If no role matches, the answer is CHECK_ROLES. If roles match but all their conditions refuse, it is WHEN; with several such refusals, the first reason is retained. Declaration order can therefore affect the explanation of a final refusal.

### Restrict the call parameters for every role

The next restriction concerns the requested refund amount rather than team membership: at most 100 may be requested. It must apply whichever grant admitted the caller.

The guard argument of @check_roles declares this shared condition. Its function receives the user and operation parameters and runs after a grant succeeds. It asks whether the proposed call meets the common rule. guard_reason declares the refusal reason.

CancellationParams inherits order_id and adds the numeric amount field. lambda user, params: params.amount <= 100 compares that amount with the limit. user is unused in this rule but remains part of the required argument list. Both queries use the same caller and differ only in amount.

```python
class CancellationParams(OrderParams):
    """Add the requested cancellation amount."""

    amount: int = Field(description="Requested amount")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole, guard=lambda user, params: params.amount <= 100, guard_reason="AMOUNT_LIMIT")
class CancelOrderAction(BaseAction[CancellationParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A shared condition checks the call parameters."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(
        caller, CancelOrderAction, CancellationParams(order_id="ord-001", amount=50)
    )
    print("amount 50:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(
        caller, CancelOrderAction, CancellationParams(order_id="ord-001", amount=150)
    )
    print("amount 150:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/03_guard.py) · [Notebook](../../examples/step_03_authorization_and_roles/03_guard.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/03_guard.py
```

Actual output:

```text
amount 50: {'kind': 'allowed'}
amount 150: {'kind': 'refused', 'gate': 'GUARD', 'reason': 'AMOUNT_LIMIT'}
```

For 50 the comparison is true, so access is allowed. For 150 it is false, yielding GUARD and AMOUNT_LIMIT. The same role already passed in both calls.

Unlike a false when, a false guard ends access evaluation. Another grant cannot bypass the shared restriction. Even an administrator grant added to this operation would still face the same guard.

Both when and guard are synchronous functions and should return bool. An async function in either position is rejected with AccessConditionAsyncError. A rule requiring asynchronous storage access belongs in the object check introduced next.

The amount here is the requested refund parameter. The condition does not establish an order's stored price or replace validation of stored data. It demonstrates a condition over the caller and supplied parameters.


<a id="object"></a>

## Authorization and preconditions: where the line is

A condition can ask two different kinds of question, and it is worth keeping them apart:

- **Who may call.** `when=` sees the caller — identity and roles — and so does a `guard=` that reads `user`. This is authorization in the usual sense: the answer depends on the subject.
- **Whether this call is admissible at all.** The guard in [`03_guard.py`](../../examples/step_03_authorization_and_roles/03_guard.py) refuses any order whose identifier starts with `LOCKED-` and never looks at `user`: the same rule holds for every caller. A refund ceiling is the same kind of thing — a limit that applies to everyone alike, and a property of the call rather than a permission of the subject. The industry calls this a **precondition**: a domain rule or a policy constraint, not authorization.

AOA checks both in the same cascade, before the run, and answers both with the same three words — deliberately, so that a caller has one place to look and one answer to read. The cost is the confusion this section is about: "access" in AOA means *may this call proceed*, not only *may this subject do it*. So when you write a condition, decide which of the two you are writing and say it in the declared reason: a refused role and a refused amount are answers of different kinds, and whoever reads the refusal deserves to know which one they got.

---

## Per-object authorization: may this caller touch this order

### Allow an operation only on the caller’s own order

So far we have known the caller and the supplied parameters. But params.order_id does not establish that the caller owns the order: a manager can submit someone else's identifier. We must read ownership from application data.

A rule about the particular order is an object-level check. In AOA it is a separate method declared with @access_decide. Roles and shared conditions are evaluated first; this method then decides before the operation's business steps begin.

OWNERS stands in for a database. Its keys are order identifiers and its values are owner identifiers. ord-001 belongs to m-1; ord-002 belongs to m-2. The application supplies this mapping instead of accepting an ownership claim with the request.

The method also needs the caller's identity. It does not receive the whole Context automatically. @context_requires("user.user_id") declares the required field and causes the machine to pass a trailing ctx argument: a ContextView exposing the requested part of the context.

The check returns a decision object. Allowed() permits execution to continue. FORBIDDEN_OBJECT is a predefined Refused answer denying object access without an additional reason. Verdict is their common base type; the -> Verdict annotation describes the result type but does not create an answer.

The listing contains the complete operation and three calls by the same user. The access rule is separate from cancel_summary, whose job remains producing the allowed operation's result.

```python
from aoa.action_machine.context.context_view import ContextView


from aoa.action_machine.exceptions import AccessDenied


from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.intents.context_requires import context_requires


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


OWNERS = {"ord-001": "m-1", "ord-002": "m-2"}


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Allow cancellation of the caller's own order")
    @context_requires("user.user_id")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        ctx: ContextView,
    ) -> Verdict:
        """Decide access before cancelling the order."""
        if OWNERS.get(params.order_id) != ctx.get("user.user_id"):
            return FORBIDDEN_OBJECT
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A manager may cancel only their own order."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    result = await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    print("own order:", result.model_dump())
    for order_id in ("ord-002", "missing"):
        try:
            await machine.run(caller, CancelOrderAction(), OrderParams(order_id=order_id))
        except AccessDenied as exc:
            print(order_id + ":", exc.verdict.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/04_access_decide.py) · [Notebook](../../examples/step_03_authorization_and_roles/04_access_decide.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/04_access_decide.py
```

Actual output:

```text
own order: {'order_id': 'ord-001'}
ord-002: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': None}
missing: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': None}
```

For ord-001, ManagerRole matches. The check reads owner m-1 from OWNERS and caller m-1 from ctx. They are equal, so it returns Allowed(). The machine then calls the summary and returns the operation result.

For ord-002, the stored owner is m-2. The check returns FORBIDDEN_OBJECT; the machine stops and raises AccessDenied. The except block prints the decision carried in exc.verdict. The summary does not run for that order.

For missing, dict.get returns None, which also differs from m-1. The same refusal is deliberate: distinguishing “exists but belongs to someone else” from “does not exist” would reveal foreign order existence through the error channel.

The method's signature is fixed. params carries input; box provides tools associated with the call; connections maps connection names to supplied resources such as storage; ctx is present because the context requirement was declared. Unused box and connections parameters must still be present. There is no state argument because the business pipeline has not run.

async def permits the method to await storage reads. Arguments other than self and the return type are annotated because AOA validates that contract. Place @context_requires under @access_decide so the declaration sees the request for the trailing ctx parameter.

Replacing the dictionary with a database changes the read, not the rule: find the object, then compare its stored owner with the established caller. Do not cancel the order inside this method; preliminary access queries also invoke it.

### Return the reason an order cannot be cancelled

Ownership is not the only possible rule. Suppose the user is entitled to see the order, but it has already shipped and can no longer be cancelled. An interface benefits from distinguishing this situation from a general refusal.

The object check can return Refused("ORDER_ALREADY_SHIPPED"). The application chooses that reason string. Refused defaults to the ACCESS_DECIDE gate, so the gate need not be repeated. STATUS stores one order's state. This experiment isolates the shipped-order rule rather than repeating ownership checks.

```python
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


STATUS = {"ord-001": "shipped"}


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        if STATUS[params.order_id] == "shipped":
            return Refused("ORDER_ALREADY_SHIPPED")
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """An object refusal can explain a business rule."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print(answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/09_reasons.py) · [Notebook](../../examples/step_03_authorization_and_roles/09_reasons.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/09_reasons.py
```

Actual output:

```text
{'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'ORDER_ALREADY_SHIPPED'}
```

The check reads shipped and returns a refusal. Its dictionary identifies the negative outcome with kind='refused', the object-check stage with gate='ACCESS_DECIDE', and the business rule with reason='ORDER_ALREADY_SHIPPED'. Calling code can branch on these fields without parsing an exception message.

A refusal reason differs from a diagnostic failure message. Here the state was read successfully and supports a negative decision. If the read failed, claiming that the order shipped would be wrong; we will introduce a separate result for that situation.

Where ownership restricts visibility, establish the right to see the object before revealing its state. Foreign and missing orders should retain the shared refusal. Use a detailed reason only where that information may be disclosed.

### What happens when a check reads an undeclared field

The ownership check declared one context field and read it. Now test the boundary: the method still declares user.user_id but also tries to read request.client_ip, the client's address in request metadata.

ContextView does not expose a field merely because it exists in the full context. It limits the method to declared dependencies, making the data used by a decision visible from its declaration.

This deliberately incorrect method first prints the allowed field, then reads the undeclared one. When it cannot finish, the machine returns Undecided, meaning it could not determine access. Unlike Refused, this does not claim the caller violated an access rule.

```python
from aoa.action_machine.context.context_view import ContextView


from aoa.action_machine.intents.access_control import Allowed, Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.intents.context_requires import context_requires


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    @context_requires("user.user_id")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        ctx: ContextView,
    ) -> Verdict:
        """Decide access before cancelling the order."""
        print("declared user:", ctx.get("user.user_id"))
        ctx.get("request.client_ip")
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A check can read only declared context fields."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("answer:", answer.model_dump(mode="json"))
    print("server cause:", type(answer.cause).__name__)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/10_context_in_the_check.py) · [Notebook](../../examples/step_03_authorization_and_roles/10_context_in_the_check.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/10_context_in_the_check.py
```

Actual output:

```text
declared user: m-1
answer: {'kind': 'undecided', 'gate': 'ACCESS_DECIDE'}
server cause: ContextAccessError
```

The first print succeeds because user.user_id is declared. The second read raises ContextAccessError, so return Allowed() is never reached. The machine converts the failed check to Undecided at ACCESS_DECIDE.

The last line reads the original error type through answer.cause. That is server-side information, absent from the dictionary printed above it. Fix the method by declaring request.client_ip if the rule needs it, or by removing the read. Its signature offers no alternative argument exposing the full context.

The dependency also appears in the application graph, AOA's representation of declarations as nodes and relationships. The check has an AccessDecide node and its context requirement connects to RequiredContext, making the dependency inspectable without executing the method.


<a id="outcomes"></a>

## Two outcomes: a refusal is not a failure

### Receive a refusal from a query and from execution

check_access_decide asks for permission, while run attempts the operation. Calling code must know how the same refusal reaches it through these different entry points.

Use a fixed rule: all manager cancellations are temporarily paused. The guard always returns False and declares CANCELLATIONS_PAUSED. A constant condition makes the comparison independent of changing data.

The preliminary query returns refusal as an ordinary decision value. Execution cannot return a cancellation result because cancellation is prohibited, so it raises AccessDenied. That exception's verdict attribute carries the refusal. The example exercises both paths.

```python
from aoa.action_machine.exceptions import AccessDenied


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole, guard=lambda user, params: False, guard_reason="CANCELLATIONS_PAUSED")
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """Check and run carry the same refusal."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("check:", answer.model_dump(mode="json"))
    try:
        await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        print("run raises:", type(exc).__name__)
        print("run verdict:", exc.verdict.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/07_three_answers.py) · [Notebook](../../examples/step_03_authorization_and_roles/07_three_answers.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/07_three_answers.py
```

Actual output:

```text
check: {'kind': 'refused', 'gate': 'GUARD', 'reason': 'CANCELLATIONS_PAUSED'}
run raises: AccessDenied
run verdict: {'kind': 'refused', 'gate': 'GUARD', 'reason': 'CANCELLATIONS_PAUSED'}
```

The first line is the query's returned decision. run then raises AccessDenied, and the handler extracts exc.verdict. Both contain refused, GUARD, and CANCELLATIONS_PAUSED.

These are not separately implemented access policies. Both entry points use the same declarations and check order; they deliver a negative result differently. A query returns a value, while a stopped operation raises an exception. Application code must handle the appropriate form.

Two separate calls can only be expected to agree while their inputs and relevant data agree. This example uses a constant condition. An order can change after a preliminary answer, which is why execution checks again.

### Distinguish a refusal from an inability to check access

Suppose the order store is unavailable while a check is reading ownership. The check cannot establish who owns the order. Allowing access would be unsafe, but saying “this order is not yours” would also misstate the facts: ownership was never determined.

Undecided represents this third outcome. When a check raises an exception, the machine retains the original failure and produces that decision. Execution raises AccessUndecided rather than AccessDenied.

The example immediately raises RuntimeError("order store unavailable") from the object check to reproduce a storage failure. The caller has the correct role and no other conditions obscure the result.

```python
from aoa.action_machine.exceptions import AccessUndecided


from aoa.action_machine.intents.access_control import Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        raise RuntimeError("order store unavailable")

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A failed check is not a refusal."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("check:", answer.model_dump(mode="json"))
    try:
        await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessUndecided as exc:
        print("run raises:", type(exc).__name__)
        print("run verdict:", exc.verdict.model_dump(mode="json"))
        print("server cause:", type(exc.__cause__).__name__)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.py) · [Notebook](../../examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.py
```

Actual output:

```text
check: {'kind': 'undecided', 'gate': 'ACCESS_DECIDE'}
run raises: AccessUndecided
run verdict: {'kind': 'undecided', 'gate': 'ACCESS_DECIDE'}
server cause: RuntimeError
```

The query returns undecided at ACCESS_DECIDE. Execution raises AccessUndecided carrying the same serialized decision. The business method does not run: without permission the machine cannot proceed.

The answer does not include “order store unavailable.” That message is diagnostic material, not an explanation of a policy refusal. Server code can inspect answer.cause, or exc.__cause__ on execution. The example prints only RuntimeError, its type. Serializing the decision excludes the original failure and traceback, the chain of calls leading to it.

The distinction matters to clients: Refused can explain an unavailable action, while Undecided means checking failed and requires technical error handling. It does not establish that the user's rights were revoked.

A guard exception similarly yields Undecided at GUARD. A when exception yields CHECK_ROLES because its function runs inside role selection; WHEN names a conditional refusal, not a separate execution stage.

These decisions describe access. Call-configuration mistakes such as a missing required resource connection may still raise ordinary exceptions. check_access_decide does not convert every possible program error into a verdict.

We can now collect the outcomes in one table. An access decision is different from a business result: Allowed permits work to begin; OrderResult is produced after that work.

| What the access check established | Preliminary query | Execution attempt |
| --- | --- | --- |
| All rules permit the call | Returns Allowed | Runs the steps and returns the business result |
| A rule was evaluated and refused | Returns Refused | Raises AccessDenied carrying exc.verdict |
| A rule could not decide | Returns Undecided | Raises AccessUndecided carrying exc.verdict |

Refused has a gate and optional reason. Undecided publicly carries only kind and gate, with the original failure kept separately for server code. Calling code can therefore handle access through structured data rather than interpreting message text.

<a id="order"></a>

## The cascade: the order every check runs in

### Observe which checks actually ran

We have examined the rules separately. Now combine them to observe their order. The caller is established and holds the role. The role's condition is checked, then the shared call condition, then the order-specific rule. If a stage does not permit continuation, later stages are not reached. This ordered evaluation with stopping is called an authorization cascade.

TRACE is an ordinary list, not an AOA feature. Each function appends its name when actually called; the summary does the same. in_team returns True, but cancellations_open returns False. The object check could allow access, yet it should never be reached. The experiment isolates stopping the sequence.

```python
from aoa.action_machine.exceptions import AccessDenied


from aoa.action_machine.intents.access_control import Allowed, Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.intents.check_roles import check_roles, grant


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


TRACE = []


def in_team(user):
    """Record the role condition being evaluated."""
    TRACE.append("when")
    return True


def cancellations_open(user, params):
    """Record the shared condition refusing."""
    TRACE.append("guard")
    return False


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(
    grant(ManagerRole, when=in_team, reason="TEAM_REQUIRED"),
    guard=cancellations_open,
    guard_reason="CANCELLATIONS_PAUSED",
)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        TRACE.append("object")
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        TRACE.append("summary")
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A refusal stops the remaining checks."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    try:
        await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        print("refused at:", exc.verdict.gate.value)
    print("called:", TRACE)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/13_cascade.py) · [Notebook](../../examples/step_03_authorization_and_roles/13_cascade.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/13_cascade.py
```

Actual output:

```text
refused at: GUARD
called: ['when', 'guard']
```

TRACE contains only when and guard. The role condition ran and passed; the shared condition ran and refused; neither the object check nor the summary ran. GUARD identifies the same stopping point.

Changing cancellations_open to return True would reach the object check and summary, producing ['when', 'guard', 'object', 'summary']. Removing the caller's role instead would prevent even in_team from running, because a role must match before its condition is called.

With several grants, a false when still allows another grant to succeed. Role selection finishes that search before producing its result. Once a grant succeeds, the shared guard runs once for the whole call.

Access stops before business steps, so there are no completed steps to undo. @on_error, the business-error handler, is not a mechanism for reconsidering access. Compensations—actions undoing completed work—belong to failures within an operation and are covered in the next chapter.

Having seen ordered evaluation, we can connect it to the answer's gate field. A stage is a part of access evaluation; gate identifies it. AOA lists these names in Gate.

| Check | Data used | Negative-answer name |
| --- | --- | --- |
| Caller identity | Request and authentication coordinator | Current adapter rejects before the machine |
| A matching role | Context.user.roles and operation roles | CHECK_ROLES |
| The matching role's condition | when, receiving the user | WHEN |
| A shared restriction | guard, receiving user and input | GUARD |
| Access to the selected object | The declared @access_decide method | ACCESS_DECIDE |

Identity is checked at the request boundary. Gate also contains AUTH_COORDINATOR, but the current machine's corresponding stage performs no verification: the adapter already invoked the coordinator. An invalid token is therefore not returned by machine.run as Refused(AUTH_COORDINATOR); it stops the request earlier.

Optional undeclared restrictions are skipped: an operation may have no when, guard, or object method. @check_roles remains mandatory. Passing an early restriction only advances to the next; final permission requires passing every declared restriction.

<a id="observing"></a>

## Observability: what a plugin sees

### Observe a check starting and finishing

An application may need to measure a check or record its start and completion. Rather than adding monitoring to every rule, the machine can notify observers.

Such a notification is an event: it describes something that happened and carries related information. A plugin is an object connected to the machine that subscribes to selected events. The plugin below only prints a method name; it does not change access rules.

BeforeAccessDecideAspectEvent marks the declared object check starting; AfterAccessDecideAspectEvent marks completion without a failure cause. Despite Aspect in their names, these describe the access method, not business pipeline execution. @on(EventType) connects a plugin method to its event.

The complete example declares the operation, plugin, and plugins=[AccessPrinter()] configuration. It makes only a preliminary access query, isolating the check's events from operation execution.

```python
from aoa.action_machine.intents.access_control import Allowed, Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.intents.on import on


from aoa.action_machine.plugin.core.events import AfterAccessDecideAspectEvent, BeforeAccessDecideAspectEvent


from aoa.action_machine.plugin.core.plugin import Plugin


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


class AccessPrinter(Plugin):
    """Print the declared check's boundaries."""

    plugin_name = "access_printer"
    plugin_version = "1"

    async def get_initial_state(self):
        """Use no persistent plugin state."""
        return None

    @on(BeforeAccessDecideAspectEvent)
    async def on_before_check(self, state, event, log):
        """Report the check starting."""
        print("before:", event.aspect_name)

    @on(AfterAccessDecideAspectEvent)
    async def on_after_check(self, state, event, log):
        """Report the check finishing."""
        print("after:", event.aspect_name)


async def main() -> None:
    """A preliminary check publishes its own events."""
    machine = ActionProductMachine(cache_coordinator=None, plugins=[AccessPrinter()])
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("answer:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/11_events.py) · [Notebook](../../examples/step_03_authorization_and_roles/11_events.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/11_events.py
```

Actual output:

```text
before: cancel_access_decide
after: cancel_access_decide
answer: {'kind': 'allowed'}
```

The plugin first receives before, the check returns Allowed, and the plugin then receives after. The final line belongs to calling code that received the decision. The output separates observing execution from receiving its answer.

get_initial_state initializes plugin state for the call; this plugin needs none and returns None. Event handlers receive state, event, and log: plugin state, the notification object, and a logging tool. Here only event.aspect_name is used. Handler names start with on_ as required by @on.

A preliminary query starts no business operation, so it emits no GlobalStartEvent or GlobalFinishEvent, the operation's start and successful-finish notifications. It does run the object check and emits that check's events. Saying it emits no events at all would be incorrect.

The machine publishes no separate allowed/refused decision event. The caller receives the decision; these events describe the check's progress. An ordinary Refused is also a completed check and gets both boundary events. A failed method differs.

### Identify the stage where an access check failed

The preceding check completed normally. This one raises RuntimeError while an operation is being attempted. AccessGateFailedEvent notifies observers that an access stage could not complete.

Its gate identifies the stage; exception_type names the original exception class. A plugin can use those fields for failure counters or diagnostics, without receiving the exception message. The example subscribes only to that event, then prints the caller's decision. It uses run rather than a preliminary query, which matters to event publication.

```python
from aoa.action_machine.exceptions import AccessUndecided


from aoa.action_machine.intents.access_control import Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.intents.on import on


from aoa.action_machine.plugin.core.events import AccessGateFailedEvent


from aoa.action_machine.plugin.core.plugin import Plugin


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        raise RuntimeError("order store unavailable")

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


class FailurePrinter(Plugin):
    """Report which access step failed."""

    plugin_name = "failure_printer"
    plugin_version = "1"

    async def get_initial_state(self):
        """Use no persistent plugin state."""
        return None

    @on(AccessGateFailedEvent)
    async def on_failure(self, state, event, log):
        """Print the step and exception type."""
        print("failed gate:", event.gate)
        print("exception type:", event.exception_type)


async def main() -> None:
    """A plugin sees a failed access step."""
    machine = ActionProductMachine(cache_coordinator=None, plugins=[FailurePrinter()])
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    try:
        await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessUndecided as exc:
        print("caller:", exc.verdict.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/21_failure_event.py) · [Notebook](../../examples/step_03_authorization_and_roles/21_failure_event.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/21_failure_event.py
```

Actual output:

```text
failed gate: ACCESS_DECIDE
exception type: RuntimeError
caller: {'kind': 'undecided', 'gate': 'ACCESS_DECIDE'}
```

The plugin sees ACCESS_DECIDE and RuntimeError. Calling code catches AccessUndecided and prints the decision without diagnostic text. Both learn where the problem occurred without receiving “order store unavailable” in these records.

AccessGateFailedEvent is emitted on run. A preliminary query encountering the same failure returns Undecided without that event. The declared check's before event has already occurred, but its after event is absent when the decision carries a failure cause.

Roles and the shared guard run before GlobalStartEvent. The object check on run occurs after that event. An object refusal or failure can therefore leave a start without GlobalFinishEvent: the operation did not finish successfully. A failure handler should not invent a successful-finish event to fill that gap.

For reading an event log, the combinations matter. This table covers run boundaries and access events, not every event emitted by business steps.

| Object-check outcome | Preliminary query | run |
| --- | --- | --- |
| Allows | BeforeAccessDecideAspectEvent, then AfterAccessDecideAspectEvent | GlobalStartEvent, both check events, then GlobalFinishEvent after successful operation completion |
| Returns refusal | Both check events | GlobalStartEvent and both check events; no successful finish |
| Raises an exception | BeforeAccessDecideAspectEvent only | GlobalStartEvent, BeforeAccessDecideAspectEvent, AccessGateFailedEvent; no successful finish |

A method can itself return Undecided without an original failure cause. That method completed and gets AfterAccessDecideAspectEvent. An Undecided carrying a cause does not get After. Inability to decide and an exception from the method therefore do not always produce the same event sequence.

<a id="mistakes"></a>

## Invariants: how a wrong declaration is caught

The working examples established the rules. The remaining experiments examine authoring mistakes. An invalid declaration is not a refusal for a particular user; it means the rule cannot be assembled or executed correctly. Each experiment isolates one mistake and explains its detection and repair.

### Mistake: an operation declares two object checks

A faulty rule and a faulty declaration are detected at different times. When a machine is constructed, it collects operation declarations and validates that they can be invoked unambiguously. This assembly happens before serving requests.

The operation below has two methods marked @access_decide. Each method is individually valid, but their relationship is unspecified. AOA requires one declared object check per operation rather than guessing how to combine them. We only construct the machine; no caller or order is needed to expose the declaration error.

```python
from aoa.action_machine.exceptions import DuplicateAccessDecideError


from aoa.action_machine.intents.access_control import Allowed, Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        return Allowed()

    @access_decide("Check whether the order can be cancelled")
    async def second_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """An action declares at most one object check."""
    try:
        ActionProductMachine(cache_coordinator=None)
    except DuplicateAccessDecideError as exc:
        print(type(exc).__name__)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/06_the_declaration.py) · [Notebook](../../examples/step_03_authorization_and_roles/06_the_declaration.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/06_the_declaration.py
```

Actual output:

```text
DuplicateAccessDecideError
```

Assembly raises DuplicateAccessDecideError. Keep one method and explicitly combine the necessary rules inside it, for example ownership first and then the visible order's state. Their order and return conditions remain visible together.

An object check belongs to the operation whose own class body declares it; it is not inherited as an access rule from a parent. An operation with no object check adds no object-level restriction after its other rules. This differs from @check_roles, which is mandatory.

### Mistake: the check has no description

The text passed to @access_decide describes the rule. AOA includes it in its representation of the operation, so an empty string is not a valid declaration.

Simply creating the decorator with empty text exposes the error. This and the next two short listings are standalone files and need no shared definitions.

```python
from __future__ import annotations


import asyncio


from aoa.action_machine.intents.access_decide import access_decide


async def main() -> None:
    """An object check requires a description."""
    try:
        access_decide("")
    except ValueError as exc:
        print(type(exc).__name__ + ":", exc)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/18_empty_description.py) · [Notebook](../../examples/step_03_authorization_and_roles/18_empty_description.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/18_empty_description.py
```

Actual output:

```text
ValueError: @access_decide: description cannot be empty or whitespace. Say what the check decides.
```

ValueError occurs before a method or machine is constructed. Supply a nonempty description such as "Allow cancellation of the caller's own order". This describes the method's purpose; it is not the refusal reason and does not replace a returned verdict. Method description, decision, and refusal explanation are separate concepts.

### Mistake: copying a state argument into the check

Business methods receive intermediate state, but an object check runs before business steps and has a different parameter list. Copying state into that signature must not silently shift the arguments the machine passes.

This method is asynchronous and annotated, but includes one extra argument. That isolates the declaration mistake.

```python
from __future__ import annotations


import asyncio


from aoa.action_machine.intents.access_control import Allowed, Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.model import BaseParams


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


async def main() -> None:
    """An object check does not receive pipeline state."""
    try:

        @access_decide("Check the order")
        async def order_access_decide(
            self, params: BaseParams, state: object, box: ToolsBox, connections: dict[str, BaseResource]
        ) -> Verdict:
            """Demonstrate the extra state argument."""
            return Allowed()
    except TypeError as exc:
        print(type(exc).__name__ + ":", exc)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/19_wrong_signature.py) · [Notebook](../../examples/step_03_authorization_and_roles/19_wrong_signature.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/19_wrong_signature.py
```

Actual output:

```text
TypeError: @access_decide: method 'order_access_decide' must declare its parameters as (self, params, box, connections), got (self, params, state, box, connections). The object step hands over (self, params, box, connections) in that order, and Python binds by position, so a renamed or reordered parameter would receive something other than it says.
```

TypeError states the expected order self, params, box, connections and shows the actual order containing state. It is raised when the decorator is applied. Remove state; read the required order data from storage using params rather than expecting state from steps that have not run.

Context follows the previously introduced rule: @context_requires below the check declaration adds a trailing ctx: ContextView. Arbitrarily renaming or adding parameters is not supported; names and order are checked along with the count.

### Mistake: omitting the decision return annotation

A correct parameter list is not sufficient. The declared object check also needs a return annotation so its contract can be validated. This method returns Allowed(), but its header does not state a result type.

The example demonstrates an authoring error before any access request, not a refusal for a user.

```python
from __future__ import annotations


import asyncio


from aoa.action_machine.intents.access_control import Allowed


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.model import BaseParams


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


async def main() -> None:
    """An object check must annotate its answer."""
    try:

        @access_decide("Check the order")
        async def order_access_decide(self, params: BaseParams, box: ToolsBox, connections: dict[str, BaseResource]):
            """Demonstrate the missing return annotation."""
            return Allowed()
    except TypeError as exc:
        print(type(exc).__name__ + ":", exc)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/20_missing_return_type.py) · [Notebook](../../examples/step_03_authorization_and_roles/20_missing_return_type.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/20_missing_return_type.py
```

Actual output:

```text
TypeError: @access_decide: method 'order_access_decide' must annotate what it returns (-> Verdict, or one of Allowed / Refused / Undecided).
```

The decorator raises TypeError asking for a result annotation. Use -> Verdict for a method that may return different decisions, or a specific decision type where appropriate.

Missing annotations differ from annotations naming the wrong types. Presence and parameter shape can be checked at decoration. Resolving and validating named types may require the completed class, so that happens at machine assembly. The actual returned value is checked during invocation, as shown below.

### Mistake: a condition has no refusal reason

A when condition computes only True or False. False alone does not explain whether the caller belongs to the wrong team, is suspended, or violates another rule. The condition's author knows that meaning.

A when therefore requires reason. This standalone file declares the role and condition but deliberately omits the explanation.

```python
from __future__ import annotations


import asyncio


from aoa.action_machine.auth import ApplicationRole


from aoa.action_machine.intents.check_roles import grant


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


async def main() -> None:
    """A role condition must declare its refusal reason."""
    try:
        grant(ManagerRole, when=lambda user: False)
    except ValueError as exc:
        print(type(exc).__name__ + ":", exc)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/22_reason_required.py) · [Notebook](../../examples/step_03_authorization_and_roles/22_reason_required.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/22_reason_required.py
```

Actual output:

```text
ValueError: when= must say why it refuses: declare reason= beside it, because a caller must not have to guess.
```

Grant construction raises ValueError. Adding reason="EU_TEAM_ONLY" fixes the declaration shape, provided the reason actually describes the rule. The corresponding argument for guard is guard_reason.

This does not require every refusal in the system to carry a reason. CHECK_ROLES identifies an unmet role requirement, and FORBIDDEN_OBJECT intentionally omits additional detail. The requirement applies to conditions explicitly introduced through when and guard.

### Mistake: returning True after promising a verdict

A type annotation states a contract, but ordinary Python does not force the function body to obey it. A method annotated -> Verdict can still return True. The machine must therefore validate the actual returned value as well as the declaration.

The method below has a valid declaration. Its only deliberate mistake is return True instead of return Allowed(). The query shows whether that is treated as permission.

```python
from aoa.action_machine.intents.access_control import Verdict


from aoa.action_machine.intents.access_decide import access_decide


from aoa.action_machine.resources import BaseResource


from aoa.action_machine.runtime.tools_box import ToolsBox


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        return True  # Deliberately wrong: the example demonstrates runtime validation.

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


async def main() -> None:
    """A boolean is not an object-access verdict."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("answer:", answer.model_dump(mode="json"))
    print("server cause:", type(answer.cause).__name__)


if __name__ == "__main__":
    asyncio.run(main())
```

[Complete script](../../examples/step_03_authorization_and_roles/23_invalid_answer.py) · [Notebook](../../examples/step_03_authorization_and_roles/23_invalid_answer.ipynb)

Run the complete file from the repository root:

```bash
uv run python examples/step_03_authorization_and_roles/23_invalid_answer.py
```

Actual output:

```text
answer: {'kind': 'undecided', 'gate': 'ACCESS_DECIDE'}
server cause: TypeError
```

There is no permission: the answer is Undecided with a private TypeError cause. The machine detects a value outside the decision contract rather than guessing its meaning. Return Allowed() to permit, Refused(...) to deny, or Undecided(...) when the method itself reports inability to decide.

False, strings, and None are invalid substitutes too. Keep the contracts distinct: synchronous when and guard predicates return bool; the asynchronous object check returns a decision, which can carry a refusal reason or report inability to complete.


## Migration: if you used the previous API

The previous object rule overrode a plain access_decide method returning bool. The current API uses @access_decide on a separate method whose name ends in _access_decide. It requires argument and return annotations and a returned Allowed, Refused, or Undecided. Leaving the old method in place is insufficient because the machine resolves the declaration.

machine.check_access_decide now examines one operation and one input at a time. The batch form and max_check_access_decide_batch_size setting are removed. Handle execution refusals through AccessDenied and inability to decide through AccessUndecided; the stage is in exc.verdict.gate rather than the former numeric level.

## Check your understanding

1. Why is a client-supplied administrator name insufficient for authentication? Where does the JWT example establish trust in the identifier?
2. How does caller information in Context differ from the order identifier in OrderParams? Why are they separate arguments?
3. Why does AdminRole(ManagerRole) satisfy a manager requirement but not the reverse? When is a role list more appropriate than inheritance?
4. Does a user with a user_id but no roles satisfy AnyRole?
5. What information can when, guard, and an object check use? Where should ownership be checked?
6. Why can a false when still lead to permission while a false guard stops access?
7. Why do foreign and missing orders share an answer? What would distinguishing them disclose?
8. What reaches the client after a policy refusal versus a storage failure? Where does the original error remain?
9. Why does a preliminary Allowed not guarantee execution a minute later? Which work does the preliminary query still perform?
10. Why can a plugin see an operation start without a successful-finish event?

> **Change one rule.** Predict the answer for amount 150 with a limit of 200 in 03_guard.py. Change only the limit and run it. Restore 100, then change only the caller's roles to an empty tuple. Explain why the refusal now names CHECK_ROLES rather than GUARD.
>
> **Change object-related data.** In 04_access_decide.py change the caller from m-1 to m-2 while preserving the role. Predict all three answers before running. Explain why the first two change while missing does not.
>
> **Follow the order.** In 13_cascade.py make cancellations_open return True. Write the expected TRACE before running, then name the rule that permitted each newly reached function.

Access in this chapter is decided before business steps. [Saga and compensations](step-04-saga-and-compensations.md) addresses the next situation: some work completed before a later step failed, so completed effects must be undone. That explains why an access refusal and a failure within an operation use different recovery mechanisms.

<table width="100%"><tr>
  <td align="left"><a href="step-02-state-as-x-ray.md">← Step 02 — State</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-04-saga-and-compensations.md">Step 04 — Saga and compensations →</a></td>
</tr></table>
