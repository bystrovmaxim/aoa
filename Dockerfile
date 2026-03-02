FROM python:3-alpine

ARG YOUTRACK_TOKEN
ENV YOUTRACK_TOKEN=$YOUTRACK_TOKEN

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код проекта
COPY ActionEngine/ ActionEngine/
COPY YouTrackMCP/ YouTrackMCP/
# Если есть корневые скрипты (например, run_action.py), копируем их
COPY run_action.py .  # если существует

# (Необязательно) можно скопировать все оставшиеся файлы, но лучше явно перечислить нужное
COPY *.py ./

# Указываем точку входа (как и раньше)
ENTRYPOINT ["python"]