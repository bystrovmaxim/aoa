"""
ConnectionGateHost – миксин для присоединения шлюза соединений к классу действия.

Этот миксин используется в иерархии BaseAction. Он:
- Объявляет атрибут _connection_info для использования декоратором @connection.
- Создаёт экземпляр ConnectionGate для класса (один на класс, разделяется всеми экземплярами).
- Собирает информацию о соединениях из декораторов @connection, применённых к классу.
- После сбора замораживает шлюз, чтобы гарантировать неизменность набора соединений.
- Предоставляет метод get_connection_gate() для доступа к шлюзу из машины.

Механизм сбора:
    Декоратор @connection при применении к классу добавляет в класс атрибут
    _connection_info (список ConnectionInfo). Поскольку декоратор класса применяется
    ПОСЛЕ __init_subclass__, сбор данных выполняется лениво при первом вызове
    get_connection_gate(). Шлюз замораживается после первого сбора.

Важно:
    Шлюз хранится в классовой переменной __connection_gate. При наследовании каждый
    подкласс получает свой собственный шлюз благодаря проверке в get_connection_gate().
"""

from typing import Any, ClassVar

from .connection_gate import ConnectionGate, ConnectionInfo


class ConnectionGateHost:
    """
    Миксин, добавляющий классу шлюз соединений.

    Классовые атрибуты:
        __connection_gate: ConnectionGate | None – шлюз, общий для всех экземпляров данного класса.
        _connection_info: list[ConnectionInfo] | None – временное хранилище,
                         используемое декоратором @connection для передачи данных.
                         Собирается лениво в get_connection_gate().
    """

    __connection_gate: ClassVar[ConnectionGate | None] = None
    _connection_info: ClassVar[list[ConnectionInfo] | None] = None

    @classmethod
    def get_connection_gate(cls) -> ConnectionGate:
        """
        Возвращает шлюз соединений для данного класса.

        Шлюз создаётся и заполняется лениво при первом вызове.
        Если в классе есть _connection_info (установленный декоратором @connection),
        все соединения регистрируются в шлюзе, и шлюз замораживается.

        Ленивая инициализация необходима потому, что декоратор класса (@connection)
        применяется ПОСЛЕ __init_subclass__. На момент вызова __init_subclass__
        атрибут _connection_info ещё не установлен.

        Проверка cls.__dict__ гарантирует, что мы не используем шлюз родителя.

        Возвращает:
            ConnectionGate, связанный с классом.
        """
        # Проверяем, что шлюз принадлежит именно этому классу, а не унаследован
        if '__connection_gate' not in cls.__dict__ or cls.__connection_gate is None:
            gate = ConnectionGate()

            # Собираем _connection_info, если он установлен декоратором @connection
            connection_info = getattr(cls, '_connection_info', None)
            if connection_info is not None:
                for info in connection_info:
                    gate.register(info)

            gate.freeze()
            cls.__connection_gate = gate

        return cls.__connection_gate

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается при создании подкласса.

        Сбрасывает шлюз, чтобы при следующем вызове get_connection_gate()
        он был создан заново для этого конкретного класса.

        Не выполняет сбор _connection_info здесь, потому что декоратор @connection
        ещё не был применён на этом этапе (декоратор класса выполняется
        после __init_subclass__).

        Аргументы:
            **kwargs: передаются в родительский __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Сбрасываем шлюз для этого класса, чтобы он был создан заново
        # при следующем вызове get_connection_gate() (после применения @connection)
        cls.__connection_gate = None