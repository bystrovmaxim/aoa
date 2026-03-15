# Новая структура документации ActionEngine / AOA

---

## Блок 1. Введение и старт
```
01_index.md               — Что такое ActionEngine и AOA. Зачем. Какие боли решает.
02_getting_started.md     — Установка. Первое действие. Запуск. Минимальный рабочий пример.
03_glossary.md            — Глоссарий всех терминов AOA.
```

## Блок 2. Концепции
```
04_concepts.md            — Все базовые сущности: Action, Aspect, Params, Result, State, Plugin, Resource, DI, Context.
05_philosophy.md          — Философия AOA. Почему именно так. Золотые принципы.
06_guarantees.md          — Формальные гарантии AOA. Что обеспечивает архитектура.
```

## Блок 3. Actions и Aspects
```
07_actions.md             — Как писать Actions. Params, Result, аспекты, зависимости, CheckRoles.
08_aspects_vs_actions.md  — Когда аспект, когда action. Алгоритм выбора. Примеры трансформации.
09_typed_state.md         — TypedDict и state. Чекеры. Контракт аспекта.
```

## Блок 4. Ресурсы
```
10_resource_managers.md         — Что такое ресурс. Порт/адаптер. Структура. Примеры.
11_action_vs_resource.md        — Когда action, когда resource. Золотое правило.
12_create_resource_manager.md   — Пошаговое создание своего менеджера ресурсов. Прокси.
13_errors_in_resources.md       — Обработка ошибок в ресурсах. Когда бросать, когда оборачивать.
```

## Блок 5. Машина и DI
```
14_machine.md             — ActionMachine. Жизненный цикл. Pipeline. Роли. Кэширование.
15_di.md                  — DI в AOA. @depends. DependencyFactory. factory=. Вложенные действия.
16_transactions.md        — Управление транзакциями. connections. Прокси. Явность без магии.
17_async.md               — Асинхронность. asyncio. run_in_thread. Блокировки. CoreHelper.
```

## Блок 6. Плагины
```
18_plugins.md             — Плагины. События. @on. Состояние. Вложенность. Примеры.
```

## Блок 7. Тестирование
```
19_testing.md             — ActionTestMachine. MockAction. Тесты аспектов, действий, вложенности.
```

## Блок 8. Интеграции
```
20_auth_architecture.md         — Аутентификация. CredentialExtractor. Authenticator. ContextAssembler. AuthCoordinator.
21_fastapi_integration.md       — Интеграция с FastAPI. Полный цикл запроса.
22_mcp_integration.md           — Интеграция с MCP для LLM-агентов.
23_external_di_integration.md   — Интеграция с внешними DI-контейнерами (inject и др.).
```

## Блок 9. Архитектура и миграция
```
24_architecture_overview.md     — Слои, схемы, поток данных. UML. Диаграммы.
25_choosing_action_aspect_resource.md — Алгоритм выбора между action/aspect/resource.
26_migrating_legacy.md          — Пошаговая миграция легаси. Strangler-path.
27_legacy_examples.md           — Конкретные примеры трансформации монстров.
```

## Блок 10. Справочник
```
28_specification.md       — Формальная спецификация AOA v1.0. Аксиомы. Правила. Инварианты.
29_comparison.md          — Сравнение с MVC, Clean Architecture, CQRS, Service Layer.
30_examples.md            — Подборка законченных рабочих примеров от простого к сложному.
31_end_to_end_demo.md     — Полный пример от HTTP до результата в одном файле.
```

---

Готов? Начинаем с **01_index.md** — пиши «давай».