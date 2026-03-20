# src/action_machine/aspects/summary_aspect.py

def summary_aspect(description: str):
    """
    Декоратор для summary-аспекта.

    Не регистрирует аспект напрямую, а лишь добавляет временный атрибут
    `_new_aspect_meta` к методу. Регистрация выполняется позже классом
    `AspectGateHost` при создании класса действия.

    Аргументы:
        description: описание аспекта.

    Возвращает:
        Декорированный метод с добавленным атрибутом.
    """
    def decorator(method):
        method._new_aspect_meta = {
            'description': description,
            'type': 'summary'
        }
        return method
    return decorator