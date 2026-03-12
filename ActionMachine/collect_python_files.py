"""
Скрипт для сбора всех Python-файлов из директории, в которой он расположен.

Принцип работы:
- Определяет свою директорию через os.path.realpath(__file__),
  что гарантирует корректную работу независимо от текущей рабочей директории (cwd).
- Рекурсивно обходит свою директорию и все вложенные поддиректории.
- Не меняет cwd, не зависит от cwd.
- Пропускает служебные папки (venv, __pycache__, .git и т.д.).
- Собирает содержимое всех .py файлов в один code.txt.
"""

import os
from typing import List


def collect_python_files() -> None:
    # Определяем РЕАЛЬНЫЙ путь к самому скрипту (разрешаем симлинки)
    script_real_path: str = os.path.realpath(__file__)
    # Директория, в которой лежит скрипт — это корень сканирования
    scan_dir: str = os.path.dirname(script_real_path)

    print(f"Скрипт расположен в: {script_real_path}")
    print(f"Сканируем директорию: {scan_dir}")
    print(f"Текущая рабочая директория (не используется): {os.getcwd()}")

    output_file: str = os.path.join(scan_dir, "code.txt")

    # Удаляем старый code.txt если существует
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Удалён старый файл: {output_file}")

    # Папки, которые нужно пропускать
    skip_dirs: set[str] = {
        "venv", ".venv", "env", ".env",
        "__pycache__", ".git", ".pytest_cache",
        "node_modules", ".mypy_cache", ".tox",
    }

    python_files: List[str] = []

    # Обходим все папки и подпапки начиная от директории скрипта
    for root, dirs, files in os.walk(scan_dir):
        # Исключаем ненужные папки из обхода (in-place мутация)
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs)

        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            full_path: str = os.path.join(root, filename)
            # Пропускаем сам скрипт
            if os.path.realpath(full_path) == script_real_path:
                continue
            python_files.append(full_path)

    # Сортируем для детерминированного порядка
    python_files.sort()

    # Записываем содержимое всех файлов в code.txt
    with open(output_file, "w", encoding="utf-8") as out:
        for i, filepath in enumerate(python_files):
            out.write("#" * 80 + "\n")
            out.write(f"# Файл: {filepath}\n")
            out.write("#" * 80 + "\n\n")

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                out.write(content)
            except UnicodeDecodeError:
                try:
                    with open(filepath, "r", encoding="cp1251") as f:
                        content = f.read()
                    out.write(content)
                except Exception as e:
                    out.write(f"# Ошибка чтения файла: {e}\n")
            except Exception as e:
                out.write(f"# Ошибка чтения файла: {e}\n")

            if i < len(python_files) - 1:
                out.write("\n\n\n")

    print(f"\nГотово! Найдено Python-файлов: {len(python_files)}")
    print(f"Результат сохранён в: {output_file}")

    if python_files:
        print("\nСписок найденных файлов:")
        for filepath in python_files:
            print(f"  {filepath}")
    else:
        print("\nPython-файлы не найдены.")


if __name__ == "__main__":
    collect_python_files()