#!/usr/bin/env python3
"""
Скрипт для сбора всех Python-файлов в проекте и сохранения их в один файл.
Сохраняет результат в archive/logs/code.txt (фиксированное имя).
"""

import os
import sys
from datetime import datetime


class PythonFileCollector:
    """
    Класс для рекурсивного обхода директории и сбора всех Python-файлов
    с возможностью исключения папок по имени.
    Все выходные файлы сохраняются в archive/logs/ с фиксированным именем.
    """

    # Значения по умолчанию
    DEFAULT_OUTPUT_DIR = "archive/logs"
    DEFAULT_EXCLUDE = ["__pycache__", ".venv", "venv", ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache", "archive"]

    def __init__(self, output_file: str | None = None, exclude_dirs: list[str] | None = None):
        """
        :param output_file: путь к файлу, куда будет записан список.
                            Если None, создаётся имя с датой и временем.
        :param exclude_dirs: список имён папок, которые нужно исключить из обхода.
        """
        self.exclude_dirs: set[str] = set(exclude_dirs) if exclude_dirs else set(self.DEFAULT_EXCLUDE)

        # Если выходной файл не указан, создаём имя с датой и временем
        if output_file is None:
            # Создаём папку если её нет
            os.makedirs(self.DEFAULT_OUTPUT_DIR, exist_ok=True)

            # Генерируем имя файла: python_files_20260317_164500.txt
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"python_files_{timestamp}.txt"
            self.output_file = os.path.join(self.DEFAULT_OUTPUT_DIR, filename)
        else:
            self.output_file = output_file

    def _should_exclude_dir(self, dirpath: str, dirname: str) -> bool:
        """
        Проверяет, нужно ли исключить папку.

        Аргументы:
            dirpath: полный путь к родительской папке
            dirname: имя папки для проверки

        Возвращает:
            True если папку нужно исключить
        """
        # Проверяем по имени
        if dirname in self.exclude_dirs:
            return True

        # Проверяем по полному пути (например, .venv/lib)
        full_path = os.path.join(dirpath, dirname)
        for exclude in self.exclude_dirs:
            if exclude in full_path.split(os.sep):
                return True

        return False

    def collect(self, root_dir: str | None = None) -> None:
        """
        Обходит директорию root_dir (по умолчанию — папка, где находится скрипт)
        и записывает содержимое всех Python-файлов в output_file.
        """
        if root_dir is None:
            root_dir = os.path.dirname(os.path.abspath(__file__))

        print(f"📁 Сканируем: {root_dir}")
        print(f"🚫 Исключаемые папки: {', '.join(sorted(self.exclude_dirs))}")
        print(f"📄 Выходной файл: {self.output_file}")

        # Создаём директорию для выходного файла, если её нет
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        python_files = []
        script_path = os.path.abspath(__file__)

        try:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                # Исключаем папки по имени и пути
                dirnames[:] = [d for d in dirnames if not self._should_exclude_dir(dirpath, d)]

                for filename in filenames:
                    if filename.endswith(".py"):
                        full_path = os.path.join(dirpath, filename)
                        # Пропускаем сам скрипт
                        if os.path.abspath(full_path) == script_path:
                            continue
                        python_files.append(full_path)

            # Сортируем для удобства
            python_files.sort()

            # Записываем результат
            with open(self.output_file, "w", encoding="utf-8") as out:
                # Заголовок с информацией
                out.write("#" * 80 + "\n")
                out.write("# СБОРКА PYTHON-ФАЙЛОВ\n")
                out.write(f"# Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                out.write(f"# Директория: {root_dir}\n")
                out.write(f"# Исключено: {', '.join(sorted(self.exclude_dirs))}\n")
                out.write(f"# Найдено файлов: {len(python_files)}\n")
                out.write("#" * 80 + "\n\n")

                # Записываем каждый файл
                for i, filepath in enumerate(python_files):
                    out.write("#" * 80 + "\n")
                    out.write(f"# Файл: {filepath}\n")
                    out.write("#" * 80 + "\n\n")

                    try:
                        with open(filepath, encoding="utf-8") as f:
                            content = f.read()
                        out.write(content)
                    except UnicodeDecodeError:
                        try:
                            with open(filepath, encoding="cp1251") as f:
                                content = f.read()
                            out.write(content)
                        except Exception as e:
                            out.write(f"# Ошибка чтения файла: {e}\n")
                    except Exception as e:
                        out.write(f"# Ошибка чтения файла: {e}\n")

                    if i < len(python_files) - 1:
                        out.write("\n\n\n")

            print(f"\n✅ Готово! Найдено Python-файлов: {len(python_files)}")
            print(f"📁 Результат сохранён в: {self.output_file}")

            if python_files:
                print("\n📋 Список найденных файлов (первые 10):")
                for filepath in python_files[:10]:
                    print(f"  {filepath}")
                if len(python_files) > 10:
                    print(f"  ... и ещё {len(python_files) - 10} файлов")
            else:
                print("\n⚠️ Python-файлы не найдены.")

        except Exception as e:
            raise RuntimeError(f"❌ Ошибка при сборе файлов: {e}") from e

    @classmethod
    def from_command_line(cls):
        """
        Запускает сборщик из командной строки.
        Можно указать дополнительные папки для исключения.
        """
        # Если есть аргументы, это дополнительные папки для исключения
        exclude_dirs = cls.DEFAULT_EXCLUDE.copy()

        if len(sys.argv) > 1:
            # Добавляем пользовательские папки к исключениям
            exclude_dirs.extend(sys.argv[1:])
            print(f"➕ Добавлены исключения: {', '.join(sys.argv[1:])}")

        # Создаём файл в archive/logs/ с датой
        collector = cls(output_file=None, exclude_dirs=exclude_dirs)
        collector.collect()


if __name__ == "__main__":
    # Вариант 1: с фиксированным именем файла (как в file_list_generator.py)
    collector = PythonFileCollector(
        output_file="archive/logs/code.txt",  # фиксированное имя
        exclude_dirs=["__pycache__", ".venv", "venv", ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache"],
    )
    collector.collect()

    # Вариант 2: через командную строку (закомментировано)
    # PythonFileCollector.from_command_line()
