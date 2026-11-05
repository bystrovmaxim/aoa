# Contract: `@entity` and the messages of this change

```python
def entity(description: str, *, resource: type[BaseResource]) -> Callable[[type], type]: ...
```

| Case | Declaration | Answer |
|---|---|---|
| 2.6 | `@entity(description="Customer order", resource=StorefrontDatabase)` | accepted; domain `StoreDomain` (from `StorefrontDatabase`'s `@meta`) |
| 2.1 | `@entity(description="Customer order")` | `EntityDecoratorError: SalesOrderCoreEntity — @entity needs resource=: an entity is stored by a resource.` |
| 2.2 | `@entity(description=..., domain=StoreDomain, resource=StorefrontDatabase)` | `TypeError: entity() got an unexpected keyword argument 'domain'` |
| 2.3 | `resource=StoreDomain` | `EntityDecoratorError: SalesOrderCoreEntity — @entity resource= must be a BaseResource subclass, got StoreDomain.` |
| 2.3 | `resource=BaseStorage` | `EntityDecoratorError: SalesOrderCoreEntity — @entity resource= must be a concrete resource, got BaseStorage, which is excluded from the graph model.` |
| 2.3 | resource without `@meta` | `EntityDecoratorError: SalesOrderCoreEntity — @entity resource= StorefrontDatabase declares no domain: decorate it with @meta(domain=...).` |
| 2.5 | `resource=(StorefrontDatabase, StorefrontSessionCache)` | `EntityDecoratorError: SalesOrderCoreEntity — @entity takes one resource, got 2: StorefrontDatabase, StorefrontSessionCache.` |
| 2.4 | association across resources | `EntityResourceError: SupportTicketCoreEntity.order relates SupportTicketCoreEntity (SupportDatabase) to SalesOrderCoreEntity (StorefrontDatabase): a relation stays inside one resource.` |
| 2.4 | state type across resources | `EntityResourceError: OrderStateEntity is the state type of OrderCoreEntity.lifecycle (StorefrontDatabase) and ReturnCoreEntity.lifecycle (SupportDatabase): a lifecycle stays inside one resource.` |
| 2.5 | graph: entity without the edge | `InvalidGraphError: Entity <id> has 0 entity_resource edges; an entity has exactly one.` |
| 2.5 | graph: relation edge across resources | `InvalidGraphError: Edge <edge id> joins <source> (<ResourceA>) and <target> (<ResourceB>): a relation stays inside one resource.` |

The texts are the target; the tests pin them word for word once written.
