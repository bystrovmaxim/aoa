# src/action_machine/auth/role_gate_host_inspector.py
"""
RoleGateHostInspector — инспектор гейтхоста ролей для построения графа.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RoleGateHostInspector обходит всех наследников маркерного миксина
RoleGateHost, обнаруживает классы с декоратором @check_roles и собирает
из них FacetPayload для графа координатора.

═══════════════════════════════════════════════════════════════════════════════
ДВА КЛАССА — ДВЕ ОТВЕТСТВЕННОСТИ
═══════════════════════════════════════════════════════════════════════════════

    RoleGateHost (маркерный миксин, auth/role_gate_host.py)
        Живёт в MRO класса BaseAction. Разрешает применение декоратора
        @check_roles через issubclass-проверку. Не содержит логики
        инспекции. Не наследует BaseGateHostInspector. Не меняется.

    RoleGateHostInspector (инспектор, этот файл)
        Наследует BaseGateHostInspector. Реализует inspect() и
        _build_payload(). Обходит наследников RoleGateHost через
        _target_mixin. Регистрируется в координаторе.

Связь между ними — поле _target_mixin. Инспектор знает, наследников
какого маркера обходить. Маркер не знает про инспектор.

═══════════════════════════════════════════════════════════════════════════════
ДАННЫЕ, СОБИРАЕМЫЕ ИНСПЕКТОРОМ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @check_roles при применении записывает на класс атрибут:

    cls._role_info = {"spec": "admin"}           # одна роль
    cls._role_info = {"spec": ["user", "mgr"]}   # список ролей
    cls._role_info = {"spec": "__NONE__"}         # ROLE_NONE
    cls._role_info = {"spec": "__ANY__"}          # ROLE_ANY

Инспектор читает _role_info и формирует узел графа типа "role"
с метаданными spec.

═══════════════════════════════════════════════════════════════════════════════
УЗЕЛ В ГРАФЕ
═══════════════════════════════════════════════════════════════════════════════

    node_type : "role"
    node_name : "module.CreateOrderAction" (полное имя класса)
    node_meta : (("spec", "admin"),)
    edges     : () — ролевой узел не имеет исходящих рёбер

Ключ в графе координатора: "role:module.CreateOrderAction".

═══════════════════════════════════════════════════════════════════════════════
ЛОГИКА inspect()
═══════════════════════════════════════════════════════════════════════════════

    1. getattr(target_cls, "_role_info", None)
    2. Если None → return None (класс без @check_roles, пропускаем)
    3. Если не None → _build_payload() → return payload

Инспектор НЕ выбрасывает TypeError при отсутствии _role_info. Класс
может наследовать RoleGateHost через BaseAction, но не иметь @check_roles.
Это допустимо — машина (ActionProductMachine) проверит наличие ролей
при выполнении и выбросит TypeError если роли обязательны.

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Валидация разделена между двумя уровнями:

    Декоратор @check_roles (import-time):
        Проверяет аргументы при определении класса — spec является
        строкой или списком строк, пустой список запрещён, элементы
        списка — строки. Ошибки обнаруживаются немедленно при импорте.

    Координатор GateCoordinator.build() (build-time):
        Глобальные структурные проверки — уникальность ключей узлов,
        ссылочная целостность рёбер, ацикличность структурных рёбер.

Логика проверки не размазывается. Декоратор отвечает за свои аргументы,
координатор — за целостность графа.

═══════════════════════════════════════════════════════════════════════════════
ОБХОД НАСЛЕДНИКОВ
═══════════════════════════════════════════════════════════════════════════════

_subclasses_recursive() переопределён: обходит наследников _target_mixin
(RoleGateHost) через хелпер _collect_subclasses() базового класса,
а не наследников самого RoleGateHostInspector.

Координатор вызывает RoleGateHostInspector._subclasses_recursive()
и получает [BaseAction, CreateOrderAction, UpdateOrderAction, ...].
Затем для каждого вызывает inspect(). BaseAction без @check_roles →
None (пропущен). CreateOrderAction с @check_roles → FacetPayload.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР
═══════════════════════════════════════════════════════════════════════════════

    @check_roles("admin")
    class AdminAction(BaseAction[AdminParams, AdminResult]):
        ...

    # Координатор при build():
    # RoleGateHostInspector.inspect(AdminAction)
    # → FacetPayload(
    #       node_type="role",
    #       node_name="myapp.actions.AdminAction",
    #       node_class=AdminAction,
    #       node_meta=(("spec", "admin"),),
    #       edges=(),
    #   )

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    # RoleGateHostInspector.inspect(PingAction)
    # → FacetPayload(
    #       node_type="role",
    #       node_name="myapp.actions.PingAction",
    #       node_class=PingAction,
    #       node_meta=(("spec", "__NONE__"),),
    #       edges=(),
    #   )

    class BaseAction(ABC, RoleGateHost, ...):
        ...

    # RoleGateHostInspector.inspect(BaseAction)
    # → None (нет _role_info)
"""

from __future__ import annotations

from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload


class RoleGateHostInspector(BaseGateHostInspector):
    """
    Инспектор гейтхоста ролей.

    Обходит наследников RoleGateHost, обнаруживает классы с декоратором
    @check_roles и собирает FacetPayload с ролевой спецификацией
    для графа координатора.

    Узел в графе: тип "role", без исходящих рёбер.
    Метаданные узла: spec (строка, список строк, ROLE_NONE, ROLE_ANY).

    Атрибуты класса:
        _target_mixin : type
            Маркерный миксин, наследников которого обходит инспектор.
            RoleGateHost — миксин, разрешающий @check_roles.
    """

    _target_mixin: type = RoleGateHost

    # ═══════════════════════════════════════════════════════════════════
    # Обход наследников маркерного миксина
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """
        Возвращает всех наследников RoleGateHost.

        Переопределяет метод BaseGateHostInspector, чтобы обходить
        наследников маркерного миксина (_target_mixin), а не
        наследников самого RoleGateHostInspector.

        Использует хелпер _collect_subclasses() из базового класса
        BaseGateHostInspector.

        Координатор вызывает этот метод при build() и получает
        список классов для инспекции: [BaseAction, CreateOrderAction, ...].
        Классы без @check_roles будут отфильтрованы в inspect() → None.

        Возвращает:
            list[type] — все наследники RoleGateHost.
        """
        return cls._collect_subclasses(cls._target_mixin)

    # ═══════════════════════════════════════════════════════════════════
    # Контракт BaseGateHostInspector
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """
        Проверяет наличие @check_roles и собирает данные.

        Читает атрибут _role_info, записанный декоратором @check_roles.
        Если атрибут отсутствует — класс не имеет ролевых ограничений,
        возвращает None. Если присутствует — собирает payload.

        Аргументы:
            target_cls: класс для инспекции (наследник RoleGateHost).

        Возвращает:
            FacetPayload — класс имеет @check_roles, данные собраны.
            None — класс не имеет @check_roles (нет _role_info).
        """
        role_info = getattr(target_cls, "_role_info", None)
        if role_info is None:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """
        Собирает FacetPayload из _role_info класса.

        Формирует узел типа "role" с метаданными spec. Рёбра
        отсутствуют — ролевой узел не ссылается на другие узлы.

        Аргументы:
            target_cls: класс с атрибутом _role_info.

        Возвращает:
            FacetPayload с node_type="role" и spec в node_meta.
        """
        return FacetPayload(
            node_type="role",
            node_name=cls._make_node_name(target_cls),
            node_class=target_cls,
            node_meta=cls._make_meta(
                spec=target_cls._role_info["spec"],
            ),
            edges=(),
        )
