# tests/adapters/test_route_record_edges.py
"""
Дополнительные тесты извлечения типов из BaseAction[P, R].

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Закрывает непокрытые строки в base_route_record.py:

- _resolve_forward_ref: ветка неудачного резолва (строки 205-208).
- _resolve_generic_arg: ветка с аргументом-строкой (строки 228, 233-236).
- effective_request_model / effective_response_model с явным override,
  отличающимся от извлечённого типа (строки 273, 275, 278).

Все хелперы, которые представляют заведомо нерабочие или нестандартные
Action, создаются внутри теста — они не могут быть частью рабочей
доменной модели.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

_resolve_forward_ref:
    - ForwardRef, указывающий на несуществующий класс, возвращает None.
    - ForwardRef, указывающий на не-тип, возвращает None.

_resolve_generic_arg:
    - Строковый аргумент оборачивается в ForwardRef и резолвится.
    - Строковый аргумент с несуществующим именем возвращает None.
    - Аргумент неизвестного типа (не type, не ForwardRef, не str)
      возвращает None.

effective models:
    - effective_request_model возвращает request_model, когда тот
      отличается от params_type (с маппером).
    - effective_response_model возвращает response_model, когда тот
      отличается от result_type (с маппером).
"""

from dataclasses import dataclass
from typing import ForwardRef

from pydantic import BaseModel

from action_machine.adapters.base_route_record import (
    BaseRouteRecord,
    _resolve_forward_ref,
    _resolve_generic_arg,
)
from action_machine.core.base_params import BaseParams
from tests.domain import PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Хелперы — заведомо нестандартные модели, не часть рабочей доменной модели.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _TestRecord(BaseRouteRecord):
    """Конкретный наследник для тестирования BaseRouteRecord."""
    pass


class _AltRequest(BaseModel):
    """Альтернативная модель запроса, отличающаяся от любого Params."""
    query: str = "test"


class _AltResponse(BaseModel):
    """Альтернативная модель ответа, отличающаяся от любого Result."""
    data: str = "ok"


# ═════════════════════════════════════════════════════════════════════════════
# _resolve_forward_ref — ветка неудачного резолва
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveForwardRef:
    """Покрывает fallback-ветки _resolve_forward_ref."""

    def test_nonexistent_class_returns_none(self) -> None:
        """ForwardRef с именем несуществующего класса возвращает None."""
        # Arrange — ForwardRef указывает на класс, которого нет ни в модуле,
        # ни в localns
        ref = ForwardRef("CompletelyNonexistentClassName12345")

        # Act
        result = _resolve_forward_ref(ref, PingAction)

        # Assert — резолв не удался, возвращается None
        assert result is None

    def test_non_type_ref_returns_none(self) -> None:
        """ForwardRef, резолвящийся в не-тип (например, строку), возвращает None."""
        # Arrange — ForwardRef указывает на имя, которое в globalns является
        # строкой, а не типом. __name__ — строка 'PingAction' в модуле.
        ref = ForwardRef("__name__")

        # Act
        result = _resolve_forward_ref(ref, PingAction)

        # Assert — __name__ это строка, не type → None
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# _resolve_generic_arg — все ветки
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveGenericArg:
    """Покрывает все три ветки _resolve_generic_arg."""

    def test_type_passthrough(self) -> None:
        """Конкретный тип возвращается без изменений."""
        # Arrange — аргумент уже является type
        # Act
        result = _resolve_generic_arg(BaseParams, PingAction)

        # Assert
        assert result is BaseParams

    def test_forward_ref_resolved(self) -> None:
        """ForwardRef резолвится в конкретный тип через контекст action_class."""
        # Arrange — ForwardRef на вложенный класс
        ref = ForwardRef("PingAction.Params")

        # Act
        result = _resolve_generic_arg(ref, PingAction)

        # Assert
        assert result is PingAction.Params

    def test_string_resolved(self) -> None:
        """Строковый аргумент оборачивается в ForwardRef и резолвится."""
        # Arrange — строка вместо ForwardRef
        # Act
        result = _resolve_generic_arg("PingAction.Result", PingAction)

        # Assert
        assert result is PingAction.Result

    def test_string_nonexistent_returns_none(self) -> None:
        """Строка с несуществующим именем возвращает None."""
        # Arrange
        # Act
        result = _resolve_generic_arg("NoSuchClass999", PingAction)

        # Assert
        assert result is None

    def test_unknown_type_returns_none(self) -> None:
        """Аргумент неизвестного типа (не type, не ForwardRef, не str) → None."""
        # Arrange — передаём число
        # Act
        result = _resolve_generic_arg(42, PingAction)

        # Assert
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# effective_request_model / effective_response_model с override
# ═════════════════════════════════════════════════════════════════════════════


class TestEffectiveModelOverrides:
    """Покрывает ветки effective_*_model, когда указан отличающийся тип с маппером."""

    def test_effective_request_with_different_model(self) -> None:
        """request_model отличается от params_type — effective возвращает request_model."""
        # Arrange — _AltRequest != PingAction.Params, маппер предоставлен
        record = _TestRecord(
            action_class=PingAction,
            request_model=_AltRequest,
            params_mapper=lambda r: PingAction.Params(),
        )

        # Act
        result = record.effective_request_model

        # Assert
        assert result is _AltRequest

    def test_effective_response_with_different_model(self) -> None:
        """response_model отличается от result_type — effective возвращает response_model."""
        # Arrange — _AltResponse != PingAction.Result, маппер предоставлен
        record = _TestRecord(
            action_class=PingAction,
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(data="mapped"),
        )

        # Act
        result = record.effective_response_model

        # Assert
        assert result is _AltResponse
