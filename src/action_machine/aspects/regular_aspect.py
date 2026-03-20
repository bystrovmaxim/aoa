# src/action_machine/aspects/regular_aspect.py

def regular_aspect(description: str):
    """
    Декоратор для обычных (regular) аспектов.

    Не регистрирует аспект напрямую, а лишь добавляет временный атрибут
    `_new_aspect_meta` к методу. Регистрация выполняется позже классом
    `AspectGateHost` при создании класса действия.

    Аргументы:
        description: описание аспекта (используется в логах и документации).

    Возвращает:
        Декорированный метод с добавленным атрибутом.
    """
    def decorator(method):
        method._new_aspect_meta = {
            'description': description,
            'type': 'regular'
        }
        return method
    return decorator