#!/usr/bin/env python3
"""
Генератор списка файлов.
Обходит директорию, в которой находится скрипт (или указанную), исключая заданные папки,
и записывает в выходной файл полные пути всех файлов.
Все выходные файлы сохраняются в папку archive/logs/ с датой и временем.
"""

import os
import sys
from datetime import datetime


class FileListGenerator:
    """
    Класс для рекурсивного обхода директории и генерации списка всех файлов
    с возможностью исключения папок по имени.
    Все выходные файлы автоматически сохраняются в archive/logs/.
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

            # Генерируем имя файла: project_structure_20260317_164500.txt
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"project_structure_{timestamp}.txt"
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

    def generate(self, root_dir: str | None = None) -> None:
        """
        Обходит директорию root_dir (по умолчанию — папка, где находится скрипт)
        и записывает полные пути всех найденных файлов в output_file.
        """
        if root_dir is None:
            root_dir = os.path.dirname(os.path.abspath(__file__))

        print(f"📁 Сканируем: {root_dir}")
        print(f"🚫 Исключаемые папки: {', '.join(sorted(self.exclude_dirs))}")
        print(f"📄 Выходной файл: {self.output_file}")

        # Создаём директорию для выходного файла, если её нет
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        all_files = []

        try:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                # Исключаем папки по имени и пути
                dirnames[:] = [d for d in dirnames if not self._should_exclude_dir(dirpath, d)]

                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    all_files.append(full_path)

            # Записываем результат
            with open(self.output_file, "w", encoding="utf-8") as f:
                # Записываем заголовок с информацией
                f.write("# Структура проекта\n")
                f.write(f"# Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Корень: {root_dir}\n")
                f.write(f"# Исключено: {', '.join(sorted(self.exclude_dirs))}\n")
                f.write(f"# Найдено файлов: {len(all_files)}\n")
                f.write("#" * 80 + "\n\n")

                for full_path in sorted(all_files):
                    f.write(full_path + "\n")

            print(f"✅ Список файлов сохранён в {self.output_file}")
            print(f"📊 Найдено файлов: {len(all_files)}")

        except Exception as e:
            raise RuntimeError(f"❌ Ошибка при генерации списка файлов: {e}") from e

    @classmethod
    def from_command_line(cls):
        """
        Запускает генератор из командной строки.
        Все файлы автоматически сохраняются в archive/logs/ с датой и временем.
        Можно указать дополнительные папки для исключения.
        """
        # Если есть аргументы, это дополнительные папки для исключения
        exclude_dirs = cls.DEFAULT_EXCLUDE.copy()

        if len(sys.argv) > 1:
            # Добавляем пользовательские папки к исключениям
            exclude_dirs.extend(sys.argv[1:])
            print(f"➕ Добавлены исключения: {', '.join(sys.argv[1:])}")

        # Всегда создаём файл с датой в archive/logs/
        generator = cls(output_file=None, exclude_dirs=exclude_dirs)
        generator.generate()


if __name__ == "__main__":
    # Создаём экземпляр напрямую с ФИКСИРОВАННЫМ именем файла
    generator = FileListGenerator(
        output_file="archive/logs/project_structure.txt",  # фиксированное имя
        exclude_dirs=["__pycache__", ".venv", "venv", ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache"],
    )
    generator.generate()
