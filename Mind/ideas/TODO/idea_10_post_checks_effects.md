idea_10_post_checks_effects.md

Постпроверки эффектов (Post-checks for Resources)

Проблема

В классическом тестировании разработчик проверяет только то, что вернуло действие — Result. Но бизнес-операция часто производит побочные эффекты: вставляет записи в базу данных, отправляет письма, обновляет кэш, создаёт файлы. Эти эффекты остаются непроверенными, если разработчик не написал отдельные assert-ы вручную после каждого вызова. В результате тест может пройти успешно (Result корректен), но в базе данных может не оказаться нужной записи, письмо может не уйти, а файл может быть пустым [6].

Проблема усугубляется тем, что для проверки побочных эффектов нужен доступ к ресурсам — к тем же репозиториям, сервисам и менеджерам соединений, которые использовало действие. В обычных фреймворках этот доступ приходится организовывать вручную, дублируя конфигурацию DI из основного кода в тестах.

Решение

В AOA все ресурсы уже доступны через DI [2], а ActionTestMachine даёт удобный способ их подмены [2]. Постпроверки используют тот же механизм: после выполнения действия разработчик может обратиться к любой зависимости через фабрику и проверить её состояние. Это не требует отдельной инфраструктуры — достаточно написать assert-ы к мокам или фейкам, которые уже переданы в ActionTestMachine.

Как это работает

Постпроверки выполняются после machine.run() и имеют доступ ко всем зависимостям, переданным в ActionTestMachine. Поскольку моки и фейки — обычные Python-объекты с состоянием, разработчик может проверить любое поле, список вызовов, содержимое буфера.

Пример

```python
@pytest.mark.asyncio
async def test_create_order_with_post_checks():
    fake_order_repo = FakeOrderRepository()
    fake_email = FakeEmailService()
    fake_inventory = FakeInventoryService()

    machine = ActionTestMachine(
        {
            OrderRepository: fake_order_repo,
            EmailService: fake_email,
            InventoryService: fake_inventory,
        },
        context=Context(user=UserInfo(roles=["manager"]))
    )

    result = await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(
            user_id=1, product_id=10, quantity=2
        )
    )

    # Проверка Result — как обычно
    assert result.order_id > 0
    assert result.success is True

    # Постпроверки побочных эффектов
    # 1. Запись в базе данных действительно создана
    assert fake_order_repo.last_saved_order is not None
    assert fake_order_repo.last_saved_order["user_id"] == 1
    assert fake_order_repo.last_saved_order["product_id"] == 10
    assert fake_order_repo.last_saved_order["quantity"] == 2

    # 2. Письмо отправлено правильному получателю
    assert fake_email.sent_count == 1
    assert fake_email.last_recipient == "[EMAIL_REDACTED]"
    assert "заказ" in fake_email.last_subject.lower()

    # 3. Склад уменьшен на правильное количество
    assert fake_inventory.last_deducted_product == 10
    assert fake_inventory.last_deducted_quantity == 2
```

Как выглядят фейки для постпроверок

Фейки — это простые классы, которые реализуют интерфейс ресурса и записывают все вызовы во внутренние поля:

```python
class FakeOrderRepository:
    def __init__(self):
        self.last_saved_order = None
        self.save_count = 0

    def save(self, order_data):
        self.last_saved_order = order_data
        self.save_count += 1
        return {"id": 42, **order_data}


class FakeEmailService:
    def __init__(self):
        self.sent_count = 0
        self.last_recipient = None
        self.last_subject = None

    def send(self, to, subject, body):
        self.sent_count += 1
        self.last_recipient = to
        self.last_subject = subject


class FakeInventoryService:
    def __init__(self):
        self.last_deducted_product = None
        self.last_deducted_quantity = None

    def deduct(self, product_id, quantity):
        self.last_deducted_product = product_id
        self.last_deducted_quantity = quantity
```

Фейки не требуют специального базового класса или регистрации — они просто передаются в ActionTestMachine как обычные зависимости [2].

Сочетание с Action Interrogation

Постпроверки идеально сочетаются с мультиассерт-режимом (idea_05). Каждый побочный эффект проверяется как независимый assert, и все ошибки видны сразу:

```python
multi_assert(
    # Result
    lambda: assert_eq(result.order_id, 42,
                      "ID заказа"),
    lambda: assert_eq(result.success, True,
                      "Успешность"),

    # Побочный эффект: база данных
    lambda: assert_eq(fake_order_repo.save_count, 1,
                      "Заказ сохранён в БД"),
    lambda: assert_eq(fake_order_repo.last_saved_order["quantity"], 2,
                      "Количество в заказе"),

    # Побочный эффект: email
    lambda: assert_eq(fake_email.sent_count, 1,
                      "Письмо отправлено"),
    lambda: assert_eq(fake_email.last_recipient, "[EMAIL_REDACTED]",
                      "Получатель письма"),

    # Побочный эффект: склад
    lambda: assert_eq(fake_inventory.last_deducted_quantity, 2,
                      "Списание со склада"),
)
```

Один запуск действия, семь независимых проверок — три на Result и четыре на побочные эффекты. Все ошибки видны в одном отчёте.

Влияние

Тесты становятся глубже — проверяются не только возвращаемые значения, но и реальные последствия бизнес-операции.

Упрощается написание интеграционных тестов, потому что не нужно отдельно конфигурировать доступ к ресурсам — они уже доступны через DI [2].

Повышается уверенность в корректности взаимодействия с ресурсами. Если действие вернуло правильный Result, но не записало заказ в базу — постпроверка это обнаружит.

Фейки служат двойную роль: они и подменяют реальные ресурсы (позволяя действию выполниться без инфраструктуры), и записывают все обращения (позволяя проверить побочные эффекты).

Уникальность

В AOA все ресурсы уже доступны через DI [2], а ActionTestMachine даёт удобный способ их подмены [2]. Постпроверки не требуют отдельного фреймворка или специальной инфраструктуры — они являются естественным продолжением тестирования в AOA. Фейк — это одновременно мок для DI и журнал побочных эффектов для проверки.

В других фреймворках для проверки побочных эффектов обычно нужно либо поднимать реальную базу данных и делать SELECT после теста, либо использовать сложные mock-библиотеки (unittest.mock, MagicMock) с assert_called_with. В AOA достаточно простого фейка с полями, потому что DI-система прозрачна и подконтрольна разработчику [2].

Связь с другими идеями

Action Interrogation (idea_05) — мультиассерт превращает постпроверки из последовательности assert-ов в параллельный «допрос», где каждый побочный эффект проверяется независимо.

Auto-rollback Mode (idea_09) — при использовании реальной базы данных постпроверки могут выполнять SELECT внутри транзакции, которая откатится после теста. Данные видны внутри транзакции, но не загрязняют базу.

Генерация тестов из production-логов (idea_08) — LLM-агент, генерирующий тесты, может автоматически добавлять постпроверки для каждого ресурса, который использовало действие. Он видит, какие зависимости объявлены через @depends [2], и создаёт фейки с проверками.

Таймауты действий (idea_07) — постпроверки могут включать проверку того, что таймаут не был превышен, как один из независимых assert-ов.

Востребованность

Средне-высокая. Полезна для любых систем с побочными эффектами — а это практически все реальные приложения. Особенно ценна для систем с множеством ресурсов (БД + email + очередь + файлы), где ошибка в одном побочном эффекте может остаться незамеченной при проверке только Result.