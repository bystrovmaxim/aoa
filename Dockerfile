# Базовый образ Python 3 на Alpine (лёгкий и быстрый)
FROM python:3-alpine

# Аргумент для передачи токена YouTrack во время сборки
ARG YOUTRACK_TOKEN

# Сохраняем токен как переменную окружения внутри образа
ENV YOUTRACK_TOKEN=$YOUTRACK_TOKEN

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем сам скрипт
COPY get_issues.py .

# Делаем скрипт исполняемым (на всякий случай)
RUN chmod +x get_issues.py

# Указываем, что контейнер будет запускать Python (скрипт передаётся при запуске)
ENTRYPOINT ["python"]