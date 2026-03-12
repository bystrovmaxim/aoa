#!/bin/bash
# run_checks.sh - Скрипт для запуска всех проверок качества кода и сохранения лога

set -e  # Прерывать выполнение при ошибке (опционально, можно закомментировать)

# Переходим в корневую директорию проекта
cd ~/PythonDev/kanban_assistant || { echo "Не удалось перейти в директорию проекта"; exit 1; }

# Активируем виртуальное окружение (если необходимо)
source venv/bin/activate

LOG_FILE="code_quality.log"

# Очищаем предыдущий лог-файл
> "$LOG_FILE"

# Функция для выполнения команды с заголовком
run_and_log() {
    echo "================================================================================" >> "$LOG_FILE"
    echo ">>> Команда: $1" >> "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
    eval "$1" >> "$LOG_FILE" 2>&1
    echo "" >> "$LOG_FILE"
}

# Запускаем все проверки
run_and_log "mypy --strict --follow-imports=normal --ignore-missing-imports --warn-unreachable --no-implicit-reexport ActionMachine/"
run_and_log "radon cc ActionMachine/ -s"
run_and_log "radon mi ActionMachine/ -s"
run_and_log "radon raw ActionMachine/ -s"
run_and_log "vulture ActionMachine/ vulture_whitelist.txt"

echo "✅ Все проверки завершены. Лог сохранён в: $LOG_FILE"