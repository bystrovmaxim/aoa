#!/bin/bash
# run_checks.sh - Скрипт для запуска всех проверок качества кода и сохранения лога
#
# УСТАНОВКА ВСЕХ ИНСТРУМЕНТОВ:
# pip install mypy flake8 flake8-async pylint radon vulture

set -e  # Прерывать выполнение при ошибке

# Переходим в директорию скрипта (предполагается, что скрипт лежит в корне проекта)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo "Не удалось перейти в директорию проекта"; exit 1; }

# Активируем виртуальное окружение (предполагается, что оно есть в venv)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Виртуальное окружение не найдено. Создайте его и установите зависимости."
    exit 1
fi

LOG_FILE="code_quality.log"
> "$LOG_FILE"

run_and_log() {
    echo "================================================================================" >> "$LOG_FILE"
    echo ">>> Команда: $1" >> "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
    local output
    output=$(eval "$1" 2>&1)
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        if [ -z "$output" ]; then
            echo "✅ Успех: команда выполнена без замечаний" >> "$LOG_FILE"
        else
            echo "$output" >> "$LOG_FILE"
        fi
    else
        echo "$output" >> "$LOG_FILE"
        echo "❌ Ошибка: команда завершилась с кодом $exit_code" >> "$LOG_FILE"
    fi
    echo "" >> "$LOG_FILE"
}

# --- Типы (включая частичную проверку await) ---
run_and_log "mypy --strict --follow-imports=normal --ignore-missing-imports --warn-unreachable --no-implicit-reexport ActionMachine/"

# --- Стиль + async антипаттерны (используем конфигурационный файл .flake8) ---
run_and_log "flake8 ActionMachine/"

# --- Пропущенные await + неиспользуемые импорты ---
run_and_log "pylint --disable=C,R,W0108 ActionMachine/"

# --- Метрики сложности ---
run_and_log "radon cc ActionMachine/ -s"
run_and_log "radon mi ActionMachine/ -s"
run_and_log "radon raw ActionMachine/ -s"

# --- Мёртвый код ---
run_and_log "vulture ActionMachine/ vulture_whitelist.txt"

echo "✅ Все проверки завершены. Лог сохранён в: $LOG_FILE"