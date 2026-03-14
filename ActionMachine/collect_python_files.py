# ActionMachine/collect_files.py
#!/usr/bin/env python3
"""
Скрипт для сбора файлов с указанными расширениями из директории, в которой он расположен.

Принцип работы:
- Определяет свою директорию через os.path.realpath(__file__),
  что гарантирует корректную работу независимо от текущей рабочей директории (cwd).
- Рекурсивно обходит свою директорию и все вложенные поддиректории.
- Не меняет cwd, не зависит от cwd.
- Пропускает служебные папки и файлы (настраивается через параметры).
- Собирает содержимое всех найденных файлов в один файл code.txt в той же папке.

Параметры командной строки:
    --extensions (-e):   Расширения файлов для сбора (по умолчанию: .py .ini)
    --skip-dirs (-d):    Имена директорий, которые следует пропускать
    --skip-files (-f):   Имена файлов, которые следует пропускать
    --output (-o):       Имя выходного файла (по умолчанию: code.txt)

Примеры использования:
    # Сбор .py и .ini файлов (по умолчанию):
    python collect_files.py

    # Сбор .py, .ini, .toml и .cfg файлов:
    python collect_files.py -e .py .ini .toml .cfg

    # Дополнительно пропустить папку "migrations" и файл "secrets.ini":
    python collect_files.py -d migrations -f secrets.ini

    # Всё вместе с кастомным выходным файлом:
    python collect_files.py -e .py .ini .yaml -d migrations temp -f secrets.ini -o output.txt
"""

import os
import argparse
from typing import List, Set, TextIO, Tuple

# Директории, пропускаемые по умолчанию (служебные)
DEFAULT_SKIP_DIRS: Set[str] = {
    'venv', '.venv', 'env', '.env',
    '__pycache__', '.git', '.pytest_cache',
    'node_modules', '.mypy_cache', '.tox',
    'dist', 'build',
}

# Файлы, пропускаемые по умолчанию
DEFAULT_SKIP_FILES: Set[str] = set()

# Расширения, собираемые по умолчанию
DEFAULT_EXTENSIONS: Tuple[str, ...] = ('.py', '.ini')


def parse_args() -> argparse.Namespace:
    """
    Разбирает аргументы командной строки.

    Возвращает:
        argparse.Namespace с полями: extensions, skip_dirs, skip_files, output.
    """
    parser = argparse.ArgumentParser(
        description='Сбор файлов с указанными расширениями в один текстовый файл.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Примеры:\n'
            '  python collect_files.py\n'
            '  python collect_files.py -e .py .ini .toml .cfg\n'
            '  python collect_files.py -d migrations temp -f secrets.ini\n'
            '  python collect_files.py -e .py .yaml -o output.txt'
        ),
    )

    parser.add_argument(
        '-e', '--extensions',
        nargs='+',
        default=list(DEFAULT_EXTENSIONS),
        help=(
            'Расширения файлов для сбора (с точкой). '
            f'По умолчанию: {" ".join(DEFAULT_EXTENSIONS)}'
        ),
    )

    parser.add_argument(
        '-d', '--skip-dirs',
        nargs='+',
        default=[],
        help=(
            'Дополнительные имена директорий для пропуска '
            '(добавляются к стандартному набору: venv, __pycache__, .git и т.д.).'
        ),
    )

    parser.add_argument(
        '-f', '--skip-files',
        nargs='+',
        default=[],
        help='Имена файлов, которые следует пропускать (например: secrets.ini setup.py).',
    )

    parser.add_argument(
        '-o', '--output',
        default='code.txt',
        help='Имя выходного файла (по умолчанию: code.txt).',
    )

    return parser.parse_args()


def normalize_extensions(extensions: List[str]) -> Tuple[str, ...]:
    """
    Нормализует список расширений: гарантирует, что каждое начинается с точки.

    Аргументы:
        extensions: список расширений (например, ['.py', 'ini', '.toml']).

    Возвращает:
        Кортеж нормализованных расширений (например, ('.py', '.ini', '.toml')).
    """
    normalized = []
    for ext in extensions:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized.append(ext.lower())
    return tuple(normalized)


def get_matching_files(
    scan_dir: str,
    extensions: Tuple[str, ...],
    skip_dirs: Set[str],
    skip_files: Set[str],
) -> List[str]:
    """
    Рекурсивно обходит целевую директорию и возвращает отсортированный список
    путей ко всем файлам с указанными расширениями, исключая файлы в skip_dirs,
    файлы из skip_files и сам файл скрипта.

    Аргументы:
        scan_dir: корневая директория для обхода.
        extensions: кортеж допустимых расширений (например, ('.py', '.ini')).
        skip_dirs: множество имён папок, которые следует игнорировать.
        skip_files: множество имён файлов, которые следует игнорировать.

    Возвращает:
        Отсортированный список абсолютных путей к найденным файлам.
    """
    script_real_path = os.path.realpath(__file__)
    matched_files: List[str] = []

    for root, dirs, files in os.walk(scan_dir):
        # Исключаем нежелательные папки из обхода (in-place мутация)
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs)

        for filename in files:
            # Проверяем расширение (регистронезависимо)
            if not filename.lower().endswith(extensions):
                continue

            # Пропускаем файлы из чёрного списка
            if filename in skip_files:
                continue

            full_path = os.path.join(root, filename)

            # Пропускаем сам скрипт
            if os.path.realpath(full_path) == script_real_path:
                continue

            matched_files.append(full_path)

    matched_files.sort()
    return matched_files


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
    Записывает содержимое одного файла в выходной поток с разделителями.

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
        try:
            with open(filepath, 'r', encoding='cp1251') as f:
                content = f.read()
            out_file.write(content)
        except Exception as e:
            out_file.write(f'# Ошибка чтения файла: {e}\n')
    except Exception as e:
        out_file.write(f'# Ошибка чтения файла: {e}\n')


def collect_files() -> None:
    """
    Основная функция скрипта.

    Разбирает аргументы командной строки, определяет директорию своего расположения,
    собирает все файлы с подходящими расширениями и записывает их содержимое
    в выходной файл в той же директории.
    """
    args = parse_args()

    # Определяем реальный путь к скрипту и его папку
    script_real_path = os.path.realpath(__file__)
    scan_dir = os.path.dirname(script_real_path)

    print(f"Скрипт расположен в: {script_real_path}")
    print(f"Сканируем директорию: {scan_dir}")
    print(f"Текущая рабочая директория (не используется): {os.getcwd()}")

    # Нормализуем расширения
    extensions = normalize_extensions(args.extensions)
    print(f"Расширения для сбора: {', '.join(extensions)}")

    # Объединяем стандартные и пользовательские skip-списки
    skip_dirs: Set[str] = DEFAULT_SKIP_DIRS | set(args.skip_dirs)
    skip_files: Set[str] = DEFAULT_SKIP_FILES | set(args.skip_files)

    if args.skip_dirs:
        print(f"Дополнительно пропускаемые директории: {', '.join(args.skip_dirs)}")
    if args.skip_files:
        print(f"Пропускаемые файлы: {', '.join(args.skip_files)}")

    # Добавляем сам выходной файл в skip_files, чтобы не включить его в результат
    output_file = os.path.join(scan_dir, args.output)
    skip_files.add(args.output)

    remove_old_output(output_file)

    matched_files = get_matching_files(scan_dir, extensions, skip_dirs, skip_files)

    with open(output_file, 'w', encoding='utf-8') as out:
        for i, filepath in enumerate(matched_files):
            write_file_content(filepath, out)
            if i < len(matched_files) - 1:
                out.write('\n\n\n')

    print(f'\nГотово! Найдено файлов: {len(matched_files)}')
    print(f'Результат сохранён в: {output_file}')

    if matched_files:
        # Группируем по расширению для наглядности
        by_ext: dict[str, List[str]] = {}
        for fp in matched_files:
            _, ext = os.path.splitext(fp)
            by_ext.setdefault(ext.lower(), []).append(fp)

        print('\nНайденные файлы по типам:')
        for ext in sorted(by_ext.keys()):
            files = by_ext[ext]
            print(f'\n  {ext} ({len(files)}):')
            for fp in files:
                print(f'    {fp}')
    else:
        print('\nФайлы не найдены.')


if __name__ == '__main__':
    collect_files()