#!/usr/bin/env python3
# collect_python_files.py
"""
Collect source files under a directory tree into one text archive.

- **Scan root**: directory that contains this script (copy/move the script → scan base moves).
- **Output**: always under ``~/PythonDev/aoa/archive/logs`` regardless of where this file
  lives or what the current working directory is. Relative ``output_file`` paths join that
  directory only.

Writes to ``~/PythonDev/aoa/archive/logs/code.txt`` by default when run as ``__main__``.
"""
import os
import sys
from datetime import datetime
from pathlib import Path


def _script_parent_dir() -> str:
    """
    Absolute path to the directory containing this ``.py`` file.

    Uses ``os.path.abspath(__file__)`` without resolving symlinks so a symlinked script
    keeps its apparent folder as the scan root.
    """
    return os.path.dirname(os.path.abspath(__file__))


def _fixed_archive_logs_dir() -> str:
    """
    Fixed output directory: ``~/PythonDev/aoa/archive/logs``.

    Same path no matter where ``collect_python_files.py`` is copied; independent of cwd.
    """
    return str(Path.home() / "PythonDev" / "aoa" / "archive" / "logs")


def _normalize_extensions(exts: list[str]) -> frozenset[str]:
    """Return lowercase suffixes including a leading dot (e.g. ``.py``)."""
    out: set[str] = set()
    for raw in exts:
        e = raw.strip().lower()
        if not e.startswith("."):
            e = "." + e
        out.add(e)
    return frozenset(out)


class PythonFileCollector:
    """
    Walk from this script's folder; write outputs under ``~/PythonDev/aoa/archive/logs``.
    """

    DEFAULT_EXCLUDE = [
        "__pycache__",
        ".venv",
        "venv",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "archive",
    ]
    DEFAULT_EXTENSIONS = [".py", ".html", ".ts"]

    def __init__(
        self,
        output_file: str | None = None,
        exclude_dirs: list[str] | None = None,
        extensions: list[str] | None = None,
    ) -> None:
        self.exclude_dirs: set[str] = set(exclude_dirs) if exclude_dirs else set(self.DEFAULT_EXCLUDE)
        self.extensions: frozenset[str] = _normalize_extensions(
            extensions if extensions is not None else list(self.DEFAULT_EXTENSIONS),
        )
        self._output_logs_dir = _fixed_archive_logs_dir()
        self.output_file = output_file or self._make_output_path()
        if self.output_file and not os.path.isabs(self.output_file):
            self.output_file = os.path.join(self._output_logs_dir, self.output_file)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _make_output_path(self) -> str:
        """Timestamped file under the fixed ``~/PythonDev/aoa/archive/logs`` directory."""
        base = self._output_logs_dir
        os.makedirs(base, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(base, f"python_files_{timestamp}.txt")

    def _should_exclude_dir(self, dirpath: str, dirname: str) -> bool:
        """Return True if this directory must be skipped."""
        if dirname in self.exclude_dirs:
            return True
        full_path = os.path.join(dirpath, dirname)
        return any(part in self.exclude_dirs for part in full_path.split(os.sep))

    def _read_file(self, filepath: str) -> str:
        """Read text; try UTF-8 then CP1251; on failure return an error comment."""
        try:
            with open(filepath, encoding="utf-8") as fh:
                return fh.read()
        except UnicodeDecodeError:
            pass

        try:
            with open(filepath, encoding="cp1251") as fh:
                return fh.read()
        except Exception as exc:
            return f"# Read error: {exc}\n"

    def _matches_extension(self, filename: str) -> bool:
        """True if file suffix is one of the configured extensions."""
        suffix = Path(filename).suffix.lower()
        return suffix in self.extensions

    def _scan_source_files(self, root_dir: str) -> list[str]:
        """Collect paths under root_dir whose suffix matches (excluding this script if under root)."""
        script_path = os.path.abspath(__file__)
        result: list[str] = []

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not self._should_exclude_dir(dirpath, d)]
            for filename in filenames:
                if not self._matches_extension(filename):
                    continue
                full_path = os.path.join(dirpath, filename)
                if os.path.abspath(full_path) != script_path:
                    result.append(full_path)

        result.sort()
        return result

    def _write_header(self, out, root_dir: str, file_count: int) -> None:
        """Write metadata header to the output file."""
        separator = "#" * 80
        ext_list = ", ".join(sorted(self.extensions))
        lines = [
            separator,
            "# SOURCE FILE COLLECTION",
            f"# Date:           {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Scan root:      {root_dir}",
            f"# Output logs dir: {self._output_logs_dir}",
            f"# Output file:    {self.output_file}",
            f"# Extensions:     {ext_list}",
            f"# Excluded:       {', '.join(sorted(self.exclude_dirs))}",
            f"# File count:     {file_count}",
            separator,
            "",
        ]
        out.write("\n".join(lines) + "\n")

    def _write_files(self, out, paths: list[str]) -> None:
        """Write each file body with separators."""
        separator = "#" * 80
        last_index = len(paths) - 1

        for i, filepath in enumerate(paths):
            out.write(f"{separator}\n# File: {filepath}\n{separator}\n\n")
            out.write(self._read_file(filepath))
            if i < last_index:
                out.write("\n\n\n")

    def _print_summary(self, paths: list[str]) -> None:
        """Print stdout summary."""
        ext_list = ", ".join(sorted(self.extensions))
        print(f"\n✅ Done. Collected {len(paths)} file(s) [{ext_list}]")
        print(f"📁 Output: {self.output_file}")

        if not paths:
            print("\n⚠️  No matching files.")
            return

        print("\n📋 First 10 paths:")
        for filepath in paths[:10]:
            print(f"  {filepath}")
        if len(paths) > 10:
            print(f"  ... and {len(paths) - 10} more")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self, root_dir: str | None = None) -> None:
        """
        Walk ``root_dir`` (default: this script's directory) and write matches.

        Relative ``output_file`` paths are resolved under ``~/PythonDev/aoa/archive/logs``,
        not under the script directory or cwd.
        """
        if root_dir is None:
            root_dir = _script_parent_dir()
        root_dir = os.path.abspath(root_dir)

        ext_list = ", ".join(sorted(self.extensions))
        print(f"📜 This script: {os.path.abspath(__file__)}")
        print(f"📁 Scan root: {root_dir}")
        print(f"📦 Output logs dir (fixed): {self._output_logs_dir}")
        print(f"📎 Extensions: {ext_list}")
        print(f"🚫 Excluded dirs: {', '.join(sorted(self.exclude_dirs))}")
        print(f"📄 Output: {self.output_file}")

        os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)

        try:
            paths = self._scan_source_files(root_dir)

            with open(self.output_file, "w", encoding="utf-8") as out:
                self._write_header(out, root_dir, len(paths))
                self._write_files(out, paths)

            self._print_summary(paths)

        except Exception as exc:
            raise RuntimeError(f"❌ Collection failed: {exc}") from exc

    @classmethod
    def from_command_line(cls) -> None:
        """CLI: scan from script directory; optional argv adds exclude segments."""
        exclude_dirs = cls.DEFAULT_EXCLUDE.copy()
        if len(sys.argv) > 1:
            exclude_dirs.extend(sys.argv[1:])
            print(f"➕ Extra excludes: {', '.join(sys.argv[1:])}")
        cls(output_file=None, exclude_dirs=exclude_dirs).collect()


if __name__ == "__main__":
    PythonFileCollector(
        output_file="code.txt",
        exclude_dirs=[
            "__pycache__",
            ".cursor",
            ".github",
            ".gitverse",
            ".import_linter_cache",
            ".venv",
            "venv",
            ".git",
            ".ruff_cache",
            "archive",
            "scripts",
            "tests",
            "docs",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "htmlcov",
            "node_modules",
            ".vite",
        ],
        extensions=[
            # Backend / tooling in this package
            ".py",
            # HTML / SSR
            ".html",
            ".htm",
            # TypeScript / JavaScript (incl. ESM/CJS variants)
            ".ts",
            ".tsx",
            ".mts",
            ".cts",
            ".js",
            ".jsx",
            ".mjs",
            ".cjs",
            # Styles
            # ".css",
            # ".scss",
            # ".sass",
            # ".less",
            # ".styl",
            # Config & typed data (package.json, tsconfig, vite, components.json, …)
            # ".json",
            # ".jsonc",
            # ".yaml",
            # ".yml",
            # Docs / MDX
            # ".md",
            # ".mdx",
            # GraphQL clients
            # ".graphql",
            # ".gql",
            # SVG as text (inline assets / components)
            # ".svg",
            # Misc text shipped with the app (LICENSE, robots.txt, …)
            # ".txt",
        ],
    ).collect()
