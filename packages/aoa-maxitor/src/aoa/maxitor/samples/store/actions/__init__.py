# packages/aoa-maxitor/src/aoa/maxitor/samples/store/actions/__init__.py
from aoa.maxitor.samples.store.actions.cart_abandon_stub import CartAbandonStubAction
from aoa.maxitor.samples.store.actions.checkout_submit import CheckoutSubmitAction
from aoa.maxitor.samples.store.actions.inventory_hold_stub import InventoryHoldStubAction
from aoa.maxitor.samples.store.actions.loyalty_points_stub import LoyaltyPointsStubAction
from aoa.maxitor.samples.store.actions.order_lookup import OrderLookupAction
from aoa.maxitor.samples.store.actions.ping import OpsPingAction
from aoa.maxitor.samples.store.actions.role_migration import RoleMigrationAction

CartAbandonStubParams = CartAbandonStubAction.Params
CartAbandonStubResult = CartAbandonStubAction.Result
CheckoutSubmitParams = CheckoutSubmitAction.Params
CheckoutSubmitResult = CheckoutSubmitAction.Result
InventoryHoldStubParams = InventoryHoldStubAction.Params
InventoryHoldStubResult = InventoryHoldStubAction.Result
LoyaltyPointsStubParams = LoyaltyPointsStubAction.Params
LoyaltyPointsStubResult = LoyaltyPointsStubAction.Result
OpsPingParams = OpsPingAction.Params
OpsPingResult = OpsPingAction.Result
OrderLookupParams = OrderLookupAction.Params
OrderLookupResult = OrderLookupAction.Result
RoleMigrationParams = RoleMigrationAction.Params
RoleMigrationResult = RoleMigrationAction.Result

__all__ = [
    "CartAbandonStubAction",
    "CartAbandonStubParams",
    "CartAbandonStubResult",
    "CheckoutSubmitAction",
    "CheckoutSubmitParams",
    "CheckoutSubmitResult",
    "InventoryHoldStubAction",
    "InventoryHoldStubParams",
    "InventoryHoldStubResult",
    "LoyaltyPointsStubAction",
    "LoyaltyPointsStubParams",
    "LoyaltyPointsStubResult",
    "OpsPingAction",
    "OpsPingParams",
    "OpsPingResult",
    "OrderLookupAction",
    "OrderLookupParams",
    "OrderLookupResult",
    "RoleMigrationAction",
    "RoleMigrationParams",
    "RoleMigrationResult",
]
