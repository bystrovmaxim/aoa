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

Валидаторы вызываются из ``MetadataBuilder.build()`` после завершения
сбора данных коллекторами и перед созданием ``ClassMetadata``.
При нарушении инварианта выбрасывается ``ValueError`` или ``TypeError``
с информативным сообщением.

═══════════════════════════════════════════════════════════════════════════════
СИСТЕМА ГЕЙТ-ХОСТОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый декоратор грамматики намерений ActionMachine требует, чтобы
целевой класс наследовал соответствующий маркерный миксин (гейт-хост).
Гейт-хост — это РАЗРЕШЕНИЕ на использование декоратора. Без гейта
декоратор применён туда, куда нельзя, и это ошибка конфигурации.

Полная таблица соответствий:

    Декоратор              Гейт-хост              Кто проверяет
    ─────────────────────  ─────────────────────── ──────────────────
    @CheckRoles            RoleGateHost            Декоратор (класс)
    @depends               DependencyGateHost      Декоратор (класс)
    @connection            ConnectionGateHost      Декоратор (класс)
    @regular_aspect        AspectGateHost          MetadataBuilder
    @summary_aspect        AspectGateHost          MetadataBuilder
    @on                    OnGateHost              MetadataBuilder
    Чекеры                 CheckerGateHost         MetadataBuilder
    @sensitive             (без ограничений)       —

Декораторы уровня класса (@CheckRoles, @depends, @connection)
проверяют issubclass самостоятельно в момент применения — они
получают cls как аргумент и класс уже создан.

Декораторы уровня метода (@regular_aspect, @summary_aspect, @on,
чекеры) НЕ МОГУТ проверить issubclass самостоятельно — в момент
их применения класс ещё не существует (Python сначала обрабатывает
тело класса, декорирует методы, и только потом создаёт объект класса).
Поэтому проверка гейтов для декораторов методов выполняется здесь.

Результат одинаковый: без гейта — TypeError до первого run().

═══════════════════════════════════════════════════════════════════════════════
ПРОВЕРЯЕМЫЕ ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

Гейт-хосты (validate_gate_hosts):
    1. Аспекты → класс ОБЯЗАН наследовать AspectGateHost.
    2. Чекеры → класс ОБЯЗАН наследовать CheckerGateHost.
    3. Подписки → класс ОБЯЗАН наследовать OnGateHost.
    4. @sensitive — без ограничений (допустим на любом классе).

Аспекты (validate_aspects):
    5. Не более одного summary-аспекта на класс.
    6. Если есть regular-аспекты, должен быть ровно один summary.
    7. Summary должен быть объявлен последним.
    8. Классы без аспектов (Plugin, утилитарный класс) — допустимы.

Чекеры (validate_checkers_belong_to_aspects):
    9. Каждый чекер привязан к существующему аспекту (по method_name).

═══════════════════════════════════════════════════════════════════════════════
НЕ ТРОГАТЬ
═══════════════════════════════════════════════════════════════════════════════

Проверки гейт-хостов гарантируют, что декораторы грамматики намерений
применены только к классам, предназначенным для этого. Удаление проверок
приведёт к тому, что декораторы можно будет навесить на произвольный
класс без ошибки, а проблема обнаружится только в рантайме.
"""

from __future__ import annotations

from typing import Any

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.class_metadata import AspectMeta, CheckerMeta
from action_machine.plugins.on_gate_host import OnGateHost

# ═════════════════════════════════════════════════════════════════════════════
# Валидация гейт-хостов
#
# НЕ УДАЛЯТЬ И НЕ МОДИФИЦИРОВАТЬ БЕЗ ПОНИМАНИЯ ПОСЛЕДСТВИЙ.
#
# Каждый декоратор грамматики намерений требует гейт-хоста.
# Декораторы уровня класса проверяют гейт сами при применении.
# Декораторы уровня метода не могут — класс ещё не создан.
# Эта функция закрывает дыру для декораторов уровня метода.
# Результат одинаковый: без гейта — TypeError до первого run().
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

    Гейт-хост — маркерный миксин, РАЗРЕШАЮЩИЙ применение декоратора.
    Без гейта декоратор применён к классу, не предназначенному для этого.

    Эта функция дополняет проверки декораторов уровня класса
    (@CheckRoles, @depends, @connection), которые проверяют гейты
    самостоятельно. Декораторы уровня метода (@regular_aspect,
    @summary_aspect, @on, чекеры) не могут проверить гейт в момент
    применения, потому что класс ещё не существует.

    Проверки:
        - Аспекты (@regular_aspect, @summary_aspect) → AspectGateHost.
        - Чекеры (@ResultStringChecker и др.) → CheckerGateHost.
        - Подписки (@on) → OnGateHost.
        - @sensitive — не проверяется (допустим на любом классе).

    Аргументы:
        cls: класс, который проверяется.
        aspects: собранные аспекты из collect_aspects().
        checkers: собранные чекеры из collect_checkers().
        subscriptions: собранные подписки из collect_subscriptions().

    Исключения:
        TypeError: если класс содержит декораторы, но не наследует
                   соответствующий гейт-хост. Сообщение содержит имя
                   класса, найденные декораторы и требуемый гейт-хост.
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
        2. Если есть regular-аспекты, должен быть ровно один summary-аспект
           (действие без summary не может вернуть результат).
        3. Summary-аспект должен быть объявлен последним.

    Классы без аспектов (Plugin, утилитарный класс) — допустимы,
    правила не применяются.

    Аргументы:
        cls: класс (для формирования сообщений об ошибках).
        aspects: собранные аспекты из collect_aspects().

    Исключения:
        ValueError:
            - Больше одного summary-аспекта.
            - Есть regular-аспекты, но нет summary.
            - Summary-аспект не является последним в списке.
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

    Чекер декорирует метод, который также должен быть аспектом
    (помечен @regular_aspect или @summary_aspect). Если метод
    с чекером не является аспектом — это ошибка конфигурации:
    чекер никогда не будет вызван машиной.

    Аргументы:
        cls: класс (для формирования сообщений об ошибках).
        checkers: собранные чекеры из collect_checkers().
        aspects: собранные аспекты из collect_aspects().

    Исключения:
        ValueError: если чекер привязан к методу, который не является
                    аспектом.
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
