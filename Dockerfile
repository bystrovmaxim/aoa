FROM python:3-alpine

ARG YOUTRACK_TOKEN
ENV YOUTRACK_TOKEN=$YOUTRACK_TOKEN

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код проекта (каждая папка в свою подпапку)
COPY ActionEngine/ ./ActionEngine/
COPY YouTrackMCP/ ./YouTrackMCP/
COPY Utils/ ./Utils/

# Если есть корневые Python-скрипты, копируем их (например, run_action.py, если есть)
COPY *.py ./

ENTRYPOINT ["python"]