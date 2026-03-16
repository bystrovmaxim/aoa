#!/usr/bin/env python3
"""
Генератор списка файлов.
Обходит директорию, в которой находится скрипт (или указанную), исключая заданные папки,
и записывает в выходной файл полные пути всех файлов.
Если аргументы командной строки не заданы, используются значения по умолчанию.
"""

import os
import sys
from typing import List, Optional, Set


class FileListGenerator:
    """
    Класс для рекурсивного обхода директории и генерации списка всех файлов
    с возможностью исключения папок по имени.
    """

    # Значения по умолчанию
    DEFAULT_OUTPUT = "all_files.txt"
    DEFAULT_EXCLUDE = [".git", "venv", "__pycache__", "z"]

    def __init__(self, output_file: str, exclude_dirs: Optional[List[str]] = None):
        """
        :param output_file: путь к файлу, куда будет записан список.
        :param exclude_dirs: список имён папок, которые нужно исключить из обхода.
        """
        self.output_file = output_file
        self.exclude_dirs: Set[str] = set(exclude_dirs) if exclude_dirs else set()

    def generate(self, root_dir: Optional[str] = None) -> None:
        """
        Обходит директорию root_dir (по умолчанию — папка, где находится скрипт)
        и записывает полные пути всех найденных файлов в output_file.
        """
        if root_dir is None:
            root_dir = os.path.dirname(os.path.abspath(__file__))

        print(f"Сканируем: {root_dir}")
        print(f"Исключаемые папки: {', '.join(sorted(self.exclude_dirs))}")
        print(f"Выходной файл: {self.output_file}")

        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for dirpath, dirnames, filenames in os.walk(root_dir):
                    # Исключаем папки по имени
                    dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]

                    for filename in filenames:
                        full_path = os.path.join(dirpath, filename)
                        f.write(full_path + '\n')
            print(f"Список файлов сохранён в {self.output_file}")
            print(f"Найдено файлов: {self._count_files(root_dir)}")
        except Exception as e:
            raise RuntimeError(f"Ошибка при генерации списка файлов: {e}") from e

    def _count_files(self, root_dir: str) -> int:
        """Подсчитывает количество файлов (без учёта исключённых папок) — для информации."""
        count = 0
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
            count += len(filenames)
        return count

    @classmethod
    def from_command_line(cls):
        """
        Запускает генератор из командной строки с поддержкой значений по умолчанию.
        Если аргументы не указаны, используются DEFAULT_OUTPUT и DEFAULT_EXCLUDE.
        """
        # Если аргументов нет или только один (имя скрипта), используем значения по умолчанию
        if len(sys.argv) == 1:
            output_file = cls.DEFAULT_OUTPUT
            exclude_dirs = cls.DEFAULT_EXCLUDE
            print("Аргументы не заданы, используются значения по умолчанию.")
        else:
            # Минимум один аргумент (выходной файл) должен быть
            output_file = sys.argv[1]
            exclude_dirs = sys.argv[2:] if len(sys.argv) > 2 else []

        generator = cls(output_file, exclude_dirs)
        generator.generate()


if __name__ == "__main__":
    FileListGenerator.from_command_line()