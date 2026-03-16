# Changelog
Все заметные изменения в этом проекте будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-16

### Added
- **Единый протокол доступа к данным** – введены интерфейсы `ReadableDataProtocol` и `WritableDataProtocol`, которые стандартизируют работу с параметрами, результатами и состоянием действий.
- **Миксины для dataclass** – `ReadableMixin` и `WritableMixin`, позволяющие существующим dataclass-моделям автоматически удовлетворять новым протоколам без изменения кода бизнес-логики.
- **Строгая типизация state** – состояние аспектов теперь всегда типизируется через `TypedDict` (или обычный dict), что обеспечивает полную проверку типов на этапе компиляции.
- **Руководство по миграции** – подробный документ с примерами перехода на новую версию (см. [docs/changelog/1.0.0-unified-data-protocol.md](docs/changelog/1.0.0-unified-data-protocol.md)).

### Changed
- **Ядро (`ActionProductMachine`, `DependencyFactory`)** полностью переработано для работы через протоколы, что устранило зависимость от конкретных реализаций `BaseParams`/`BaseResult`.
- **`BaseParams` и `BaseResult`** больше не являются абстрактными классами; они наследуют соответствующие миксины и реализуют dict-подобный доступ.
- **Плагины** теперь получают данные через `PluginEvent` с чёткими типами: `params: ReadableDataProtocol`, `state_aspect: Optional[dict[str, object]]`, `result: Optional[WritableDataProtocol]`. Все стандартные плагины переписаны на dict-доступ.
- **Тесты** обновлены для покрытия новых сценариев (TypedDict в качестве входных данных, state как dict, моки с side_effect и т.д.).

### Removed
- Устаревший атрибутный доступ к полям в ядре и плагинах. Теперь только `obj["key"]`.
- Неиспользуемые импорты и мёртвый код (проверено `vulture`).

### Fixed
- Циклический импорт в `ActionProductMachine` (удалён неверный self-импорт).
- Все ошибки `mypy --strict` (проект теперь полностью типизирован).
- Достигнут максимальный рейтинг `pylint` (10.00/10) и нулевое количество предупреждений `vulture`.

[1.0.0]: https://github.com/your-repo/kanban_assistant/releases/tag/v1.0.0