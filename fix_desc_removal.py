#!/usr/bin/env python3
"""
fix_desc_removal_pass2.py — второй проход: исправляет тесты,
которые напрямую создают RoleMeta, CheckerMeta и используют desc в хелперах.

Запуск: python fix_desc_removal_pass2.py
"""

import os
import re

FILES_TO_FIX = {
    "tests/decorators/test_check_roles_checks.py": [
        # Убираем тесты на desc, которые больше не нужны — заменяем на проверку отсутствия desc
        # Но проще: загрузим файл и применим точечные замены
    ],
    "tests/metadata/test_metadata_and_coordinator.py": [],
    "tests/metadata/test_validators.py": [],
}


def fix_check_roles_tests(filepath: str) -> bool:
    """Исправляет тесты декоратора @CheckRoles."""
    if not os.path.exists(filepath):
        print(f"  Файл не найден: {filepath}")
        return False

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. Тест test_single_role_string проверяет cls._role_info["desc"] — убираем эту строку
    content = re.sub(
        r'(\s*)assert\s+cls\._role_info\["desc"\]\s*==\s*"[^"]*"\n',
        '',
        content,
    )
    # Аналогично для одинарных кавычек
    content = re.sub(
        r"(\s*)assert\s+cls\._role_info\['desc'\]\s*==\s*'[^']*'\n",
        '',
        content,
    )
    # Вариант с .get("desc")
    content = re.sub(
        r'(\s*)assert\s+cls\._role_info\.get\("desc"\)\s*==\s*"[^"]*"\n',
        '',
        content,
    )

    # 2. Тест test_default_desc — проверяет desc="" по умолчанию
    #    Заменяем тело теста на проверку отсутствия ключа desc
    content = re.sub(
        r'(def test_default_desc\(self\):.*?\n)'
        r'(\s+)(.+_role_info\["desc"\].+)\n',
        r'\1\2assert "desc" not in cls._role_info\n',
        content,
        flags=re.DOTALL,
    )

    # 3. Весь класс TestCheckRolesDescErrors — удаляем целиком
    #    Тесты проверяли TypeError для desc не-строка, что больше не актуально
    content = re.sub(
        r'\nclass TestCheckRolesDescErrors.*?(?=\nclass |\Z)',
        '\n',
        content,
        flags=re.DOTALL,
    )

    # 4. Убираем desc= из любых оставшихся вызовов _make_class_with_role
    content = re.sub(r',\s*desc\s*=\s*"[^"]*"', '', content)
    content = re.sub(r",\s*desc\s*=\s*'[^']*'", '', content)

    # 5. Если _make_class_with_role принимает второй позиционный аргумент desc — убираем
    #    def _make_class_with_role(spec, desc=""):  →  def _make_class_with_role(spec):
    content = re.sub(
        r'(def _make_class_with_role\s*\(\s*spec)\s*,\s*desc\s*=\s*"[^"]*"\s*\)',
        r'\1)',
        content,
    )
    content = re.sub(
        r"(def _make_class_with_role\s*\(\s*spec)\s*,\s*desc\s*=\s*'[^']*'\s*\)",
        r'\1)',
        content,
    )

    # 6. Внутри _make_class_with_role: @CheckRoles(spec, desc=desc) → @CheckRoles(spec)
    content = re.sub(
        r'@CheckRoles\(spec,\s*desc\s*=\s*desc\)',
        '@CheckRoles(spec)',
        content,
    )

    # 7. Вызовы _make_class_with_role("admin", "описание") → _make_class_with_role("admin")
    content = re.sub(
        r'(_make_class_with_role\(\s*"[^"]*")\s*,\s*"[^"]*"\s*\)',
        r'\1)',
        content,
    )
    content = re.sub(
        r"(_make_class_with_role\(\s*'[^']*')\s*,\s*'[^']*'\s*\)",
        r'\1)',
        content,
    )

    # 8. Убираем NameError: name 'desc' — переменная desc больше не используется
    content = re.sub(r'\s*desc\s*=\s*"[^"]*"\n', '\n', content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def fix_metadata_tests(filepath: str) -> bool:
    """Исправляет тесты метаданных и координатора."""
    if not os.path.exists(filepath):
        print(f"  Файл не найден: {filepath}")
        return False

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. RoleMeta(spec=..., description=...) → RoleMeta(spec=...)
    content = re.sub(
        r'(RoleMeta\s*\([^)]*?spec\s*=\s*[^,)]+)\s*,\s*description\s*=\s*"[^"]*"',
        r'\1',
        content,
    )
    content = re.sub(
        r"(RoleMeta\s*\([^)]*?spec\s*=\s*[^,)]+)\s*,\s*description\s*=\s*'[^']*'",
        r'\1',
        content,
    )

    # 2. CheckerMeta с description — убираем параметр description
    #    CheckerMeta(method_name=..., checker_class=..., field_name=..., description=..., required=..., extra_params=...)
    #    → CheckerMeta(method_name=..., checker_class=..., field_name=..., required=..., extra_params=...)
    content = re.sub(
        r',\s*description\s*=\s*"[^"]*"',
        '',
        content,
    )
    content = re.sub(
        r",\s*description\s*=\s*'[^']*'",
        '',
        content,
    )

    # 3. Позиционные аргументы CheckerMeta — если 7 аргументов, надо убрать 4-й (description)
    #    CheckerMeta("method", SomeChecker, "field", "desc", True, {})
    #    → CheckerMeta("method", SomeChecker, "field", True, {})
    # Это сложнее с regex, но попробуем для типичного паттерна:
    content = re.sub(
        r'(CheckerMeta\(\s*"[^"]*"\s*,\s*\w+\s*,\s*"[^"]*")\s*,\s*"[^"]*"(\s*,)',
        r'\1\2',
        content,
    )

    # 4. _make_class_with_role с двумя аргументами → с одним
    content = re.sub(
        r'(def _make_class_with_role\s*\(\s*spec)\s*,\s*desc\s*=\s*"[^"]*"\s*\)',
        r'\1)',
        content,
    )
    content = re.sub(
        r'@CheckRoles\(spec,\s*desc\s*=\s*desc\)',
        '@CheckRoles(spec)',
        content,
    )
    content = re.sub(
        r'(_make_class_with_role\(\s*"[^"]*")\s*,\s*"[^"]*"\s*\)',
        r'\1)',
        content,
    )
    content = re.sub(
        r'(_make_class_with_role\(\s*CheckRoles\.\w+)\s*,\s*"[^"]*"\s*\)',
        r'\1)',
        content,
    )

    # 5. Убираем присваивания desc = "..."
    content = re.sub(r'(\s+)desc\s*=\s*"[^"]*"\n', r'\1\n', content)

    # 6. metadata.role.description → удаляем строки с этим обращением
    content = re.sub(r'\s*assert\s+metadata\.role\.description\s*==\s*"[^"]*"\n', '\n', content)
    content = re.sub(r"\s*assert\s+metadata\.role\.description\s*==\s*'[^']*'\n", '\n', content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def fix_validators_tests(filepath: str) -> bool:
    """Исправляет тесты валидаторов метаданных."""
    if not os.path.exists(filepath):
        print(f"  Файл не найден: {filepath}")
        return False

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content

    # CheckerMeta(..., description="...", ...) → убираем description
    content = re.sub(
        r',\s*description\s*=\s*"[^"]*"',
        '',
        content,
    )
    content = re.sub(
        r",\s*description\s*=\s*'[^']*'",
        '',
        content,
    )

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main() -> None:
    print("=" * 60)
    print("Второй проход: исправление тестов")
    print("=" * 60)

    changed = []

    f1 = "tests/decorators/test_check_roles_checks.py"
    if fix_check_roles_tests(f1):
        changed.append(f1)

    f2 = "tests/metadata/test_metadata_and_coordinator.py"
    if fix_metadata_tests(f2):
        changed.append(f2)

    f3 = "tests/metadata/test_validators.py"
    if fix_validators_tests(f3):
        changed.append(f3)

    print(f"\nИзменено файлов: {len(changed)}")
    for f in changed:
        print(f"  ✓ {f}")

    print("\n" + "=" * 60)
    print("Готово. Запустите тесты: pytest")
    print("=" * 60)


if __name__ == "__main__":
    main()
