# tests/decorators/__init__.py
"""
Тесты декораторов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Покрывает все декораторы уровня класса и уровня метода:

Декораторы уровня класса:
- @meta(description, domain) — описание и доменная принадлежность.
  Записывает _meta_info в класс. Обязателен для Action с аспектами
  и для ResourceManager.
- @depends(cls, factory, description) — объявление зависимости.
  Записывает DependencyInfo в cls._depends_info.
- @connection(cls, key, description) — объявление подключения
  к внешнему ресурсу. Записывает ConnectionInfo в cls._connection_info.

Декораторы уровня метода:
- @regular_aspect(description) — шаг конвейера бизнес-логики.
  Записывает _new_aspect_meta с type="regular" в метод.
- @summary_aspect(description) — завершающий шаг конвейера.
  Записывает _new_aspect_meta с type="summary" в метод.
- @sensitive(enabled, max_chars, char, max_percent) — маскирование
  чувствительных данных в логах. Записывает _sensitive_config
  в getter свойства.

Декоратор @check_roles покрыт в tests/auth/test_check_roles_decorator.py.

Каждый тестовый файл проверяет:
1. Корректную запись метаданных при валидных аргументах.
2. TypeError/ValueError при невалидных аргументах.
3. TypeError при применении к невалидной цели.
4. Интеграцию с MetadataBuilder и ClassMetadata.
"""
