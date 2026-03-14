#!/bin/bash
# run_checks.sh - Скрипт для запуска всех проверок качества кода и сохранения лога
#
# УСТАНОВКА ВСЕХ ИНСТРУМЕНТОВ:
# pip install mypy
# pip install flake8
# pip install flake8-async
# pip install pylint
# pip install radon
# pip install vulture
#
# Или одной командой:
# pip install mypy flake8 flake8-async pylint radon vulture

set -e
cd ~/PythonDev/kanban_assistant || { echo "Не удалось перейти в директорию проекта"; exit 1; }
source venv/bin/activate

LOG_FILE="code_quality.log"
> "$LOG_FILE"

run_and_log() {
    echo "================================================================================" >> "$LOG_FILE"
    echo ">>> Команда: $1" >> "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
    eval "$1" >> "$LOG_FILE" 2>&1
    echo "" >> "$LOG_FILE"
}

# --- Типы (включая частичную проверку await) ---
run_and_log "mypy --strict --follow-imports=normal --ignore-missing-imports --warn-unreachable --no-implicit-reexport ActionMachine/"

# --- Стиль + async антипаттерны (игнорируем только E501 - слишком длинные строки) ---
run_and_log "flake8 --select=ASYNC,E,W --ignore=E501 --max-line-length=120 ActionMachine/"

# --- Пропущенные await + неиспользуемые импорты ---
run_and_log "pylint --disable=C,R,W0108 ActionMachine/"

# --- Метрики сложности ---
run_and_log "radon cc ActionMachine/ -s"
run_and_log "radon mi ActionMachine/ -s"
run_and_log "radon raw ActionMachine/ -s"

# --- Мёртвый код ---
run_and_log "vulture ActionMachine/ vulture_whitelist.txt"

echo "✅ Все проверки завершены. Лог сохранён в: $LOG_FILE"