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

    DEFAULT_OUTPUT_DIR = "archive/logs"
    DEFAULT_EXCLUDE = [
        "__pycache__", ".venv", "venv", ".git",
        ".pytest_cache", ".ruff_cache", ".mypy_cache", "archive",
    ]

    def __init__(
        self,
        output_file: str | None = None,
        exclude_dirs: list[str] | None = None,
    ) -> None:
        self.exclude_dirs: set[str] = (
            set(exclude_dirs) if exclude_dirs else set(self.DEFAULT_EXCLUDE)
        )
        self.output_file = output_file or self._make_output_path()

    # ------------------------------------------------------------------
    # Вспомогательные приватные методы
    # ------------------------------------------------------------------

    def _make_output_path(self) -> str:
        """Создаёт путь к выходному файлу с временны́м штампом."""
        os.makedirs(self.DEFAULT_OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.DEFAULT_OUTPUT_DIR, f"python_files_{timestamp}.txt")

    def _should_exclude_dir(self, dirpath: str, dirname: str) -> bool:
        """Возвращает True, если папку нужно пропустить при обходе."""
        if dirname in self.exclude_dirs:
            return True
        full_path = os.path.join(dirpath, dirname)
        return any(part in self.exclude_dirs for part in full_path.split(os.sep))

    def _read_file(self, filepath: str) -> str:
        """
        Читает файл сначала как UTF-8, затем как CP1251.
        При неудаче возвращает строку-комментарий с описанием ошибки.
        """
        # Попытка 1: UTF-8
        try:
            with open(filepath, encoding="utf-8") as fh:
                return fh.read()
        except UnicodeDecodeError:
            pass

        # Попытка 2: CP1251
        try:
            with open(filepath, encoding="cp1251") as fh:
                return fh.read()
        except Exception as exc:
            return f"# Ошибка чтения файла: {exc}\n"

    def _scan_python_files(self, root_dir: str) -> list[str]:
        """Рекурсивно собирает пути ко всем .py-файлам, кроме самого скрипта."""
        script_path = os.path.abspath(__file__)
        result: list[str] = []

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [
                d for d in dirnames
                if not self._should_exclude_dir(dirpath, d)
            ]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                full_path = os.path.join(dirpath, filename)
                if os.path.abspath(full_path) != script_path:
                    result.append(full_path)

        result.sort()
        return result

    def _write_header(self, out, root_dir: str, file_count: int) -> None:
        """Записывает информационный заголовок в выходной файл."""
        separator = "#" * 80
        lines = [
            separator,
            "# СБОРКА PYTHON-ФАЙЛОВ",
            f"# Дата:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Директория: {root_dir}",
            f"# Исключено:  {', '.join(sorted(self.exclude_dirs))}",
            f"# Найдено файлов: {file_count}",
            separator,
            "",
        ]
        out.write("\n".join(lines) + "\n")

    def _write_files(self, out, python_files: list[str]) -> None:
        """Записывает содержимое каждого файла с разделителями."""
        separator = "#" * 80
        last_index = len(python_files) - 1

        for i, filepath in enumerate(python_files):
            out.write(f"{separator}\n# Файл: {filepath}\n{separator}\n\n")
            out.write(self._read_file(filepath))
            if i < last_index:
                out.write("\n\n\n")

    def _print_summary(self, python_files: list[str]) -> None:
        """Выводит итоговую информацию в stdout."""
        print(f"\n✅ Готово! Найдено Python-файлов: {len(python_files)}")
        print(f"📁 Результат сохранён в: {self.output_file}")

        if not python_files:
            print("\n⚠️  Python-файлы не найдены.")
            return

        print("\n📋 Список найденных файлов (первые 10):")
        for filepath in python_files[:10]:
            print(f"  {filepath}")
        if len(python_files) > 10:
            print(f"  ... и ещё {len(python_files) - 10} файлов")

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def collect(self, root_dir: str | None = None) -> None:
        """
        Обходит root_dir и записывает содержимое всех .py-файлов
        в self.output_file.
        """
        if root_dir is None:
            root_dir = os.path.dirname(os.path.abspath(__file__))

        print(f"📁 Сканируем: {root_dir}")
        print(f"🚫 Исключаемые папки: {', '.join(sorted(self.exclude_dirs))}")
        print(f"📄 Выходной файл: {self.output_file}")

        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        try:
            python_files = self._scan_python_files(root_dir)

            with open(self.output_file, "w", encoding="utf-8") as out:
                self._write_header(out, root_dir, len(python_files))
                self._write_files(out, python_files)

            self._print_summary(python_files)

        except Exception as exc:
            raise RuntimeError(f"❌ Ошибка при сборе файлов: {exc}") from exc

    @classmethod
    def from_command_line(cls) -> None:
        """Запускает сборщик, принимая дополнительные исключения из argv."""
        exclude_dirs = cls.DEFAULT_EXCLUDE.copy()
        if len(sys.argv) > 1:
            exclude_dirs.extend(sys.argv[1:])
            print(f"➕ Добавлены исключения: {', '.join(sys.argv[1:])}")
        cls(output_file=None, exclude_dirs=exclude_dirs).collect()


if __name__ == "__main__":
    PythonFileCollector(
        output_file="archive/logs/code.txt",
        exclude_dirs=[
            "__pycache__", ".cursor", ".github", ".gitverse", ".import_linter_cache", ".venv", "venv", 
            ".git", ".ruff_cache", "archive", "scripts", "tests", "docs",
            ".pytest_cache", ".ruff_cache", ".mypy_cache", "dist", ".import_linter_cache", "docs", "htmlcov"
        ],
    ).collect()
