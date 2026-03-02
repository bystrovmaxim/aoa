#!/bin/bash
# Загружает переменные окружения из файла .env

if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✅ Переменные окружения загружены из .env"
else
    echo "❌ Файл .env не найден. Создайте его на основе .env.example"
fi