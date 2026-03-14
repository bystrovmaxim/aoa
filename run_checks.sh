#!/bin/bash
# run_checks.sh - Скрипт для запуска всех проверок качества кода и сохранения лога
#
# УСТАНОВКА ВСЕХ ИНСТРУМЕНТОВ:
# pip install mypy flake8 flake8-async pylint radon vulture

set -e  # Прерывать выполнение при критической ошибке

# Переходим в директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo "❌ Не удалось перейти в директорию проекта"; exit 1; }

# Активируем виртуальное окружение (если есть)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "⚠️ Виртуальное окружение не найдено. Продолжаем без активации."
fi

LOG_FILE="code_quality.log"
> "$LOG_FILE"  # Очищаем лог-файл

# Функция для запуска команды с логированием
run_and_log() {
    local cmd="$1"
    local name="$2"  # человекочитаемое имя проверки
    echo "▶ Запуск $name..."
    
    # Записываем заголовок в лог
    {
        echo "================================================================================"
        echo ">>> Команда: $cmd"
        echo "================================================================================"
    } >> "$LOG_FILE"
    
    # Выполняем команду, перенаправляем вывод в лог
    if eval "$cmd" >> "$LOG_FILE" 2>&1; then
        echo "✅ $name: успешно" | tee -a "$LOG_FILE"
    else
        local ec=$?
        echo "❌ $name: ошибка (код $ec)" | tee -a "$LOG_FILE"
    fi
    echo "" >> "$LOG_FILE"
}

# --- Запуск всех проверок ---
run_and_log "mypy --strict --follow-imports=normal --warn-unreachable --no-implicit-reexport ActionMachine/" "mypy"
run_and_log "flake8 ActionMachine/" "flake8"
run_and_log "pylint --disable=C,R,W0108 ActionMachine/" "pylint"
run_and_log "radon cc ActionMachine/ -s" "radon cc"
run_and_log "radon mi ActionMachine/ -s" "radon mi"
run_and_log "radon raw ActionMachine/ -s" "radon raw"

# Vulture с опциональным whitelist
if [ -f "vulture_whitelist.txt" ]; then
    run_and_log "vulture ActionMachine/ vulture_whitelist.txt" "vulture"
else
    run_and_log "vulture ActionMachine/" "vulture"
fi

echo ""
echo "✅ Все проверки завершены. Лог сохранён в: $LOG_FILE"