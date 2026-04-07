# src/action_machine/domain/lifecycle.py
"""
Lifecycle — декларативный конечный автомат жизненного цикла сущности.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два уровня API:

1. Lifecycle — шаблон конечного автомата (граф состояний и переходов).
   Определяется через fluent-цепочку при определении класса (import-time).
   Координатор проверяет 8 правил целостности при старте приложения.

2. Специализированный класс состояния (наследник Lifecycle) — хранит
   конкретное текущее состояние экземпляра сущности. Используется как
   обычное pydantic-поле сущности.

═══════════════════════════════════════════════════════════════════════════════
СПЕЦИАЛИЗИРОВАННЫЙ КЛАСС СОСТОЯНИЯ
═══════════════════════════════════════════════════════════════════════════════

Для каждого конечного автомата создаётся класс-наследник Lifecycle
с конкретным графом состояний в атрибуте _template:

    class OrderLifecycle(Lifecycle):
        _template = (
            Lifecycle()
            .state("new", "Новый").to("confirmed", "cancelled").initial()
            .state("confirmed", "Подтверждён").to("shipped").intermediate()
            .state("shipped", "Отправлен").to("delivered").intermediate()
            .state("delivered", "Доставлен").final()
            .state("cancelled", "Отменён").final()
        )

    class PaymentLifecycle(Lifecycle):
        _template = (
            Lifecycle()
            .state("pending", "Ожидает").to("paid", "failed").initial()
            .state("paid", "Оплачен").final()
            .state("failed", "Ошибка").to("pending").intermediate()
        )

_template создаётся при определении класса (import-time). GateCoordinator
при старте находит все поля-наследники Lifecycle в model_fields сущности,
читает _template и проверяет 8 правил целостности. Приложение не
запустится при нарушении любого правила.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В СУЩНОСТИ
═══════════════════════════════════════════════════════════════════════════════

Lifecycle-поле — обычное pydantic-поле. Может быть любое количество
полей с разными типами автоматов, или ни одного. Имя поля — любое.

    @entity(description="Заказ клиента", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        id: str = Field(description="ID заказа")
        amount: float = Field(description="Сумма", ge=0)
        lifecycle: OrderLifecycle | None = Field(
            description="Жизненный цикл заказа",
        )
        payment: PaymentLifecycle | None = Field(
            description="Статус оплаты",
        )

Поле без default — обязательное при полном создании. При partial()
незагруженное поле → FieldNotLoadedError.

═══════════════════════════════════════════════════════════════════════════════
ЧТЕНИЕ ТЕКУЩЕГО СОСТОЯНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Полная загрузка из БД:
    order = OrderEntity(
        id="ORD-001",
        amount=1500.0,
        lifecycle=OrderLifecycle("new"),
        payment=PaymentLifecycle("pending"),
    )

    order.lifecycle.current_state       # → "new"
    order.payment.current_state         # → "pending"

    # Проверка допустимости перехода:
    order.lifecycle.can_transition("confirmed")  # → True
    order.lifecycle.can_transition("delivered")  # → False

    # Доступные переходы из текущего состояния:
    order.lifecycle.available_transitions  # → {"confirmed", "cancelled"}

    # Текущее состояние — начальное? финальное?
    order.lifecycle.is_initial  # → True
    order.lifecycle.is_final    # → False

    # Частичная загрузка без lifecycle:
    order = OrderEntity.partial(id="ORD-001", amount=1500.0)
    order.lifecycle  # → FieldNotLoadedError

═══════════════════════════════════════════════════════════════════════════════
ПЕРЕХОД СОСТОЯНИЯ (FROZEN-СУЩНОСТЬ)
═══════════════════════════════════════════════════════════════════════════════

Сущность frozen после создания. Переход состояния = новый экземпляр:

    # transition() возвращает НОВЫЙ OrderLifecycle:
    new_lifecycle = order.lifecycle.transition("confirmed")

    # Новый экземпляр сущности:
    confirmed_order = order.model_copy(update={"lifecycle": new_lifecycle})
    confirmed_order.lifecycle.current_state  # → "confirmed"

    # Старый не изменился:
    order.lifecycle.current_state  # → "new"

    # Недопустимый переход → InvalidTransitionError:
    order.lifecycle.transition("delivered")
    # → InvalidTransitionError

═══════════════════════════════════════════════════════════════════════════════
КЛАССИФИКАЦИЯ СОСТОЯНИЙ (StateType)
═══════════════════════════════════════════════════════════════════════════════

    INITIAL       — входная точка. Сущность создаётся в этом состоянии.
    INTERMEDIATE  — промежуточное. Обязано иметь хотя бы один переход.
    FINAL         — конечное. НЕ должно иметь переходов.

StateType — enum, исключающий невалидные комбинации на уровне типа.

═══════════════════════════════════════════════════════════════════════════════
ПРОВЕРКИ ЦЕЛОСТНОСТИ (КООРДИНАТОР ПРИ СТАРТЕ)
═══════════════════════════════════════════════════════════════════════════════

1. Каждое состояние завершено флагом (.initial()/.intermediate()/.final()).
2. Есть хотя бы одно начальное состояние.
3. Есть хотя бы одно финальное состояние.
4. Финальные состояния не имеют переходов.
5. Все цели переходов существуют.
6. Каждое не-финальное состояние имеет хотя бы один переход.
7. Из каждого начального достижимо хотя бы одно финальное.
8. Каждое не-initial состояние является целью хотя бы одного перехода.

═══════════════════════════════════════════════════════════════════════════════
FLUENT API ДЛЯ ПОСТРОЕНИЯ ШАБЛОНА
═══════════════════════════════════════════════════════════════════════════════

    Lifecycle()
        .state(key, display_name)       → _StateBuilder
            .to(*target_keys)           → _StateBuilder
            .initial()                  → Lifecycle
            .intermediate()             → Lifecycle
            .final()                    → Lifecycle

Порядок объявления состояний НЕ ВАЖЕН. Forward-ссылки в .to() разрешены.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════════
# ИСКЛЮЧЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════════


class InvalidStateError(ValueError):
    """
    Неизвестное состояние при создании экземпляра Lifecycle.

    Выбрасывается когда current_state не входит в множество
    объявленных состояний _template.

    Атрибуты:
        state_key:       переданный ключ состояния.
        lifecycle_class: имя класса Lifecycle.
        valid_states:    множество допустимых ключей.
    """

    def __init__(
        self,
        state_key: str,
        lifecycle_class: str,
        valid_states: set[str],
    ) -> None:
        self.state_key = state_key
        self.lifecycle_class = lifecycle_class
        self.valid_states = valid_states
        sorted_states = ", ".join(sorted(valid_states))
        super().__init__(
            f"Состояние '{state_key}' не объявлено в {lifecycle_class}. "
            f"Допустимые состояния: {sorted_states}."
        )


class InvalidTransitionError(ValueError):
    """
    Недопустимый переход между состояниями.

    Выбрасывается при вызове transition() когда переход
    из current_state в target_state не разрешён графом.

    Атрибуты:
        current_state:   текущее состояние.
        target_state:    целевое состояние.
        lifecycle_class: имя класса Lifecycle.
        valid_targets:   множество допустимых целей.
    """

    def __init__(
        self,
        current_state: str,
        target_state: str,
        lifecycle_class: str,
        valid_targets: set[str],
    ) -> None:
        self.current_state = current_state
        self.target_state = target_state
        self.lifecycle_class = lifecycle_class
        self.valid_targets = valid_targets
        sorted_targets = ", ".join(sorted(valid_targets)) if valid_targets else "(нет переходов)"
        super().__init__(
            f"Переход '{current_state}' → '{target_state}' недопустим "
            f"в {lifecycle_class}. "
            f"Допустимые переходы из '{current_state}': {sorted_targets}."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# КЛАССИФИКАЦИЯ СОСТОЯНИЙ
# ═══════════════════════════════════════════════════════════════════════════════


class StateType(Enum):
    """
    Тип состояния в конечном автомате.

    Три взаимоисключающих варианта — невалидная комбинация невозможна.

    Значения:
        INITIAL      — входная точка жизненного цикла.
        INTERMEDIATE — промежуточное состояние.
        FINAL        — конечное состояние.
    """

    INITIAL = "initial"
    INTERMEDIATE = "intermediate"
    FINAL = "final"


# ═══════════════════════════════════════════════════════════════════════════════
# МЕТАДАННЫЕ СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class StateInfo:
    """
    Полные метаданные одного состояния в Lifecycle.

    Frozen dataclass. Содержит всю информацию о состоянии в одном месте.

    Атрибуты:
        key          : уникальный строковый ключ ("new", "confirmed").
        display_name : человекочитаемое имя ("Новый заказ", "Подтверждён").
        state_type   : классификация: INITIAL, INTERMEDIATE или FINAL.
        transitions  : множество ключей допустимых целевых состояний.
    """

    key: str
    display_name: str
    state_type: StateType
    transitions: frozenset[str]

    @property
    def is_initial(self) -> bool:
        """True если состояние начальное."""
        return self.state_type == StateType.INITIAL

    @property
    def is_final(self) -> bool:
        """True если состояние финальное."""
        return self.state_type == StateType.FINAL

    @property
    def is_intermediate(self) -> bool:
        """True если состояние промежуточное."""
        return self.state_type == StateType.INTERMEDIATE


# ═══════════════════════════════════════════════════════════════════════════════
# BUILDER ОДНОГО СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════════════════════


class _StateBuilder:
    """
    Builder для одного состояния в fluent-цепочке Lifecycle.

    Создаётся Lifecycle.state(). Не для прямого использования.

    Атрибуты:
        _lifecycle    : родительский Lifecycle.
        _key          : ключ состояния.
        _display_name : отображаемое имя.
        _transitions  : накопленные ключи целей переходов.
        _completed    : True после .initial()/.intermediate()/.final().
    """

    def __init__(self, lifecycle: Lifecycle, key: str, display_name: str) -> None:
        self._lifecycle = lifecycle
        self._key = key
        self._display_name = display_name
        self._transitions: set[str] = set()
        self._completed = False

    def to(self, *target_keys: str) -> _StateBuilder:
        """
        Задаёт допустимые переходы из текущего состояния.

        Forward-ссылки разрешены. Может вызываться несколько раз.

        Аргументы:
            *target_keys: ключи целевых состояний.

        Возвращает:
            self — для продолжения fluent-цепочки.

        Исключения:
            TypeError:  target_key — не строка.
            ValueError: target_key — пустая строка.
        """
        for key in target_keys:
            if not isinstance(key, str):
                raise TypeError(
                    f"Ключ перехода должен быть строкой, "
                    f"получен {type(key).__name__}: {key!r}."
                )
            if not key.strip():
                raise ValueError(
                    f"Ключ перехода не может быть пустой строкой "
                    f"в состоянии '{self._key}'."
                )
            self._transitions.add(key)
        return self

    def initial(self) -> Lifecycle:
        """Помечает состояние как начальное (INITIAL)."""
        return self._finalize(StateType.INITIAL)

    def intermediate(self) -> Lifecycle:
        """Помечает состояние как промежуточное (INTERMEDIATE)."""
        return self._finalize(StateType.INTERMEDIATE)

    def final(self) -> Lifecycle:
        """
        Помечает состояние как финальное (FINAL).

        Исключения:
            ValueError: если у финального состояния есть переходы.
        """
        if self._transitions:
            raise ValueError(
                f"Финальное состояние '{self._key}' не может иметь переходов, "
                f"но указаны: {sorted(self._transitions)}"
            )
        return self._finalize(StateType.FINAL)

    def _finalize(self, state_type: StateType) -> Lifecycle:
        """
        Завершает объявление состояния и регистрирует в Lifecycle.

        Исключения:
            RuntimeError: если состояние уже завершено.
        """
        if self._completed:
            raise RuntimeError(
                f"Состояние '{self._key}' уже завершено. "
                f"Нельзя вызывать .initial()/.intermediate()/.final() повторно."
            )
        self._completed = True
        state_info = StateInfo(
            key=self._key,
            display_name=self._display_name,
            state_type=state_type,
            transitions=frozenset(self._transitions),
        )
        self._lifecycle._register_state(state_info)
        return self._lifecycle

    @property
    def is_completed(self) -> bool:
        """True если состояние завершено."""
        return self._completed


# ═══════════════════════════════════════════════════════════════════════════════
# LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════


class Lifecycle:
    """
    Конечный автомат жизненного цикла сущности.

    Два режима использования:

    1. ШАБЛОН — создаётся через fluent-цепочку, содержит граф состояний.
       Используется в _template специализированных классов.
       GateCoordinator проверяет 8 правил целостности при старте.

    2. ЭКЗЕМПЛЯР — создаётся с current_state, хранит текущее состояние
       конкретного бизнес-объекта. Является обычным pydantic-полем
       сущности. Frozen — переход = новый экземпляр.

    Специализированный класс определяет _template и наследует Lifecycle:

        class OrderLifecycle(Lifecycle):
            _template = (
                Lifecycle()
                .state("new", "Новый").to("confirmed", "cancelled").initial()
                .state("confirmed", "Подтверждён").final()
            )

    Экземпляр создаётся с текущим состоянием:

        lc = OrderLifecycle("new")
        lc.current_state              # → "new"
        lc.can_transition("confirmed") # → True
        new_lc = lc.transition("confirmed")  # → новый OrderLifecycle

    Атрибуты:
        _states        : dict[str, StateInfo] — граф состояний (для шаблона).
        _current_state : str | None — текущее состояние (для экземпляра).
        _current_builder : _StateBuilder | None — текущий незавершённый builder.
    """

    _template: Lifecycle | None = None

    def __init__(self, current_state: str | None = None) -> None:
        """
        Создаёт Lifecycle.

        Без аргументов — пустой шаблон для fluent-цепочки.
        С current_state — экземпляр с конкретным текущим состоянием.

        Аргументы:
            current_state: текущее состояние экземпляра. None для шаблона.

        Исключения:
            InvalidStateError: если current_state не входит в _template.
        """
        self._states: dict[str, StateInfo] = {}
        self._current_state: str | None = None
        self._current_builder: _StateBuilder | None = None

        if current_state is not None:
            template = self._get_template()
            if template is None:
                raise TypeError(
                    f"{self.__class__.__name__} не имеет _template. "
                    f"Определите _template в классе или используйте "
                    f"fluent-цепочку .state().to().initial() для шаблона."
                )
            valid_states = set(template._states.keys())
            if current_state not in valid_states:
                raise InvalidStateError(
                    state_key=current_state,
                    lifecycle_class=self.__class__.__name__,
                    valid_states=valid_states,
                )
            self._states = dict(template._states)
            self._current_state = current_state

    @classmethod
    def _get_template(cls) -> Lifecycle | None:
        """
        Возвращает _template класса.

        Обходит MRO для поиска _template в наследниках.

        Возвращает:
            Lifecycle с графом состояний или None.
        """
        for klass in cls.__mro__:
            template = klass.__dict__.get("_template")
            if template is not None and isinstance(template, Lifecycle):
                return template
        return None

    # ─────────────────────────────────────────────────────────────────────
    # FLUENT API (для построения шаблона)
    # ─────────────────────────────────────────────────────────────────────

    def state(self, key: str, display_name: str) -> _StateBuilder:
        """
        Объявляет новое состояние в шаблоне.

        Аргументы:
            key:          уникальный строковый ключ.
            display_name: человекочитаемое имя для UI и диаграмм.

        Возвращает:
            _StateBuilder для настройки переходов и классификации.

        Исключения:
            TypeError:    key или display_name — не строка.
            ValueError:   key или display_name — пустая строка.
            ValueError:   состояние с таким key уже объявлено.
            RuntimeError: предыдущее состояние не завершено.
        """
        if self._current_builder is not None and not self._current_builder.is_completed:
            raise RuntimeError(
                f"Состояние '{self._current_builder._key}' не завершено. "
                f"Вызовите .initial(), .intermediate() или .final() "
                f"перед объявлением нового состояния '{key}'."
            )

        if not isinstance(key, str):
            raise TypeError(
                f"Ключ состояния должен быть строкой, "
                f"получен {type(key).__name__}: {key!r}."
            )
        if not key.strip():
            raise ValueError("Ключ состояния не может быть пустой строкой.")

        if not isinstance(display_name, str):
            raise TypeError(
                f"Отображаемое имя состояния должно быть строкой, "
                f"получен {type(display_name).__name__}: {display_name!r}."
            )
        if not display_name.strip():
            raise ValueError(
                f"Отображаемое имя состояния '{key}' не может быть пустой строкой."
            )

        if key in self._states:
            raise ValueError(
                f"Состояние '{key}' уже объявлено."
            )

        builder = _StateBuilder(self, key, display_name)
        self._current_builder = builder
        return builder

    def _register_state(self, state_info: StateInfo) -> None:
        """
        Регистрирует завершённое состояние.

        Вызывается из _StateBuilder._finalize(). Не для прямого использования.
        """
        self._states[state_info.key] = state_info

    # ─────────────────────────────────────────────────────────────────────
    # API ЭКЗЕМПЛЯРА (текущее состояние)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def current_state(self) -> str:
        """
        Текущее состояние экземпляра.

        Исключения:
            RuntimeError: если Lifecycle — шаблон (нет current_state).
        """
        if self._current_state is None:
            raise RuntimeError(
                f"{self.__class__.__name__} — шаблон, не экземпляр. "
                f"Текущее состояние доступно только у экземпляров: "
                f"{self.__class__.__name__}('state_key')."
            )
        return self._current_state

    @property
    def current_state_info(self) -> StateInfo:
        """
        Полные метаданные текущего состояния.

        Возвращает:
            StateInfo текущего состояния.
        """
        return self._states[self.current_state]

    @property
    def available_transitions(self) -> set[str]:
        """
        Множество допустимых целевых состояний из текущего.

        Возвращает:
            set[str] — ключи состояний, в которые можно перейти.
        """
        return set(self.current_state_info.transitions)

    @property
    def is_initial(self) -> bool:
        """True если текущее состояние — начальное."""
        return self.current_state_info.is_initial

    @property
    def is_final(self) -> bool:
        """True если текущее состояние — финальное."""
        return self.current_state_info.is_final

    def can_transition(self, target: str) -> bool:
        """
        Проверяет допустимость перехода.

        Аргументы:
            target: ключ целевого состояния.

        Возвращает:
            True если переход из current_state в target разрешён.
        """
        return target in self.current_state_info.transitions

    def transition(self, target: str) -> Lifecycle:
        """
        Создаёт НОВЫЙ экземпляр Lifecycle с новым current_state.

        Не мутирует текущий объект — сущность frozen, поэтому
        переход состояния = новый экземпляр через model_copy():

            new_lc = order.lifecycle.transition("confirmed")
            confirmed_order = order.model_copy(update={"lifecycle": new_lc})

        Аргументы:
            target: ключ целевого состояния.

        Возвращает:
            Новый экземпляр того же класса с current_state=target.

        Исключения:
            InvalidTransitionError: если переход недопустим.
        """
        if not self.can_transition(target):
            raise InvalidTransitionError(
                current_state=self.current_state,
                target_state=target,
                lifecycle_class=self.__class__.__name__,
                valid_targets=self.available_transitions,
            )
        return self.__class__(target)

    # ─────────────────────────────────────────────────────────────────────
    # API ШАБЛОНА (для координатора)
    # ─────────────────────────────────────────────────────────────────────

    def get_states(self) -> dict[str, StateInfo]:
        """
        Все состояния автомата.

        Возвращает:
            dict[str, StateInfo] — копия словаря {ключ: метаданные}.
        """
        return dict(self._states)

    def get_initial_keys(self) -> set[str]:
        """Ключи всех начальных состояний."""
        return {
            key for key, info in self._states.items()
            if info.state_type == StateType.INITIAL
        }

    def get_final_keys(self) -> set[str]:
        """Ключи всех финальных состояний."""
        return {
            key for key, info in self._states.items()
            if info.state_type == StateType.FINAL
        }

    def get_transitions(self) -> dict[str, set[str]]:
        """
        Граф переходов автомата.

        Возвращает:
            dict[str, set[str]] — {ключ_источника: {ключи_целей}}.
        """
        return {
            key: set(info.transitions)
            for key, info in self._states.items()
        }

    def has_state(self, key: str) -> bool:
        """Проверяет существование состояния."""
        return key in self._states

    def __repr__(self) -> str:
        if self._current_state is not None:
            return (
                f"{self.__class__.__name__}('{self._current_state}')"
            )
        return (
            f"Lifecycle(states={len(self._states)}, "
            f"initial={len(self.get_initial_keys())}, "
            f"final={len(self.get_final_keys())})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Lifecycle):
            return NotImplemented
        return (
            type(self) is type(other)
            and self._current_state == other._current_state
        )

    def __hash__(self) -> int:
        return hash((type(self), self._current_state))
