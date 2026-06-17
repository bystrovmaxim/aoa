<!-- translated-from: migrating-legacy_draft.md @ 2026-06-16T13:55:20Z · sha256:e3217e4b7a23 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Migrating legacy to AOA

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

AOA does not require rewriting the system from scratch. Legacy is moved gradually, with the **strangler** pattern: the monster is isolated behind an interface, wrapped in a thin operation, and then its logic is pulled out one step at a time into aspects — until the old code is left with nothing to do and is deleted. The key property of the path is that **after each step the system stays working and testable**; no revolutions and no "rewrite everything in one sprint" are needed.

Let's work through this on an end-to-end example — a typical payments "god class".

```python
class PaymentManager:               # singleton, state, transport, and logic all mixed
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.db = connect_db()
        self.http = create_http_client()
        self.stats = {}

    def process(self, user_id, card_token, amount):
        user = self.db.fetch("SELECT * FROM users WHERE id=%s", (user_id,))
        if not user:
            raise ValueError("User not found")
        if not self._validate_card(card_token, amount):
            raise ValueError("Invalid card")
        txn = self._charge(card_token, amount)
        self.db.execute("INSERT INTO payments ...")
        self.stats["total"] = self.stats.get("total", 0) + amount
        return {"success": True, "txn": txn}
```

The problems are obvious: a singleton, it holds state, it mixes transport with business rules, it is not isolated, it is not testable. We will remove them one by one.

---

## Step 1. The port

We describe **only what the domain actually needs**, not copy the whole class.

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):
    @abstractmethod
    async def validate_card(self, token: str, amount: float) -> bool: ...
    @abstractmethod
    async def charge(self, token: str, amount: float) -> str: ...
```

## Step 2. The adapter

We hide the monster behind the port. This is an **anti-corruption layer**: the new code no longer depends on the legacy directly.

```python
class LegacyPaymentGateway(BaseResource, PaymentGateway):
    def __init__(self) -> None:
        self._legacy = PaymentManager()

    async def validate_card(self, token: str, amount: float) -> bool:
        return self._legacy._validate_card(token, amount)

    async def charge(self, token: str, amount: float) -> str:
        return self._legacy._charge(token, amount)
```

## Step 3. The first wrapper operation

A single entry point, DI, and the ability to write tests appear. We do not touch the monster's logic yet — we move it "as is".

```python
class ProcessPaymentParams(BaseParams):
    user_id: int = Field(description="User identifier")
    card_token: str = Field(description="Card token")
    amount: float = Field(description="Charge amount")


class ProcessPaymentResult(BaseResult):
    success: bool = Field(description="The payment went through")
    txn: str = Field(description="Transaction identifier")


@meta(description="Process a payment", domain=BillingDomain)
@check_roles(AnyRole)
@depends(PaymentGateway)
class ProcessPaymentAction(BaseAction[ProcessPaymentParams, ProcessPaymentResult]):

    @summary_aspect("A temporary wrapper over the legacy")
    async def charge_summary(self, params, state, box, connections):
        gateway = await box.resolve(PaymentGateway)
        if not await gateway.validate_card(params.card_token, params.amount):
            return ProcessPaymentResult(success=False, txn="")
        txn = await gateway.charge(params.card_token, params.amount)
        return ProcessPaymentResult(success=True, txn=txn)
```

## Step 4. Pull the steps out into aspects

One step per iteration. Each move makes the pipeline a little more detailed, and the monster a little thinner.

```python
@meta(description="Process a payment", domain=BillingDomain)
@check_roles(AnyRole)
@depends(PaymentGateway)
@depends(UserRepository)
class ProcessPaymentAction(BaseAction[ProcessPaymentParams, ProcessPaymentResult]):

    @regular_aspect("Check the user")
    @result_instance("user", UserEntity, required=True, no_none=True)
    async def check_user_aspect(self, params, state, box, connections):
        users = await box.resolve(UserRepository)
        user = await users.get(params.user_id)
        if user is None:
            raise ValueError("User not found")
        return {"user": user}

    @summary_aspect("Charge")
    async def charge_summary(self, params, state, box, connections):
        gateway = await box.resolve(PaymentGateway)
        if not await gateway.validate_card(params.card_token, params.amount):
            return ProcessPaymentResult(success=False, txn="")
        txn = await gateway.charge(params.card_token, params.amount)
        return ProcessPaymentResult(success=True, txn=txn)
```

## Step 5. A repeating step — into a separate operation

Card validation is needed in other scenarios too — that is a signal to extract (see [Action, aspect, or resource](choosing-action-aspect-resource.md)).

```python
class ValidateCardParams(BaseParams):
    card_token: str = Field(description="Card token")
    amount: float = Field(description="Amount")


class ValidateCardResult(BaseResult):
    valid: bool = Field(description="The card is valid")


@meta(description="Validate a card", domain=BillingDomain)
@check_roles(AnyRole)
@depends(PaymentGateway)
class ValidateCardAction(BaseAction[ValidateCardParams, ValidateCardResult]):

    @summary_aspect("Card validation")
    async def validate_summary(self, params, state, box, connections):
        gateway = await box.resolve(PaymentGateway)
        valid = await gateway.validate_card(params.card_token, params.amount)
        return ValidateCardResult(valid=valid)
```

In the main operation the step becomes a call:

```python
@regular_aspect("Card validation")
@result_bool("card_valid", required=True)
async def validate_card_aspect(self, params, state, box, connections):
    result = await box.run(
        ValidateCardAction,
        ValidateCardParams(card_token=params.card_token, amount=params.amount),
    )
    if not result.valid:
        raise ValueError("The card is invalid")
    return {"card_valid": True}
```

## Step 6. Long-lived state — into a resource

The monster accumulated statistics — that state cannot be lost. We isolate it as a resource.

```python
class PaymentStats(BaseResource, ABC):
    @abstractmethod
    async def record(self, amount: float) -> None: ...


@regular_aspect("Record statistics")
@result_bool("recorded", required=True)
async def record_stats_aspect(self, params, state, box, connections):
    await (await box.resolve(PaymentStats)).record(params.amount)
    return {"recorded": True}
```

## Result

The monster has fallen apart. What remains is a transparent operation whose steps are visible from the class, plus resources holding only state:

```python
@meta(description="Process a payment", domain=BillingDomain)
@check_roles(AnyRole)
@depends(PaymentGateway)
@depends(UserRepository)
@depends(PaymentStats)
class ProcessPaymentAction(BaseAction[ProcessPaymentParams, ProcessPaymentResult]):

    @regular_aspect("Check the user") ...
    @regular_aspect("Card validation") ...
    @regular_aspect("Record statistics") ...
    @summary_aspect("Charge") ...
```

The whole path: **monster → port → adapter → first wrapper operation → aspects → reusable operations → resources for state → clean architecture.** Step by step, with tests, without rewriting everything at once.

---

## Not every monster migrates the same way

The end-to-end example above is the hardest case. More often the target form can be recognized at once:

- **Temporary state, pure rules** (a calculator object recreated on every call) → straight to one **operation** with a summary aspect; no port or adapter needed.
- **Several public methods, several responsibilities** (a report generator: `load`, `process`, `aggregate`, `export`) → each scenario is a **separate operation**, and a composite scenario assembles them through `box.run`.
- **Long-lived state, connections, caches, a singleton** → a **resource** behind a port; the business rules, if there were any, move into operations.

The signal "time to extract an operation" is the same at any stage: **the logic was needed in a second place.**

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
