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
При нарушении инварианта выбрасывается ``ValueError`` с информативным
сообщением, указывающим на класс и конкретную проблему.

═══════════════════════════════════════════════════════════════════════════════
ПРОВЕРЯЕМЫЕ ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

Аспекты:
    1. Не более одного summary-аспекта на класс.
    2. Если есть regular-аспекты, должен быть ровно один summary-аспект
       (действие без summary не может вернуть результат).
    3. Summary-аспект должен быть объявлен последним среди аспектов.
    4. Классы без аспектов вообще (Plugin, утилитарный класс) — допустимы,
       правила 1–3 к ним не применяются.

Чекеры:
    5. Каждый чекер должен быть привязан к существующему аспекту
       (по ``method_name``). Чекер на методе, который не является аспектом,
       — это ошибка конфигурации (чекер никогда не будет вызван).

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

Функции этого модуля вызываются только из ``MetadataBuilder.build()``
в модуле ``builder.py``. Они не являются частью публичного API пакета.

    from action_machine.metadata.validators import validate_aspects, validate_checkers_belong_to_aspects

    validate_aspects(cls, aspects)
    validate_checkers_belong_to_aspects(cls, checkers, aspects)
"""

from __future__ import annotations

from action_machine.core.class_metadata import AspectMeta, CheckerMeta


def validate_aspects(cls: type, aspects: list[AspectMeta]) -> None:
    """
    Проверяет структурные инварианты аспектов.

    Правила:
        1. Не более одного summary-аспекта.
        2. Если есть regular-аспекты, должен быть ровно один summary-аспект
           (действие без summary не может вернуть результат).
        3. Summary-аспект должен быть объявлен последним.

    Исключение из правила 2: классы без аспектов вообще (Plugin,
    утилитарный класс) — допустимы, правила не применяются.

    Аргументы:
        cls: класс (используется только для формирования сообщений об ошибках).
        aspects: собранные аспекты из ``collect_aspects()``.

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


def validate_checkers_belong_to_aspects(
    cls: type,
    checkers: list[CheckerMeta],
    aspects: list[AspectMeta],
) -> None:
    """
    Проверяет, что каждый чекер привязан к существующему аспекту.

    Чекер декорирует метод, который также должен быть аспектом
    (помечен ``@regular_aspect`` или ``@summary_aspect``). Если метод
    с чекером не является аспектом — это ошибка конфигурации: чекер
    никогда не будет вызван машиной, и ошибку валидации пользователь
    обнаружит только по отсутствию проверки в рантайме.

    Аргументы:
        cls: класс (используется только для формирования сообщений об ошибках).
        checkers: собранные чекеры из ``collect_checkers()``.
        aspects: собранные аспекты из ``collect_aspects()``.

    Исключения:
        ValueError: если чекер привязан к методу, который не является аспектом.
            Сообщение содержит имя класса, имя класса чекера, имя поля
            и имя метода, к которому привязан чекер.
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
