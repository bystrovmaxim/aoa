# src/action_machine/dependencies/dependency_gate_host.py
"""
DependencyGateHost – миксин для присоединения шлюза зависимостей к классу действия.

Этот миксин используется в иерархии BaseAction. Он:
- Создаёт экземпляр DependencyGate для класса (один на класс, разделяется всеми экземплярами).
- Собирает информацию о зависимостях из декораторов @depends, применённых к классу.
- Предоставляет метод get_dependency_gate() для доступа к шлюзу из машины и фабрики.

Механизм сбора:
    Декоратор @depends при применении к классу добавляет в класс атрибут
    _depends_info (список DependencyInfo). Поскольку декоратор класса применяется
    ПОСЛЕ __init_subclass__, сбор данных выполняется лениво при первом вызове
    get_dependency_gate(). Шлюз замораживается после первого сбора.

Обратная совместимость:
    На время миграции старый атрибут _dependencies продолжает существовать
    и заполняется параллельно. После полного перехода на шлюзы старый атрибут
    будет удалён.

Важно:
    Шлюз хранится в классовой переменной __dependency_gate. При наследовании каждый
    подкласс получает свой собственный шлюз благодаря проверке в get_dependency_gate().
"""

from typing import Any, ClassVar

from .dependency_gate import DependencyGate, DependencyInfo


class DependencyGateHost:
    """
    Миксин, добавляющий классу шлюз зависимостей.

    Классовые атрибуты:
        __dependency_gate: DependencyGate | None – шлюз, общий для всех экземпляров данного класса.
        _depends_info: list[DependencyInfo] | None – временное хранилище,
                         используемое декоратором @depends для передачи данных.
                         Собирается лениво в get_dependency_gate().
    """

    __dependency_gate: ClassVar[DependencyGate | None] = None
    _depends_info: ClassVar[list[DependencyInfo] | None] = None

    @classmethod
    def get_dependency_gate(cls) -> DependencyGate:
        """
        Возвращает шлюз зависимостей для данного класса.

        Шлюз создаётся и заполняется лениво при первом вызове.
        Если в классе есть _depends_info (установленный декоратором @depends),
        все зависимости регистрируются в шлюзе, и шлюз замораживается.

        Ленивая инициализация необходима потому, что декоратор класса (@depends)
        применяется ПОСЛЕ __init_subclass__. На момент вызова __init_subclass__
        атрибут _depends_info ещё не установлен.

        Проверка cls.__dict__ гарантирует, что мы не используем шлюз родителя.

        Возвращает:
            DependencyGate, связанный с классом.
        """
        # Проверяем, что шлюз принадлежит именно этому классу, а не унаследован
        if '__dependency_gate' not in cls.__dict__ or cls.__dependency_gate is None:
            gate = DependencyGate()

            # Собираем _depends_info, если он установлен декоратором @depends
            depends_info = getattr(cls, '_depends_info', None)
            if depends_info is not None:
                for info in depends_info:
                    gate.register(info)

            gate.freeze()
            cls.__dependency_gate = gate

        return cls.__dependency_gate

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается при создании подкласса.

        Сбрасывает шлюз, чтобы при следующем вызове get_dependency_gate()
        он был создан заново для этого конкретного класса.

        Не выполняет сбор _depends_info здесь, потому что декоратор @depends
        ещё не был применён на этом этапе (декоратор класса выполняется
        после __init_subclass__).

        Аргументы:
            **kwargs: передаются в родительский __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Сбрасываем шлюз для этого класса, чтобы он был создан заново
        # при следующем вызове get_dependency_gate() (после применения @depends)
        cls.__dependency_gate = None
