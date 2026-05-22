# AOA

**AOA** — Python-фреймворк, в котором намерения становятся кодом, а код — исполняемой спецификацией.

---

```python
# Контракт: что принимает операция и что возвращает
class CreateOrderParams(BaseParams):
    order_id: str = Field(description="ID заказа")

class CreateOrderResult(BaseResult):
    order_id: str = Field(description="ID созданного заказа")

# Намерения: домен, роли, ресурсы, зависимости от других операций
@meta(description="Создать заказ", domain=StoreDomain)
@check_roles(AdminRole)
@connection(DatabaseResource, key="db")
@depends(PaymentAction, mode=UseCase.include)
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

    # Именованные шаги — каждый с явным контрактом результата
    @regular_aspect("Валидация")
    @result_string("validated_id", required=True)
    async def validate_aspect(self, params, state, box, connections):
        return {"validated_id": params.order_id}

    @regular_aspect("Списание средств")
    async def charge_aspect(self, params, state, box, connections):
        ...

    # Сага: если что-то пошло не так после этого шага — откат
    @compensate("charge_aspect", "Возврат средств")
    async def charge_compensate(self, params, state, connections, error):
        ...

    @summary_aspect("Создание")
    async def create_summary(self, params, state, box, connections):
        return CreateOrderResult(order_id=state.validated_id)
```

Вы описываете операцию один раз. В шапке сразу видно всё: что принимает, что возвращает, кто может вызвать, какие ресурсы использует, от каких других операций зависит.

---

**Intent-Oriented Programming (IOP)** — так называется этот подход. AOA — его референсная реализация на Python. Три принципа:

**Intent is code** — намерение объявляется прямо в коде, а не в Wiki. `@meta`, `@check_roles`, `@depends` — не комментарии, а часть исполняемой спецификации, которую система читает вместе с логикой операции.

**Intent is persistent** — объявленное намерение не теряется после написания. `@check_roles` проверяется при каждом вызове. `@depends(..., UseCase.include)` гарантирует, что зависимость реально выполнится в этой сессии; Структурные инварианты (циклы, отсутствующие декларации) проверяются на старте. [Полный список намерений и инвариантов →](docs/intents-and-invariants.md)

**Intent is observable** — из того же кода система строит полный граф: как связаны домены, операции, сущности и зависимости. Maxitor визуализирует карту доменов, ERD, use-case-диаграмму и конечный автомат. Плагины записывают каждый запуск операции — телеметрию и логи — в формате [OCEL 2.0](https://ocel-standard.org/): какие действия выполнялись, с какими объектами и в каком контексте.

---

## Установка

Выберите минимально нужный пакет:

```bash
pip install aoa-action-machine     # core: операции, аспекты, роли, сущности, graph
pip install aoa-ocel               # OCEL 2.0 export
pip install aoa-maxitor            # визуализатор: карта доменов, ERD, lifecycle
pip install aoa-examples           # примеры доменов и FastAPI/MCP-адаптеры
```

Extras:

```bash
pip install aoa-action-machine[fastapi,mcp,postgres]
pip install aoa-ocel[pm4py]
pip install aoa-examples[fastapi,mcp]
```

Из git:

```bash
uv sync --extra dev --group dev
uv run task check
```

---

## Пакеты

Монорепо из четырёх wheels с общим namespace `aoa.*`:

| Пакет | Namespace | Назначение |
|-------|-----------|------------|
| `aoa-action-machine` | `aoa.action_machine` | Core: операции, аспекты, сага, роли, сущности, interchange graph, плагины, адаптеры |
| `aoa-ocel` | `aoa.ocel` | OCEL 2.0: `OcelFrame`, `OcelPlugin`, store resources |
| `aoa-maxitor` | `aoa.maxitor` | Визуализатор: FastAPI + React SPA |
| `aoa-examples` | `aoa.examples` | Примеры доменов, FastAPI/MCP, Store OCEL batch export |

Зависимости строго однонаправленные:

```
aoa-action-machine
aoa-ocel            →  aoa-action-machine
aoa-maxitor         →  aoa-action-machine
aoa-examples        →  aoa-action-machine, aoa-ocel
```

---

## Первый запуск

**OCEL export — Store domain:**

```bash
uv run pytest packages/aoa-examples/aoa_examples_tests/test_store_ocel_integration_log.py -q
# → archive/logs/ocel.json
```

**Визуализатор:**

```bash
uv run task maxitor-api                                        # backend :8000
cd packages/aoa-maxitor/client && npm install && npm run dev  # frontend :5173
```

---

## Документация

| | |
|---|---|
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Release notes |
| [docs/intents-and-invariants.md](docs/intents-and-invariants.md) | Все намерения и инварианты |
| [packages/aoa-action-machine/README.md](packages/aoa-action-machine/README.md) | `@depends`, include contract |
| [packages/aoa-ocel/README.md](packages/aoa-ocel/README.md) | OCEL export policy |
| [packages/aoa-maxitor/README.md](packages/aoa-maxitor/README.md) | Maxitor API + React SPA |
| [packages/aoa-examples/README.md](packages/aoa-examples/README.md) | Примеры |

---

MIT
