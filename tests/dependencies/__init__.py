# tests/dependencies/__init__.py
"""
Тесты подсистемы внедрения зависимостей ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Покрывает два компонента подсистемы зависимостей:

1. DependencyFactory — stateless-фабрика для создания экземпляров
   зависимостей, объявленных через декоратор @depends. Фабрика
   поддерживает создание через конструктор по умолчанию и через
   пользовательские factory-функции, проверку rollup-поддержки
   для BaseResourceManager, и оба формата входных данных
   (DependencyInfo и legacy dict).

2. DependencyGateHost — маркерный generic-миксин, разрешающий
   использование декоратора @depends. Параметр T определяет
   bound — базовый тип, которому должны соответствовать все
   зависимости. Функция _extract_bound извлекает bound из
   generic-параметра DependencyGateHost[T] в __init_subclass__.

═══════════════════════════════════════════════════════════════════════════════
ТЕСТОВЫЕ МОДУЛИ
═══════════════════════════════════════════════════════════════════════════════

- test_dependency_factory.py    — resolve() с конструктором и с factory,
                                  передача *args/**kwargs, undeclared
                                  dependency → ValueError, rollup-проверка
                                  для BaseResourceManager, has(),
                                  get_all_classes(), legacy dict формат,
                                  DependencyInfo иммутабельность.

- test_dependency_gate_host.py  — _extract_bound для DependencyGateHost[object],
                                  DependencyGateHost[конкретный_тип],
                                  наследование bound от родителя,
                                  класс без DependencyGateHost → object,
                                  get_depends_bound(), интеграция
                                  с BaseAction (PingAction, FullAction).

═══════════════════════════════════════════════════════════════════════════════
ДОМЕННАЯ МОДЕЛЬ
═══════════════════════════════════════════════════════════════════════════════

Рабочие Action (PingAction, FullAction) импортируются из tests/domain/.
Заведомо тестовые классы (_SimpleService, _FakeResourceManager,
_AnyDepsHost, _ResourceOnlyHost) создаются внутри тестовых файлов,
потому что они не являются частью рабочей доменной модели.
"""
