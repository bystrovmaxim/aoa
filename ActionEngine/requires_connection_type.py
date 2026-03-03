# Файл: ActionEngine/ConnectionTypeDecorator.py
"""
Декоратор для указания требуемого типа соединения в наследниках BaseInnerTransactionAction.

Требования:
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
def requires_connection_type(connection_class):
    """
    Декоратор для классов-наследников BaseInnerTransactionAction.
    Указывает, какой тип соединения требуется для выполнения действия.
    В run() будет выполнена проверка соответствия типа, и при несоответствии
    будет выброшено TypeError с сообщением на русском.

    Пример использования:
        @requires_connection_type(psycopg2.extensions.connection)
        class MyInnerAction(BaseInnerTransactionAction):
            ...
    """
    def decorator(cls):
        cls._required_connection_class = connection_class
        return cls
    return decorator