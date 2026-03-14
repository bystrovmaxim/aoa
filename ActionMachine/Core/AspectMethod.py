# ActionMachine/Core/AspectMethod.py
"""
Протокол аспектных методов и декораторы для их объявления.

Содержит:
- AspectMethod — протокол, описывающий методы с атрибутами аспектов.
- aspect() — декоратор для обычных аспектов.
- summary_aspect() — декоратор для главного (summary) аспекта.
- depends() — декоратор для объявления зависимостей действия.
"""

from typing import Any, Callable, Optional, Protocol, Type, runtime_checkable, cast


@runtime_checkable
class AspectMethod(Protocol):
    """
    Протокол, описывающий методы, помеченные декораторами aspect/summary_aspect.

    Атрибуты:
        _is_aspect: флаг, что метод является аспектом.
        _aspect_description: текстовое описание аспекта.
        _aspect_type: тип аспекта ('regular' или 'summary').
        __code__: объект кода (для сортировки по номеру строки).
        __name__: имя метода.
        __qualname__: квалифицированное имя метода.
        __call__: сигнатура вызова метода.
    """

    _is_aspect: bool
    _aspect_description: str
    _aspect_type: str
    __code__: Any
    __name__: str
    __qualname__: str
    __call__: Callable[..., Any]


def aspect(description: str) -> Callable[[Callable[..., Any]], AspectMethod]:
    """
    Декоратор для обычных аспектов.

    Помечает метод как регулярный аспект, который выполняется перед summary.
    Метод должен принимать (self, params, state, deps) и возвращать dict.

    Аргументы:
        description: текстовое описание аспекта (для документации и логирования).

    Возвращает:
        Декоратор, который добавляет атрибуты аспекта к методу.
    """
    def decorator(method: Callable[..., Any]) -> AspectMethod:
        method._is_aspect = True                      # type: ignore[attr-defined]
        method._aspect_description = description       # type: ignore[attr-defined]
        method._aspect_type = 'regular'                # type: ignore[attr-defined]
        return cast(AspectMethod, method)
    return decorator


def summary_aspect(description: str) -> Callable[[Callable[..., Any]], AspectMethod]:
    """
    Декоратор для главного аспекта (должен быть ровно один в каждом действии).

    Summary-аспект выполняется последним и возвращает итоговый Result.

    Аргументы:
        description: текстовое описание аспекта (для документации и логирования).

    Возвращает:
        Декоратор, который добавляет атрибуты summary-аспекта к методу.
    """
    def decorator(method: Callable[..., Any]) -> AspectMethod:
        method._is_aspect = True                      # type: ignore[attr-defined]
        method._aspect_description = description       # type: ignore[attr-defined]
        method._aspect_type = 'summary'                # type: ignore[attr-defined]
        return cast(AspectMethod, method)
    return decorator


def depends(
    klass: Type[Any],
    *,
    description: str = "",
    factory: Optional[Callable[[], Any]] = None,
) -> Callable[[Type[Any]], Type[Any]]:
    """
    Декоратор для объявления зависимости действия от любого класса.

    Может использоваться несколько раз для одного действия.
    Создаёт новый список зависимостей для каждого класса (не мутирует родительский).

    Аргументы:
        klass: класс зависимости (может быть Action, сервис, репозиторий и т.д.)
        description: описание зависимости (для документации).
        factory: опциональная фабрика для создания экземпляра.
                 Если не указана, используется конструктор по умолчанию.

    Возвращает:
        Декоратор, который добавляет информацию о зависимости в атрибут _dependencies.
    """
    def decorator(cls: Type[Any]) -> Type[Any]:
        # Создаём НОВЫЙ список, копируя родительский (если есть)
        deps = list(getattr(cls, '_dependencies', []))
        deps.append({
            'class': klass,
            'description': description,
            'factory': factory,
        })
        cls._dependencies = deps
        return cls
    return decorator
