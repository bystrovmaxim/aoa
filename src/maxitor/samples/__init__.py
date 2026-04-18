# src/maxitor/samples/__init__.py
"""
Демонстрационные домены Maxitor: связный «псевдо-продукт» для графа ActionMachine.

Пять ограниченных контекстов (**store**, **billing**, **messaging**, **catalog**, **support**) плюс
:mod:`maxitor.samples.roles`. У каждого домена одинаковая **структурная глубина** как у
``store``: ``dependencies``, ``resources`` (два ``@connection``), ``plugins`` (after-aspect,
global finish, unhandled error), сущности ``entities``, и действие с полной поверхностью
графа (``@depends``, ``@connection``, aspects + checkers, ``@compensate``, ``@on_error``,
``@context_requires``, ``@sensitive``).

Сборка: :func:`build_sample_coordinator`.
"""

from maxitor.samples.build import _MODULES, build_sample_coordinator
from maxitor.samples.store.domain import StoreDomain

__all__ = ["_MODULES", "StoreDomain", "build_sample_coordinator"]
