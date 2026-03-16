idea_06_env_manager.md

Ресурсный менеджер для переменных окружения (EnvManager)

Проблема

В типичных приложениях доступ к переменным окружения разбросан по всему коду: os.getenv вызывается в разных модулях, сервисах, конфигурационных файлах. Это приводит к дублированию, отсутствию типизации, сложности тестирования и невозможности понять, от каких переменных зависит конкретная бизнес-операция. При смене источника конфигурации (например, переход с переменных окружения на Vault или etcd) приходится менять код во множестве мест [6].

Решение

Создать ресурсный менеджер EnvManager, который инкапсулирует доступ к переменным окружения и предоставляет чистый, типизированный интерфейс для действий. Вместо прямых вызовов os.getenv действие объявляет зависимость от EnvManager через @depends и получает значения через типизированные методы: get_str, get_int, get_bool, get_float [6].

Как это работает

EnvManager реализуется как обычный ресурсный менеджер, доступный через DI [2]. Действие объявляет зависимость:

```python
@depends(EnvManager, description="Доступ к переменным окружения")
@CheckRoles(CheckRoles.ANY, desc="Доступно аутентифицированным пользователям")
class ProcessPaymentAction(BaseAction):

    @aspect("Получить конфигурацию")
    async def load_config(self, params, state, deps, connections):
        env = deps.get(EnvManager)
        state["api_url"] = env.get_str("PAYMENT_API_URL", required=True)
        state["timeout"] = env.get_int("PAYMENT_TIMEOUT", default=30)
        state["debug"] = env.get_bool("PAYMENT_DEBUG", default=False)
        return state

    @summary_aspect("Выполнить платёж")
    async def execute(self, params, state, deps, connections):
        # state["api_url"], state["timeout"], state["debug"] уже доступны
        ...
```

EnvManager предоставляет следующие методы:

get_str(key, default=None, required=False) — возвращает строковое значение. Если required=True и переменная не найдена — выбрасывает исключение.

get_int(key, default=None, required=False) — возвращает целое число. Если значение не может быть преобразовано в int — выбрасывает исключение с понятным сообщением.

get_bool(key, default=None, required=False) — интерпретирует строки "true", "1", "yes" как True, "false", "0", "no" как False. Регистронезависимо.

get_float(key, default=None, required=False) — аналогично get_int, но для чисел с плавающей точкой.

get_list(key, separator=",", default=None) — разбивает строковое значение по разделителю и возвращает список строк.

Каждый метод выбрасывает типизированное исключение (ConfigurationError) с указанием имени переменной и причины ошибки, что упрощает отладку.

Тестирование

В тестах EnvManager подменяется через ActionTestMachine [2] точно так же, как любая другая зависимость:

```python
class MockEnvManager:
    def __init__(self, values):
        self._values = values

    def get_str(self, key, default=None, required=False):
        if key in self._values:
            return str(self._values[key])
        if required:
            raise ConfigurationError(f"Variable {key} not set")
        return default

    def get_int(self, key, default=None, required=False):
        val = self.get_str(key, default=default, required=required)
        return int(val) if val is not None else None

    # ... аналогично для остальных методов


machine = ActionTestMachine({
    EnvManager: MockEnvManager({
        "PAYMENT_API_URL": "https://test.api.com",
        "PAYMENT_TIMEOUT": "10",
        "PAYMENT_DEBUG": "true",
    })
})

result = await machine.run(ProcessPaymentAction(), params)
```

Тесты не зависят от реальных переменных окружения. Каждый тест может задать свой набор значений, включая отсутствие переменных для проверки обработки ошибок.

Расширяемость

EnvManager определяется как интерфейс (порт). Реализация по умолчанию читает os.environ, но при необходимости можно создать адаптеры для других источников конфигурации:

OsEnvManager — стандартная реализация, читает os.environ.

VaultEnvManager — получает секреты из HashiCorp Vault.

EtcdEnvManager — читает конфигурацию из etcd.

DotenvEnvManager — загружает переменные из .env файла.

FileEnvManager — читает из YAML/JSON конфигурационного файла.

Действия не меняются при смене источника — они работают с интерфейсом EnvManager, а конкретная реализация подставляется через DI при создании машины или при регистрации в транспортном слое [6].

Влияние

Прозрачность — зависимости от переменных окружения становятся частью декларации действия через @depends [2], а не размазаны по коду. Открывая класс действия, разработчик сразу видит, что оно зависит от EnvManager.

Тестируемость — в тестах можно подставить MockEnvManager с фиксированными значениями, не трогая реальные переменные окружения. Не нужно манипулировать os.environ в setUp/tearDown.

Безопасность — исключается случайное чтение несуществующих переменных. Метод с required=True гарантирует, что отсутствие критической переменной будет обнаружено немедленно, с понятным сообщением об ошибке.

Единообразие — все действия получают конфигурацию одинаково, через deps.get(EnvManager). Нет разброса между os.getenv, settings.VARIABLE, config["key"] в разных частях кода.

Гибкость — при необходимости перейти на централизованное хранилище конфигурации (Vault, etcd) достаточно заменить реализацию EnvManager, не трогая ни одного действия.

Типизация — get_int, get_bool, get_float автоматически преобразуют строковые значения в нужные типы и выбрасывают понятные ошибки при невозможности преобразования. Это устраняет целый класс багов, связанных с ручным парсингом строк.

Уникальность

В mainstream-фреймворках работа с переменными окружения остаётся «сырой» [6]. Django предлагает settings.py, FastAPI — Pydantic BaseSettings, но ни один из них не интегрирует конфигурацию с DI на уровне бизнес-действий. В AOA EnvManager — это полноценная зависимость, объявленная через @depends, подменяемая в тестах через ActionTestMachine [2] и заменяемая на альтернативный источник без изменения кода действий.

Связь с другими идеями

EnvManager естественно интегрируется с декларативной генерацией транспорта (idea_04): при регистрации действия в FastAPIRegistry или MCPRegistry можно передать конкретную реализацию EnvManager через resources, что делает конфигурацию частью композиционного корня [6]. В сочетании с координатором логеров (idea_02) значения из EnvManager (например, environment, service_name) могут автоматически подставляться в шаблоны логов через контекст [6].