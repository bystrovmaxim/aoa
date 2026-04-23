# Миграция Graph Runtime

## Цель

Этот документ описывает целевой runtime-протокол для graph-слоя.
Задача состоит в том, чтобы перевести `ActionProductMachine` и связанные
runtime-компоненты с legacy snapshot API у `GraphCoordinator` на стабильный,
минимальный protocol, который смогут реализовать и старый, и новый graph stack.

Протокол должен определяться потребностями рантайма, а не формой конкретного
координатора.

## Текущее состояние

Сейчас рантайм напрямую зависит от `GraphCoordinator`:

- `ActionProductMachine` читает `get_snapshot(..., "role" | "connections" | "aspect" | "checker" | "compensator" | "error_handler")`
- `DependencyFactory` читает `get_snapshot(..., "depends")`
- MCP и часть plugin-кода всё ещё читают graph-specific metadata из legacy coordinator

`NodeGraphCoordinator` уже является целевой топологической моделью, но пока не
предоставляет runtime-контракт метаданных, который нужен машине.

## Целевое направление

Мы не будем мигрировать так, чтобы машина одновременно понимала две графовые
системы.

Вместо этого:

1. Определяем новый runtime protocol как отдельную цель.
2. Временно даём legacy `GraphCoordinator` реализовать этот protocol.
3. Даём новому node-graph stack нативно реализовать тот же protocol.
4. Переводим runtime-callers на protocol.
5. Удаляем legacy-only методы после миграции всех callers.

Во время перехода legacy coordinator может внутри делегировать методы protocol
provider-у, построенному на node graph.

## Правила дизайна

Протокол должен:

- отдавать runtime-факты, а не внутренности графа
- не тащить в себя `FacetVertex`, snapshot-классы и задачи визуализации
- быть маленьким и sliceable, чтобы миграция шла по одной возможности за раз
- быть реализуемым и в legacy-коде, и в node-graph-коде

Протокол не должен:

- повторять весь API `GraphCoordinator`
- требовать от runtime-callers знания graph node types
- сохранять legacy-методы только потому, что они были раньше

## Целевой Runtime Protocol

В конечном состоянии должен появиться runtime-facing provider с единым источником
правды для action execution metadata.

```python
from collections.abc import Sequence
from typing import Any, Protocol


class ActionRuntimeMetadata(Protocol):
    @property
    def role_spec(self) -> Any: ...

    @property
    def connection_keys(self) -> tuple[str, ...]: ...

    @property
    def regular_aspects(self) -> tuple[Any, ...]: ...

    @property
    def summary_aspect(self) -> Any | None: ...

    @property
    def checkers_by_aspect(self) -> dict[str, tuple[Any, ...]]: ...

    @property
    def compensators_by_aspect(self) -> dict[str, Any | None]: ...

    @property
    def error_handlers(self) -> tuple[Any, ...]: ...

    @property
    def dependencies(self) -> tuple[Any, ...]: ...


class RuntimeMetadataProvider(Protocol):
    def get_action_metadata(self, action_cls: type) -> ActionRuntimeMetadata: ...
```

Это целевая форма, а не требование реализовать всё за один шаг.

## Первый Migration Slice

Миграцию нужно начинать с одного узкого protocol, а не со всего интерфейса
целиком.

Рекомендуемый первый slice:

```python
from typing import Any, Protocol


class ActionRoleMetadataProvider(Protocol):
    def get_role_spec(self, action_cls: type) -> Any: ...
```

Почему начинать стоит именно с него:

- он простой
- он критичен для рантайма
- у него нет dependency cache
- его легко поддержать и из legacy snapshots, и из node graph data

После этого добавляем по одному slice за раз:

1. `get_connection_keys(action_cls)`
2. `get_dependencies(action_cls)`
3. `get_action_metadata(action_cls)` для aspect pipeline data

## Архитектура Перехода

Переход должен выглядеть так:

```text
today:
ActionProductMachine -> GraphCoordinator -> get_snapshot(...)

transition:
ActionProductMachine -> RuntimeMetadataProvider
                                 |
                  +--------------+--------------+
                  |                             |
          LegacyGraphCoordinator         NodeGraphRuntimeProvider
          (delegates if needed)          (native implementation)

конечное состояние:
ActionProductMachine -> RuntimeMetadataProvider -> NodeGraph-based implementation
```

## Совместимость Legacy Coordinator

Во время миграции legacy coordinator может реализовывать новый runtime protocol
через делегацию.

Это допустимо тогда и только тогда, когда:

- делегация ограничена только новым runtime protocol
- legacy-only graph API больше не расширяется
- legacy coordinator выступает как временный compatibility facade

Это допустимо:

```python
class GraphCoordinator:
    def __init__(self, runtime_provider: RuntimeMetadataProvider | None = None) -> None:
        self._runtime_provider = runtime_provider

    def get_role_spec(self, action_cls: type) -> object | None:
        if self._runtime_provider is not None:
            return self._runtime_provider.get_action_metadata(action_cls).role_spec
        snap = self.get_snapshot(action_cls, "role")
        return getattr(snap, "spec", None) if snap is not None else None
```

Это недопустимо:

- превращать `GraphCoordinator` в постоянную обёртку над всем node-graph behavior
- заново воспроизводить каждый legacy method поверх `NodeGraphCoordinator`
- позволить рантайму бесконечно читать legacy snapshots

## Что Заменяет Новый Protocol

Со временем новый runtime protocol должен заменить runtime-использование:

- `get_snapshot(...)`
- чтение `DependencyFactory` на основе legacy `"depends"` snapshots
- runtime-specific metadata reads в adapters и plugin filtering

Он не обязан сразу заменять все graph-facing API, особенно:

- visualization exports
- topology inspection helpers
- debugging-only graph reads

Эти части можно мигрировать отдельно или удалить, когда они перестанут быть нужны.

## Практический Порядок Миграции

1. Вводим первый маленький runtime protocol в runtime-слое.
2. Реализуем его в legacy-коде через текущие snapshots.
3. Реализуем тот же protocol в node-graph-backed коде.
4. Переключаем один runtime-caller на этот protocol.
5. Повторяем по одной возможности за раз.
6. Удаляем legacy runtime methods после исчезновения всех callers.
7. Удаляем `FacetVertex`, legacy inspectors и `GraphCoordinator` только после того, как рантайм перестанет от них зависеть.

## Условие Успеха

Миграция считается завершённой, когда:

- `ActionProductMachine` больше не зависит от `GraphCoordinator`
- рантайм больше не читает legacy snapshots напрямую
- node-graph-backed providers становятся единственным источником runtime metadata
- legacy graph API либо удалены, либо ограничены non-runtime tooling
