# tests/bench/__init__.py
"""
Тесты TestBench API — единой точки входа для тестирования действий ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

TestBench — immutable fluent-объект, который создаёт внутри себя коллекцию
машин (async + sync), прогоняет действие на каждой и сравнивает результаты.
Если результаты расходятся — ResultMismatchError.

Тесты разбиты по темам:

- test_bench_creation.py      — создание TestBench, хранение параметров.
- test_bench_immutability.py  — fluent-методы не мутируют оригинал.
- test_bench_run.py           — полный прогон через run().
- test_bench_run_aspect.py    — выполнение одного аспекта через run_aspect().
- test_bench_run_summary.py   — выполнение summary через run_summary().
- test_mock_action.py         — MockAction: фиксированный и вычисляемый результат.
- test_comparison.py          — сравнение результатов между машинами.
- test_state_validator.py     — валидация state перед аспектами.
- test_stubs.py               — стабы контекста (UserInfoStub и т.д.).

═══════════════════════════════════════════════════════════════════════════════
ДОМЕННАЯ МОДЕЛЬ
═══════════════════════════════════════════════════════════════════════════════

Все тесты используют Action из tests/domain/:
- PingAction      — минимальный, только summary, ROLE_NONE.
- SimpleAction    — 1 regular + summary, ROLE_NONE.
- FullAction      — 2 regular + summary, depends, connection, "manager".
- ChildAction     — для вложенных вызовов через box.run().
- AdminAction     — роль "admin".

Общие фикстуры (bench, clean_bench, manager_bench, admin_bench,
mock_payment, mock_notification, mock_db) определены в tests/conftest.py.
"""
