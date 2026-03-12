from typing import Any, Callable, Optional, Protocol, Type, runtime_checkable, cast

@runtime_checkable
class AspectMethod(Protocol):
    """Протокол, описывающий методы, помеченные декораторами aspect/summary_aspect."""
    _is_aspect: bool
    _aspect_description: str
    _aspect_type: str          # 'regular' или 'summary'
    __code__: Any
    __qualname__: str
    __call__: Callable[..., Any]

def aspect(description: str) -> Callable[[Callable[..., Any]], AspectMethod]:
    """Декоратор для обычных аспектов."""
    def decorator(method: Callable[..., Any]) -> AspectMethod:
        method._is_aspect = True                     # type: ignore[attr-defined]
        method._aspect_description = description      # type: ignore[attr-defined]
        method._aspect_type = 'regular'               # type: ignore[attr-defined]
        return cast(AspectMethod, method)
    return decorator

def summary_aspect(description: str) -> Callable[[Callable[..., Any]], AspectMethod]:
    """Декоратор для главного аспекта (должен быть ровно один)."""
    def decorator(method: Callable[..., Any]) -> AspectMethod:
        method._is_aspect = True                     # type: ignore[attr-defined]
        method._aspect_description = description      # type: ignore[attr-defined]
        method._aspect_type = 'summary'               # type: ignore[attr-defined]
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

    Аргументы:
        klass: класс зависимости (может быть Action, сервис, репозиторий и т.д.)
        description: описание зависимости (для документации).
        factory: опциональная фабрика для создания экземпляра.
                 Если не указана, используется конструктор по умолчанию.
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