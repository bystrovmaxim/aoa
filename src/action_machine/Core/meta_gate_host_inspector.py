# src/action_machine/core/meta_gate_host_inspector.py
"""
Модуль: MetaGateHostInspector — инспектор графа для деклараций @meta.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Обходит классы под двумя маркерными миксинами — ``ActionMetaGateHost`` и
``ResourceMetaGateHost`` — без дубликатов в списке кандидатов. Для класса с
записанным декоратором @meta в ``_meta_info`` строит узел типа ``meta`` в
графе ``GateCoordinator`` и опциональное информационное ребро ``belongs_to``
к узлу домена, если ``domain`` — класс (тип ``BaseDomain``).

═══════════════════════════════════════════════════════════════════════════════
МАРКЕР И ИНСПЕКТОР
═══════════════════════════════════════════════════════════════════════════════

    ActionMetaGateHost / ResourceMetaGateHost
        В MRO действий и ресурсных менеджеров; дают возможность применить
        @meta. Не содержат логики обхода графа.

    MetaGateHostInspector (этот модуль)
        Наследует ``BaseGateHostInspector``. Поле ``_target_mixins`` задаёт
        два маркера; ``_subclasses_recursive`` объединяет подклассы и снимает
        дубликаты через ``seen``.

═══════════════════════════════════════════════════════════════════════════════
ДАННЫЕ НА КЛАССЕ
═══════════════════════════════════════════════════════════════════════════════

@meta записывает словарь ``cls._meta_info`` (как минимум ``description``;
опционально ``domain`` — класс домена).

═══════════════════════════════════════════════════════════════════════════════
УЗЕЛ ГРАФА И РЁБРА
═══════════════════════════════════════════════════════════════════════════════

    node_type : ``meta``
    node_name : полное имя класса (``module.QualName``)
    node_meta : ``description``, ``domain`` (как в ``_meta_info``)
    edges     : пусто или одно ребро ``belongs_to`` → узел ``domain``, если
                ``domain`` не ``None`` и является ``type``

Ключ узла в координаторе: ``"meta:"`` + ``node_name``.

═══════════════════════════════════════════════════════════════════════════════
СНИМОК (Snapshot)
═══════════════════════════════════════════════════════════════════════════════

Вложенный класс ``MetaGateHostInspector.Snapshot`` наследует
``BaseFacetSnapshot``: типизированное представление фасета; method
``to_facet_payload()`` — единственная проекция в ``FacetPayload`` для графа.
Координатор кеширует снимок при ``build()`` (фаза 1), если реализован
``facet_snapshot_for_class``.

═══════════════════════════════════════════════════════════════════════════════
ПОТОК inspect()
═══════════════════════════════════════════════════════════════════════════════

1. Проверка ``_has_meta_info_invariant`` (есть ``_meta_info``).
2. При отсутствии → ``None``.
3. Иначе ``_build_payload`` → ``Snapshot.from_target`` → ``to_facet_payload``.

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Args @meta проверяются декоратором при импорте. Глобальные инварианты
графа — в ``GateCoordinator.build()`` (фазы 2–3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload


class MetaGateHostInspector(BaseGateHostInspector):
    """
    Инспектор: декларации @meta → узел ``meta`` и опциональное ребро к домену.

    Атрибуты класса:
        _target_mixins : tuple[type, ...]
            ``ActionMetaGateHost``, ``ResourceMetaGateHost`` — источники обхода.
    """

    _target_mixins: tuple[type, ...] = (ActionMetaGateHost, ResourceMetaGateHost)

    # ═══════════════════════════════════════════════════════════════════
    # Снимок фасета (вложенный класс)
    # ═══════════════════════════════════════════════════════════════════

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """
        Типизированный фасет ``meta``: поля из ``_meta_info``.

        Поля:
            class_ref   : класс-владелец (действие или менеджер).
            description : описание из @meta (или ``None``).
            domain      : класс домена или ``None``.

        ``to_facet_payload()`` добавляет ребро ``belongs_to``, только если
        ``domain`` не ``None`` и является ``type``.
        """

        class_ref: type
        description: Any
        domain: Any

        def to_facet_payload(self) -> FacetPayload:
            """
            Собирает ``FacetPayload`` узла ``meta`` и рёбра к домену.

            Returns:
                Готовый пейлоад для фазы commit координатора.
            """
            edges: tuple[Any, ...] = ()
            if self.domain is not None and isinstance(self.domain, type):
                edges = (
                    MetaGateHostInspector._make_edge(
                        target_node_type="domain",
                        target_cls=self.domain,
                        edge_type="belongs_to",
                        is_structural=False,
                    ),
                )
            return FacetPayload(
                node_type="meta",
                node_name=MetaGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=MetaGateHostInspector._make_meta(
                    description=self.description,
                    domain=self.domain,
                ),
                edges=edges,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> MetaGateHostInspector.Snapshot:
            """
            Строит снимок из ``target_cls._meta_info``.

            Args:
                target_cls: класс с уже записанным ``_meta_info``.

            Returns:
                Экземпляр ``Snapshot``.
            """
            meta_info = getattr(target_cls, "_meta_info", None)
            if not isinstance(meta_info, dict):
                raise TypeError(
                    f"{target_cls.__name__} does not contain valid _meta_info.",
                )
            return cls(
                class_ref=target_cls,
                description=meta_info.get("description"),
                domain=meta_info.get("domain"),
            )

    # ═══════════════════════════════════════════════════════════════════
    # Обход подклассов (два маркера, без дубликатов)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """
        Объединяет подклассы всех маркеров из ``_target_mixins`` без повторов.

        Returns:
            Список классов в порядке обхода; каждый класс не более одного раза.
        """
        result: list[type] = []
        seen: set[type] = set()
        for mixin in cls._target_mixins:
            for sub in cls._collect_subclasses(mixin):
                if sub in seen:
                    continue
                seen.add(sub)
                result.append(sub)
        return result

    # ═══════════════════════════════════════════════════════════════════
    # Инварианты
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def _has_meta_info_invariant(cls, target_cls: type) -> bool:
        """True, если на классе задан ``_meta_info`` (после @meta)."""
        return getattr(target_cls, "_meta_info", None) is not None

    @classmethod
    def _has_domain_invariant(cls, target_cls: type) -> bool:
        """
        True, если в ``_meta_info`` присутствует ключ ``domain`` со значением
        не ``None`` (тип значения здесь не проверяется).
        """
        meta_info = getattr(target_cls, "_meta_info", None)
        if not isinstance(meta_info, dict):
            return False
        return meta_info.get("domain") is not None

    # ═══════════════════════════════════════════════════════════════════
    # Контракт BaseGateHostInspector
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """
        Если у класса есть @meta, возвращает пейлоад узла ``meta``; иначе ``None``.

        Args:
            target_cls: кандидат из обхода маркеров.

        Returns:
            ``FacetPayload`` или ``None``.
        """
        if not cls._has_meta_info_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> MetaGateHostInspector.Snapshot | None:
        """
        Returns снимок для кеша координатора или ``None``, если @meta нет.

        Args:
            target_cls: класс с возможным ``_meta_info``.

        Returns:
            ``Snapshot`` либо ``None``.
        """
        if not cls._has_meta_info_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """
        Строит пейлоад только через ``Snapshot`` (согласованность с графом).

        Args:
            target_cls: класс с ``_meta_info`` (вызывать после ``inspect``).

        Returns:
            ``FacetPayload`` узла ``meta``.
        """
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
