#!/bin/bash
# run_checks_with_log.sh — Запуск проверок с сохранением лога в archive/logs/

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Создаём директорию для логов, если её нет
mkdir -p archive/logs

# Фиксированное имя файла лога (перезаписывается при каждом запуске)
LOG_FILE="archive/logs/check-all.log"

echo -e "${YELLOW}📝 Лог будет сохранён в: ${LOG_FILE}${NC}"
echo ""

# Заголовок лога (перезаписываем файл)
{
    echo "=================================================="
    echo "📋 Проверка проекта ActionMachine"
    echo "📅 Дата: $(date)"
    echo "🕒 Время: $(date +%H:%M:%S)"
    echo "=================================================="
    echo ""
} > "$LOG_FILE"

# Функция для запуска команды с логированием (без вывода в консоль)
run_and_log() {
    local cmd="$1"
    local name="$2"
    
    echo -e "${YELLOW}▶ Запуск: ${name}${NC}"
    
    # Пишем заголовок в лог
    {
        echo "=== $name ==="
        echo "$ $cmd"
        echo ""
    } >> "$LOG_FILE"
    
    # Выполняем команду, вывод только в лог
    eval "$cmd" >> "$LOG_FILE" 2>&1
    
    local exit_code=$?
    echo "" >> "$LOG_FILE"
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ ${name} — успешно${NC}"
        echo "✅ ${name} — успешно" >> "$LOG_FILE"
    else
        echo -e "${RED}❌ ${name} — ошибка (код $exit_code)${NC}"
        echo "❌ ${name} — ошибка (код $exit_code)" >> "$LOG_FILE"
    fi
    echo "" >> "$LOG_FILE"
}

# Переходим в корень проекта (предполагаем, что скрипт в корне)
cd "$(dirname "$0")" || exit 1

# Проверяем, что мы в правильной директории
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Ошибка: файл pyproject.toml не найден в текущей директории${NC}"
    echo -e "${YELLOW}   Текущая директория: $(pwd)${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Запуск полной проверки проекта...${NC}"
echo ""

# Шаг 0: Автоисправление импортов (ruff --fix)
run_and_log "uv run ruff check --fix --select I001 src/" "Автоисправление импортов (ruff)"

# Запускаем остальные проверки
run_and_log "uv run task lint" "Линтер (ruff)"
run_and_log "uv run task typecheck" "Проверка типов (mypy)"
run_and_log "uv run task pylint" "Полный линтер (pylint)"
run_and_log "uv run task dead" "Мёртвый код (vulture)"
run_and_log "uv run task test" "Тесты (pytest)"
run_and_log "uv run task cc" "Цикломатическая сложность (radon)"
run_and_log "uv run task mi" "Индекс поддерживаемости (radon)"

# Финальный итог
{
    echo "=================================================="
    echo "✅ Проверка завершена"
    echo "📁 Лог сохранён в: $LOG_FILE"
    echo "=================================================="
} >> "$LOG_FILE"

echo ""
echo -e "${GREEN}✅ Все проверки завершены!${NC}"
echo -e "${GREEN}📁 Лог сохранён в: ${LOG_FILE}${NC}"