13_errors_in_resources.md

# Обработка ошибок в ресурсных менеджерах

В AOA ответственность за ошибки внешнего мира целиком лежит на ресурсных менеджерах. Actions должны оставаться чистыми и свободными от инфраструктурных деталей — включая формат, типы и характер ошибок. Этот документ объясняет как правильно обрабатывать ошибки в ресурсах, когда их поднимать, когда оборачивать и как Actions должны с ними работать [1].

---

## Основной принцип

Ресурсный менеджер — единственный кто видит сеть, файлы, API, базы данных, дескрипторы и сокеты. Именно он обязан поймать инфраструктурное исключение и привести его к виду понятному домену.

Actions не должны знать про ConnectionError, TimeoutError, HTTPError, OperationalError и другие инфраструктурные исключения. Эти детали — ответственность ресурса.

Это разделение обеспечивает чистоту доменного кода и позволяет заменять адаптеры без изменения бизнес-логики.

---

## Три вида ошибок в ресурсах

Первый вид — инфраструктурные ошибки. Это ошибки транспорта и внешних систем: сеть недоступна, БД упала, таймаут, файл исчез, внешний API вернул 500. Такие ошибки оборачиваются в HandleException и поднимаются наверх. Action пропускает их — пусть транспортный слой решает что вернуть клиенту.

Второй вид — доменные ошибки. Это ошибки которые влияют на бизнес-решение: товар не найден, платёж уже обработан, пользователь заблокирован. Их нужно преобразовывать в доменные исключения понятные Action.

Третий вид — ошибки жизненного цикла соединения. Это попытки использовать ресурс неправильно: вызов execute до open, двойной commit, rollback без открытого соединения. Для них в ActionEngine определены специальные исключения.

---

## HandleException — стандартное инфраструктурное исключение

HandleException — это единообразное исключение ActionEngine для всех инфраструктурных ошибок [1]. Ресурсный менеджер должен оборачивать все внешние исключения в HandleException прежде чем они покинут адаптер.

```python
from ActionMachine.Core.Exceptions import HandleException

class PostgresOrderRepository(IOrderRepository):

    async def create(self, user_id: int, total: float) -> int:
        try:
            result = await self._pool.fetchval(
                "INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",
                user_id, total
            )
            return result
        except asyncpg.PostgresConnectionError as e:
            raise HandleException(f"Нет соединения с БД: {e}") from e
        except asyncpg.PostgresError as e:
            raise HandleException(f"Ошибка PostgreSQL: {e}") from e
        except Exception as e:
            raise HandleException(f"Неожиданная ошибка при создании заказа: {e}") from e
```

Action видит только HandleException и не знает какая именно БД использовалась и какое конкретное исключение произошло внутри.

---

## Доменные ошибки — преобразование в понятный вид

Если ошибка имеет смысл для бизнес-логики — ресурс должен преобразовать её в доменное исключение прежде чем поднять наверх.

```python
from ActionMachine.Core.Exceptions import HandleException

class StripePaymentGateway(IPaymentGateway):

    async def charge(self, token: str, amount: float) -> str:
        try:
            response = await self._client.post("/charge", json={
                "token": token,
                "amount": amount
            })
            response.raise_for_status()
            return response.json()["transaction_id"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise ValueError("Платёж уже был обработан ранее") from e
            if e.response.status_code == 422:
                raise ValueError("Недостаточно средств на карте") from e
            raise HandleException(f"Ошибка платёжного шлюза: {e}") from e
        except httpx.ConnectError as e:
            raise HandleException(f"Платёжный шлюз недоступен: {e}") from e
        except Exception as e:
            raise HandleException(f"Неожиданная ошибка платежа: {e}") from e
```

Теперь Action получает либо HandleException — и пропускает его наверх, либо ValueError с понятным доменным сообщением — и может принять бизнес-решение.

---

## Ошибки жизненного цикла соединения

ActionEngine определяет специальные исключения для ошибок использования ресурса [1]:

ConnectionNotOpenError — попытка выполнить запрос до открытия соединения.

ConnectionAlreadyOpenError — попытка открыть уже открытое соединение.

TransactionException — общая ошибка управления транзакцией.

TransactionProhibitedError — попытка дочернего действия вызвать open, commit или rollback на прокси-обёртке.

```python
from ActionMachine.Core.Exceptions import (
    ConnectionNotOpenError,
    HandleException
)

class CsvConnectionManager(IConnectionManager):

    async def execute(self, query: str, params=None):
        if self._file is None:
            raise ConnectionNotOpenError(
                "Попытка записи до открытия файла. Вызовите open() сначала."
            )
        try:
            self._writer.writerow(params)
        except Exception as e:
            raise HandleException(f"Ошибка записи в CSV: {e}") from e
```

---

## Когда Action обрабатывает ошибки ресурса

Большинство инфраструктурных ошибок Action должен пропускать наверх не перехватывая. Но есть случаи когда обработка ошибки — это часть бизнес-логики.

Правильно — пропустить инфраструктурную ошибку:

```python
@aspect("Загрузка продукта")
async def load_product(self, params, state, deps):
    repo = deps.get(IProductRepository)
    product = await repo.get(params.product_id)
    state["product"] = product
    return state
```

Если repo.get поднимет HandleException — она пройдёт насквозь и транспорт вернёт клиенту ошибку 500. Action не должен перехватывать это.

Правильно — обработать доменную ошибку:

```python
@aspect("Загрузка продукта")
async def load_product(self, params, state, deps):
    repo = deps.get(IProductRepository)
    try:
        product = await repo.get(params.product_id)
    except ValueError as e:
        raise ValueError(f"Продукт {params.product_id} не найден") from e
    state["product"] = product
    return state
```

Здесь ValueError — доменная ошибка, её обработка — часть бизнес-логики.

---

## Никогда не делай это в ресурсе

Ресурс не должен принимать бизнес-решения на основе ошибок. Неправильно:

```python
async def get_product(self, product_id: int):
    try:
        return await self._db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    except Exception:
        return None  # НЕЛЬЗЯ — скрываем ошибку, Action не узнает что пошло не так
```

Такой подход скрывает ошибку и лишает Action возможности принять правильное решение. Всегда поднимай исключение.

---

## Полный пример правильного ресурса

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from ActionMachine.Core.Exceptions import HandleException

@dataclass
class Product:
    id: int
    name: str
    price: float
    stock: int

class IProductRepository(ABC):

    @abstractmethod
    async def get(self, product_id: int) -> Product: ...

    @abstractmethod
    async def update_stock(self, product_id: int, quantity: int) -> None: ...


class PostgresProductRepository(IProductRepository):

    def __init__(self, pool):
        self._pool = pool

    async def get(self, product_id: int) -> Product:
        try:
            row = await self._pool.fetchrow(
                "SELECT id, name, price, stock FROM products WHERE id = $1",
                product_id
            )
            if row is None:
                raise ValueError(f"Продукт с id={product_id} не найден")
            return Product(
                id=row["id"],
                name=row["name"],
                price=row["price"],
                stock=row["stock"]
            )
        except ValueError:
            raise
        except Exception as e:
            raise HandleException(f"Ошибка загрузки продукта {product_id}: {e}") from e

    async def update_stock(self, product_id: int, quantity: int) -> None:
        try:
            await self._pool.execute(
                "UPDATE products SET stock = stock - $1 WHERE id = $2",
                quantity, product_id
            )
        except Exception as e:
            raise HandleException(f"Ошибка обновления остатков: {e}") from e
```

Что здесь правильно:

ValueError для доменной ошибки — продукт не найден. HandleException для инфраструктурных ошибок — проблемы с БД. Явный re-raise ValueError чтобы не перехватить его в блоке except Exception. Чистый маппинг из строки БД в доменный объект Product. Нет бизнес-решений — только транспорт и маппинг.

---

## Тестирование обработки ошибок

В тестах ошибки ресурса имитируются через фейковые реализации:

```python
class FakeProductRepository(IProductRepository):

    def __init__(self, should_fail: bool = False):
        self._should_fail = should_fail

    async def get(self, product_id: int) -> Product:
        if self._should_fail:
            raise HandleException("Симуляция недоступности БД")
        if product_id == 999:
            raise ValueError(f"Продукт {product_id} не найден")
        return Product(id=product_id, name="Test", price=100.0, stock=10)

    async def update_stock(self, product_id: int, quantity: int) -> None:
        pass


async def test_product_not_found():
    machine = ActionTestMachine({
        IProductRepository: FakeProductRepository()
    })
    with pytest.raises(ValueError, match="не найден"):
        await machine.run(
            LoadProductAction(),
            LoadProductAction.Params(product_id=999)
        )


async def test_db_unavailable():
    machine = ActionTestMachine({
        IProductRepository: FakeProductRepository(should_fail=True)
    })
    with pytest.raises(HandleException, match="недоступности БД"):
        await machine.run(
            LoadProductAction(),
            LoadProductAction.Params(product_id=1)
        )
```

---

## Итоговые правила

Первое. Ресурс ловит все внешние исключения и оборачивает их в HandleException или доменные ошибки.

Второе. Если ошибка имеет бизнес-смысл — поднимай ValueError или кастомное доменное исключение.

Третье. Если ошибка инфраструктурная — поднимай HandleException с понятным сообщением.

Четвёртое. Никогда не возвращай None вместо исключения.

Пятое. Action пропускает HandleException наверх и обрабатывает только доменные ошибки.

Шестое. Тесты проверяют оба типа ошибок через фейковые реализации портов.

---

## Что изучать дальше

14_machine.md — жизненный цикл и пайплайн ActionMachine.

15_di.md — декларативное внедрение зависимостей.

16_transactions.md — управление транзакциями в ресурсах.

19_testing.md — полное руководство по тестированию.

26_migrating_legacy.md — как правильно обёртывать легаси с ошибками.
