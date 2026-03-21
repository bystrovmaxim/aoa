# src/action_machine/dependencies/dependency_gate_host.py
"""
DependencyGateHost – миксин для присоединения шлюза зависимостей к классу действия.

Этот миксин используется в иерархии BaseAction. Он:
- Создаёт экземпляр DependencyGate для класса (один на класс, разделяется всеми экземплярами).
- Собирает информацию о зависимостях из декораторов @depends, применённых к классу.
- После сбора замораживает шлюз, чтобы гарантировать неизменность набора зависимостей.
- Предоставляет метод get_dependency_gate() для доступа к шлюзу из машины и фабрики.

Механизм сбора:
    Декоратор @depends при применении к классу добавляет в класс временный атрибут
    _depends_info (список DependencyInfo). В __init_subclass__ этот список
    собирается и регистрируется в шлюзе. После регистрации временный атрибут
    удаляется, чтобы не засорять класс.

Обратная совместимость:
    На время миграции старый атрибут _dependencies продолжает существовать
    и заполняется параллельно. После полного перехода на шлюзы старый атрибут
    будет удалён.

Важно:
    Шлюз хранится в классовой переменной __dependency_gate. При наследовании каждый
    подкласс получает свой собственный шлюз. Для этого в __init_subclass__
    явно сбрасывается __dependency_gate = None, чтобы при вызове get_dependency_gate()
    создавался новый шлюз для дочернего класса, а не использовался родительский.
"""

from typing import Any, ClassVar

from .dependency_gate import DependencyGate, DependencyInfo


class DependencyGateHost:
    """
    Миксин, добавляющий классу шлюз зависимостей.

    Классовые атрибуты:
        __dependency_gate: DependencyGate | None – шлюз, общий для всех экземпляров.
        _depends_info: list[DependencyInfo] | None – временное хранилище,
                         используемое декоратором @depends для передачи данных
                         в __init_subclass__.
    """

    __dependency_gate: ClassVar[DependencyGate | None] = None
    _depends_info: ClassVar[list[DependencyInfo] | None] = None

    @classmethod
    def get_dependency_gate(cls) -> DependencyGate:
        """
        Возвращает шлюз зависимостей для данного класса.

        Шлюз создаётся лениво при первом вызове, если ещё не был создан.
        После завершения __init_subclass__ шлюз замораживается.

        Возвращает:
            DependencyGate, связанный с классом.
        """
        if cls.__dependency_gate is None:
            cls.__dependency_gate = DependencyGate()
        return cls.__dependency_gate

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается при создании подкласса. Собирает зависимости из временных
        метаданных и регистрирует их в шлюзе.

        Алгоритм:
            1. Вызывает super().__init_subclass__() для поддержки множественного наследования.
            2. Сбрасывает унаследованный шлюз, чтобы дочерний класс получил свой собственный.
            3. Получает шлюз через get_dependency_gate().
            4. Если есть _depends_info (временные данные от декораторов @depends),
               регистрирует каждый DependencyInfo в шлюзе.
            5. Удаляет _depends_info, чтобы не засорять класс.
            6. Замораживает шлюз.

        Аргументы:
            **kwargs: передаются в родительский __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Сбрасываем унаследованный шлюз, чтобы дочерний класс создал свой собственный
        cls.__dependency_gate = None
        gate = cls.get_dependency_gate()

        # Собираем зависимости, накопленные декораторами
        if cls._depends_info:
            for info in cls._depends_info:
                gate.register(info)

        # Очищаем временные данные
        if hasattr(cls, "_depends_info"):
            delattr(cls, "_depends_info")

        # Замораживаем шлюз – после этого регистрация невозможна
        gate.freeze()