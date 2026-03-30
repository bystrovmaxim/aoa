# src/action_machine/metadata/validators.py
"""
Модуль: validators — функции структурной валидации собранных метаданных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит функции валидации, которые проверяют структурные инварианты
собранных метаданных. Эти инварианты невозможно проверить на уровне
отдельного декоратора — они требуют знания обо всех декораторах класса
в совокупности.

═══════════════════════════════════════════════════════════════════════════════
ПРОВЕРЯЕМЫЕ ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

Обязательность описаний полей (validate_described_fields):
    1. Если Params наследует DescribedFieldsGateHost и имеет поля —
       каждое поле обязано иметь непустой description.
    2. Если Result наследует DescribedFieldsGateHost и имеет поля —
       каждое поле обязано иметь непустой description.

Обязательность @meta (validate_meta_required):
    3. ActionMetaGateHost + аспекты → @meta обязателен.
    4. ResourceMetaGateHost → @meta обязателен.

Гейт-хосты (validate_gate_hosts):
    5. Аспекты → AspectGateHost.
    6. Чекеры → CheckerGateHost.
    7. Подписки → OnGateHost.

Аспекты (validate_aspects):
    8. Не более одного summary-аспекта.
    9. Regular без summary — ошибка.
    10. Summary последним.

Чекеры (validate_checkers_belong_to_aspects):
    11. Каждый чекер привязан к существующему аспекту.
"""

from __future__ import annotations

from typing import Any, get_args, get_origin

from pydantic import BaseModel

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.class_metadata import AspectMeta, CheckerMeta, FieldDescriptionMeta, MetaInfo
from action_machine.core.described_fields_gate_host import DescribedFieldsGateHost
from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.plugins.on_gate_host import OnGateHost

# ═════════════════════════════════════════════════════════════════════════════
# Валидация описаний полей Params и Result
#
# Если класс Params или Result наследует DescribedFieldsGateHost и содержит
# pydantic-поля — каждое поле обязано иметь непустой description в Field().
# Пустые классы (без собственных полей) не проверяются.
# ═════════════════════════════════════════════════════════════════════════════


def _extract_generic_params_result(cls: type) -> tuple[type | None, type | None]:
    """
    Извлекает generic-параметры P и R из BaseAction[P, R] в MRO класса.

    Аргументы:
        cls: класс действия.

    Возвращает:
        Кортеж (P, R). Если не найдены — (None, None).
    """
    from action_machine.core.base_action import BaseAction  # pylint: disable=import-outside-toplevel

    for klass in cls.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is BaseAction:
                args = get_args(base)
                if len(args) >= 2:
                    p_type = args[0] if isinstance(args[0], type) else None
                    r_type = args[1] if isinstance(args[1], type) else None
                    return p_type, r_type
    return None, None


def _validate_pydantic_model_descriptions(model_cls: type) -> list[str]:
    """
    Проверяет, что все поля pydantic-модели имеют непустой description.

    Аргументы:
        model_cls: pydantic-класс для проверки.

    Возвращает:
        Список имён полей без описания. Пустой список если всё OK.
    """
    if not isinstance(model_cls, type) or not issubclass(model_cls, BaseModel):
        return []

    missing: list[str] = []
    for field_name, field_info in model_cls.model_fields.items():
        description = field_info.description
        if not description or not description.strip():
            missing.append(field_name)

    return missing


def validate_described_fields(
    cls: type,
    params_fields: list[FieldDescriptionMeta],
    result_fields: list[FieldDescriptionMeta],
) -> None:
    """
    Проверяет обязательность описаний полей Params и Result.

    Извлекает generic-параметры P и R из BaseAction[P, R]. Для каждого
    проверяет: если класс наследует DescribedFieldsGateHost и содержит
    pydantic-поля — каждое поле обязано иметь непустой description.

    Пустые классы (BaseParams, BaseResult без собственных полей,
    MockParams и т.д.) не проверяются.

    Аргументы:
        cls: класс действия для анализа.
        params_fields: собранные описания полей Params.
        result_fields: собранные описания полей Result.

    Исключения:
        TypeError: если хотя бы одно поле не имеет описания.
    """
    p_type, r_type = _extract_generic_params_result(cls)

    # Проверка Params
    if (
        p_type is not None
        and issubclass(p_type, DescribedFieldsGateHost)
        and params_fields
    ):
        missing = _validate_pydantic_model_descriptions(p_type)
        if missing:
            fields_str = ", ".join(f"'{f}'" for f in missing)
            raise TypeError(
                f"Поля {fields_str} в {p_type.__name__} не имеют описания. "
                f'Используйте Field(description="...") для каждого поля.'
            )

    # Проверка Result
    if (
        r_type is not None
        and issubclass(r_type, DescribedFieldsGateHost)
        and result_fields
    ):
        missing = _validate_pydantic_model_descriptions(r_type)
        if missing:
            fields_str = ", ".join(f"'{f}'" for f in missing)
            raise TypeError(
                f"Поля {fields_str} в {r_type.__name__} не имеют описания. "
                f'Используйте Field(description="...") для каждого поля.'
            )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация обязательности @meta
# ═════════════════════════════════════════════════════════════════════════════


def validate_meta_required(
    cls: type,
    meta: MetaInfo | None,
    aspects: list[AspectMeta],
) -> None:
    """
    Проверяет обязательность декоратора @meta для классов с гейт-хостами.

    Правила:
        1. ActionMetaGateHost + аспекты → @meta обязателен.
        2. ResourceMetaGateHost → @meta обязателен.

    Аргументы:
        cls: класс, который проверяется.
        meta: собранные метаданные @meta (или None).
        aspects: собранные аспекты.

    Исключения:
        TypeError: если класс обязан иметь @meta, но декоратор не применён.
    """
    if meta is not None:
        return

    if issubclass(cls, ActionMetaGateHost) and aspects:
        raise TypeError(
            f"Action {cls.__name__} не имеет декоратора @meta. "
            f"Каждое действие обязано иметь описание. "
            f'Добавьте @meta(description="...") перед определением класса.'
        )

    if issubclass(cls, ResourceMetaGateHost):
        raise TypeError(
            f"Ресурсный менеджер {cls.__name__} не имеет декоратора @meta. "
            f"Каждый ресурсный менеджер обязан иметь описание. "
            f'Добавьте @meta(description="...") перед определением класса.'
        )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация гейт-хостов
# ═════════════════════════════════════════════════════════════════════════════


def validate_gate_hosts(
    cls: type,
    aspects: list[AspectMeta],
    checkers: list[CheckerMeta],
    subscriptions: list[Any],
) -> None:
    """
    Проверяет, что класс наследует необходимые гейт-хосты для всех
    обнаруженных декораторов уровня метода.

    Проверки:
        - Аспекты → AspectGateHost.
        - Чекеры → CheckerGateHost.
        - Подписки → OnGateHost.

    Аргументы:
        cls: класс, который проверяется.
        aspects: собранные аспекты.
        checkers: собранные чекеры.
        subscriptions: собранные подписки.

    Исключения:
        TypeError: если класс содержит декораторы без гейт-хоста.
    """
    if aspects and not issubclass(cls, AspectGateHost):
        aspect_names = ", ".join(a.method_name for a in aspects)
        raise TypeError(
            f"Класс {cls.__name__} содержит аспекты ({aspect_names}), "
            f"но не наследует AspectGateHost. Декораторы @regular_aspect "
            f"и @summary_aspect разрешены только на классах, наследующих "
            f"AspectGateHost. Используйте BaseAction или добавьте "
            f"AspectGateHost в цепочку наследования."
        )

    if checkers and not issubclass(cls, CheckerGateHost):
        checker_fields = ", ".join(c.field_name for c in checkers)
        raise TypeError(
            f"Класс {cls.__name__} содержит чекеры для полей ({checker_fields}), "
            f"но не наследует CheckerGateHost. Декораторы чекеров "
            f"(@ResultStringChecker, @ResultIntChecker и др.) разрешены "
            f"только на классах, наследующих CheckerGateHost. "
            f"Используйте BaseAction или добавьте CheckerGateHost "
            f"в цепочку наследования."
        )

    if subscriptions and not issubclass(cls, OnGateHost):
        event_types = ", ".join(
            getattr(s, "event_type", str(s)) for s in subscriptions
        )
        raise TypeError(
            f"Класс {cls.__name__} содержит подписки на события ({event_types}), "
            f"но не наследует OnGateHost. Декоратор @on разрешён только "
            f"на классах, наследующих OnGateHost. Используйте Plugin "
            f"или добавьте OnGateHost в цепочку наследования."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация аспектов
# ═════════════════════════════════════════════════════════════════════════════


def validate_aspects(cls: type, aspects: list[AspectMeta]) -> None:
    """
    Проверяет структурные инварианты аспектов.

    Правила:
        1. Не более одного summary-аспекта.
        2. Regular без summary — ошибка.
        3. Summary последним.

    Аргументы:
        cls: класс для сообщений об ошибках.
        aspects: собранные аспекты.

    Исключения:
        ValueError: при нарушении инвариантов.
    """
    if not aspects:
        return

    summaries = [a for a in aspects if a.aspect_type == "summary"]
    regulars = [a for a in aspects if a.aspect_type == "regular"]

    if len(summaries) > 1:
        names = ", ".join(s.method_name for s in summaries)
        raise ValueError(
            f"Класс {cls.__name__} содержит {len(summaries)} summary-аспектов "
            f"({names}), допускается не более одного."
        )

    if regulars and not summaries:
        raise ValueError(
            f"Класс {cls.__name__} содержит {len(regulars)} regular-аспект(ов), "
            f"но не имеет summary-аспекта. Действие должно завершаться "
            f"summary-аспектом, возвращающим Result."
        )

    if summaries and aspects[-1].aspect_type != "summary":
        raise ValueError(
            f"Класс {cls.__name__}: summary-аспект '{summaries[0].method_name}' "
            f"должен быть объявлен последним методом среди аспектов. "
            f"Сейчас последний аспект — '{aspects[-1].method_name}' "
            f"(тип: {aspects[-1].aspect_type})."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация чекеров
# ═════════════════════════════════════════════════════════════════════════════


def validate_checkers_belong_to_aspects(
    cls: type,
    checkers: list[CheckerMeta],
    aspects: list[AspectMeta],
) -> None:
    """
    Проверяет, что каждый чекер привязан к существующему аспекту.

    Аргументы:
        cls: класс для сообщений об ошибках.
        checkers: собранные чекеры.
        aspects: собранные аспекты.

    Исключения:
        ValueError: если чекер привязан к несуществующему аспекту.
    """
    aspect_names = {a.method_name for a in aspects}

    for checker in checkers:
        if checker.method_name not in aspect_names:
            raise ValueError(
                f"Класс {cls.__name__}: чекер '{checker.checker_class.__name__}' "
                f"для поля '{checker.field_name}' привязан к методу "
                f"'{checker.method_name}', который не является аспектом. "
                f"Чекеры можно применять только к методам с @regular_aspect "
                f"или @summary_aspect."
            )
