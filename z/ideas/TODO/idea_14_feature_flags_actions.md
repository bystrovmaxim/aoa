idea_14_feature_flags_actions.md

Управление фичами на уровне бизнес-операций (Feature Flags for Actions)

Проблема

В традиционных системах feature flags реализуются на уровне HTTP-эндпоинтов, конфигурационных файлов или условных ветвлений внутри кода. Это приводит к нескольким проблемам. Флаги размазаны по коду — условие `if feature_enabled("new_checkout")` появляется в контроллерах, сервисах, шаблонах. Нет централизованного понимания, какие бизнес-операции затронуты флагом. Невозможно быстро ответить на вопрос «какие фичи сейчас включены и на какие операции они влияют». При удалении флага приходится искать и удалять условия по всему коду. Тестирование с флагами требует дублирования setup-фазы для каждой комбинации.

В AOA бизнес-операции уже являются атомарными единицами с чёткими границами — Actions [2][5]. Это создаёт естественную точку для управления фичами: не на уровне строк кода, а на уровне целых бизнес-операций.

Решение

Декоратор @feature на уровне класса Action, который связывает действие с именованным флагом. ActionMachine проверяет состояние флага перед выполнением действия — до проверки ролей, до запуска аспектов, до вызова плагинов. Если флаг выключен, машина выбрасывает FeatureDisabledError с понятным сообщением, или возвращает альтернативный результат — в зависимости от конфигурации.

Источник состояния флагов — FeatureFlagProvider — это ресурсный менеджер, объявляемый через @depends [2]. Реализация может быть любой: файл конфигурации, переменная окружения через EnvManager (idea_06), Redis, LaunchDarkly, база данных. Действие не знает, откуда берётся состояние флага — оно просто объявляет зависимость от фичи.

Как это работает

Разработчик помечает Action декоратором @feature с именем флага:

```python
@feature("new_checkout_flow", fallback_result=None)
@depends(OrderRepository, description="Репозиторий заказов")
@CheckRoles(["user"], desc="Доступно пользователям")
class NewCheckoutAction(BaseAction):

    @aspect("Валидация корзины")
    @IntFieldChecker("items_count", desc="Количество товаров")
    async def validate(self, params, state, deps, connections):
        ...
        return {"items_count": len(params.items)}

    @summary_aspect("Оформление заказа")
    async def checkout(self, params, state, deps, connections):
        ...
        return NewCheckoutAction.Result(order_id=42)
```

ActionMachine при вызове run() выполняет проверку в следующем порядке:

1. Проверка feature flag — если флаг выключен, действие не выполняется.
2. Проверка ролей — @CheckRoles [2].
3. Проверка connections — @connection [2].
4. Событие global_start для плагинов.
5. Выполнение аспектов.

Проверка флага происходит раньше всего остального, потому что если фича выключена, нет смысла проверять роли или готовить зависимости.

Поведение при выключенном флаге

Разработчик выбирает один из двух режимов при объявлении @feature:

Режим исключения (по умолчанию) — если fallback_result не указан, машина выбрасывает FeatureDisabledError с именем флага и именем действия. Транспортный слой (FastAPI, MCP) может перехватить это исключение и вернуть HTTP 404, 501 или соответствующий ответ.

Режим альтернативного результата — если указан fallback_result, машина возвращает его как Result действия. Аспекты не выполняются, плагины получают событие feature_disabled вместо global_start/global_finish.

```python
# Режим исключения — эндпоинт отвечает 501
@feature("experimental_ai_search")
class AISearchAction(BaseAction):
    ...

# Режим альтернативного результата — тихий откат на старую версию
@feature("new_pricing", fallback_result=PricingAction.Result(price=0, source="legacy"))
class NewPricingAction(BaseAction):
    ...
```

FeatureFlagProvider — источник состояния флагов

Состояние флагов абстрагировано через интерфейс:

```python
class FeatureFlagProvider(ABC):
    @abstractmethod
    def is_enabled(self, flag_name: str, context: Optional[Context] = None) -> bool:
        """
        Проверяет, включён ли флаг.
        
        Может учитывать контекст: роли пользователя, окружение,
        процент раскатки и т.д.
        """
        pass
```

Реализации:

EnvFeatureFlagProvider — читает переменные окружения через EnvManager (idea_06). Имя переменной формируется из имени флага: FEATURE_NEW_CHECKOUT_FLOW=true.

ConfigFileFeatureFlagProvider — читает YAML/JSON файл с флагами. Удобно для локальной разработки.

RemoteFeatureFlagProvider — обращается к внешнему сервису (LaunchDarkly, Unleash, Flagsmith). Кэширует результат на время выполнения действия.

PercentageFeatureFlagProvider — включает флаг для заданного процента пользователей, используя user_id из Context для детерминированного хэширования. Один и тот же пользователь всегда получает одинаковый результат.

FeatureFlagProvider регистрируется как зависимость машины, а не отдельных действий. Машина получает его при инициализации и использует для проверки всех флагов.

Событие для плагинов

Когда действие заблокировано флагом, ActionMachine генерирует событие feature_disabled:

```python
@on('feature_disabled', '.*', ignore_exceptions=True)
async def on_feature_disabled(self, state_plugin, event):
    log(f"⛔ {event.action_name} blocked by feature flag '{event.feature_name}' "
        f"for user {event.context.user.user_id}")
    return state_plugin
```

Событие содержит: action_name, feature_name, context, fallback_used (True/False). Это позволяет мониторить, как часто срабатывают флаги и какие пользователи их «попадают».

Интеграция с интроспектором

Интроспектор бизнес-процессов (idea_12) может извлекать информацию о флагах из атрибута _feature_spec, добавляемого декоратором @feature [5]. Это позволяет автоматически генерировать:

Карту фич — какие Actions привязаны к каким флагам.

Отчёт по раскатке — какие фичи включены, какие выключены, какие в процентной раскатке.

Предупреждения об устаревших флагах — если флаг включён для всех пользователей более 30 дней, интроспектор предлагает удалить декоратор @feature и оставить Action как обычный.

Тестирование

В ActionTestMachine флаги управляются через MockFeatureFlagProvider:

```python
machine = ActionTestMachine(
    mocks={...},
    feature_flags={"new_checkout_flow": True, "experimental_ai_search": False}
)

# new_checkout_flow включён — действие выполняется
result = await machine.run(NewCheckoutAction(), params)
assert result.order_id == 42

# experimental_ai_search выключен — FeatureDisabledError
with pytest.raises(FeatureDisabledError):
    await machine.run(AISearchAction(), params)
```

В сочетании с Action Interrogation (idea_05) можно проверять оба варианта в одном тесте:

```python
# Тест с включённым флагом
machine_on = ActionTestMachine(feature_flags={"new_pricing": True})
result_on = await machine_on.run(NewPricingAction(), params)

# Тест с выключенным флагом (fallback)
machine_off = ActionTestMachine(feature_flags={"new_pricing": False})
result_off = await machine_off.run(NewPricingAction(), params)

multi_assert(
    lambda: assert_eq(result_on.source, "new_engine",
                      "Новый движок при включённом флаге"),
    lambda: assert_eq(result_off.source, "legacy",
                      "Откат на legacy при выключенном флаге"),
    lambda: assert_eq(result_off.price, 0,
                      "Цена по умолчанию при откате"),
)
```

Влияние

Централизованное управление. Все feature flags привязаны к Actions — атомарным бизнес-операциям. Нет разбросанных if-условий по коду. Включить или выключить фичу — это включить или выключить конкретное действие.

Безопасная раскатка. Canary deployments на уровне бизнес-операций: новая версия CreateOrderAction для 5% пользователей, старая — для остальных. Прокси-слой не нужен — всё решается внутри машины.

Чистый код. Действие не содержит условной логики «если фича включена — делай так, иначе — эдак». Есть два Action: старый и новый. Флаг определяет, какой из них вызывается.

Мониторинг. Через плагинную систему [2] видно, как часто срабатывает каждый флаг, для каких пользователей, и есть ли ошибки в новой версии.

Тестируемость. Оба варианта (включён/выключен) тестируются одинаково через ActionTestMachine, без манипуляций с глобальным состоянием.

Уникальность

Существующие системы feature flags (LaunchDarkly, Unleash, django-waffle) работают на уровне HTTP-запросов или произвольных точек в коде. Ни одна из них не интегрирована с формальной моделью бизнес-операций. В AOA feature flag — это атрибут бизнес-операции, а не строчка кода. Это значит, что:

Интроспектор может построить полную карту фич из метаданных [5].
Декларативная генерация транспорта (idea_04) может автоматически скрывать эндпоинты выключенных фич из OpenAPI.
Генерация тестов из production-логов (idea_08) может группировать тесты по вариантам фич.
LLM-агент может спросить «какие фичи сейчас в тестировании» и получить ответ из метаданных Actions.

Связь с другими идеями

EnvManager (idea_06) — простейшая реализация FeatureFlagProvider через переменные окружения.

Декларативная генерация транспорта (idea_04) — регистратор может автоматически не создавать эндпоинт для действия с выключенным флагом, или добавлять пометку «experimental» в OpenAPI.

Интроспектор бизнес-процессов (idea_12) — извлекает информацию о флагах и генерирует карту фич.

Координатор логеров (idea_02) — отдельный шаблон для логирования срабатываний флагов.

Action Interrogation (idea_05) — мультиассерт-тесты для обоих вариантов фичи.

Генерация тестов из production-логов (idea_08) — LLM видит в дереве выполнения, какой вариант фичи использовался, и генерирует тесты для обоих.