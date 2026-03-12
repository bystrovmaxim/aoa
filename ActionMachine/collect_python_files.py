# ActionMachine/collect_python_files.py
#!/usr/bin/env python3
"""
Скрипт для сбора всех Python-файлов из директории, в которой он расположен.

Принцип работы:
- Определяет свою директорию через os.path.realpath(__file__),
  что гарантирует корректную работу независимо от текущей рабочей директории (cwd).
- Рекурсивно обходит свою директорию и все вложенные поддиректории.
- Не меняет cwd, не зависит от cwd.
- Пропускает служебные папки (venv, __pycache__, .git и т.д.).
- Собирает содержимое всех .py файлов в один файл code.txt в той же папке.
"""

import os
from typing import List, Set, TextIO


def get_python_files(scan_dir: str, skip_dirs: Set[str]) -> List[str]:
    """
    Рекурсивно обходит целевую директорию и возвращает отсортированный список
    путей ко всем файлам с расширением .py, исключая файлы в указанных skip_dirs
    и сам файл скрипта.

    Аргументы:
        scan_dir: корневая директория для обхода.
        skip_dirs: множество имён папок, которые следует игнорировать.

    Возвращает:
        Список абсолютных путей к Python-файлам.
    """
    script_real_path = os.path.realpath(__file__)
    python_files = []
    for root, dirs, files in os.walk(scan_dir):
        # Исключаем нежелательные папки из обхода (in-place мутация)
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for filename in files:
            if not filename.endswith('.py'):
                continue
            full_path = os.path.join(root, filename)
            # Пропускаем сам скрипт
            if os.path.realpath(full_path) == script_real_path:
                continue
            python_files.append(full_path)
    python_files.sort()
    return python_files


def remove_old_output(output_file: str) -> None:
    """
    Удаляет существующий файл output_file, если он есть.

    Аргументы:
        output_file: путь к файлу, который нужно удалить.
    """
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f'Удалён старый файл: {output_file}')


def write_file_content(filepath: str, out_file: TextIO) -> None:
    """
    Записывает содержимое одного Python-файла в выходной поток с разделителями.

    Аргументы:
        filepath: путь к исходному файлу.
        out_file: открытый файловый объект для записи.
    """
    out_file.write('#' * 80 + '\n')
    out_file.write(f'# Файл: {filepath}\n')
    out_file.write('#' * 80 + '\n\n')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        out_file.write(content)
    except UnicodeDecodeError:
        # Попытка открыть в альтернативной кодировке (например, cp1251)
        try:
            with open(filepath, 'r', encoding='cp1251') as f:
                content = f.read()
            out_file.write(content)
        except Exception as e:
            out_file.write(f'# Ошибка чтения файла: {e}\n')
    except Exception as e:
        out_file.write(f'# Ошибка чтения файла: {e}\n')


def collect_python_files() -> None:
    """
    Основная функция скрипта.
    Определяет директорию своего расположения, собирает все Python-файлы
    и записывает их содержимое в файл code.txt в той же директории.
    """
    # Определяем реальный путь к скрипту и его папку
    script_real_path = os.path.realpath(__file__)
    scan_dir = os.path.dirname(script_real_path)

    print(f"Скрипт расположен в: {script_real_path}")
    print(f"Сканируем директорию: {scan_dir}")
    print(f"Текущая рабочая директория (не используется): {os.getcwd()}")

    output_file = os.path.join(scan_dir, 'code.txt')
    skip_dirs: Set[str] = {
        'venv', '.venv', 'env', '.env',
        '__pycache__', '.git', '.pytest_cache',
        'node_modules', '.mypy_cache', '.tox',
        'dist', 'build'
    }

    remove_old_output(output_file)
    python_files = get_python_files(scan_dir, skip_dirs)

    with open(output_file, 'w', encoding='utf-8') as out:
        for i, filepath in enumerate(python_files):
            write_file_content(filepath, out)
            if i < len(python_files) - 1:
                out.write('\n\n\n')

    print(f'\nГотово! Найдено Python-файлов: {len(python_files)}')
    print(f'Результат сохранён в: {output_file}')
    if python_files:
        print('\nСписок найденных файлов:')
        for filepath in python_files:
            print(f'  {filepath}')
    else:
        print('\nPython-файлы не найдены.')


if __name__ == '__main__':
    collect_python_files()