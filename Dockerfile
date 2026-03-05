FROM python:3.12-slim

ARG YOUTRACK_TOKEN
ENV YOUTRACK_TOKEN=$YOUTRACK_TOKEN

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код проекта
COPY ActionEngine/ ./ActionEngine/
COPY API/ ./API/
COPY APP/ ./APP/
COPY EntryPoint/ ./EntryPoint/
COPY Utils/ ./Utils/
COPY *.py ./

ENTRYPOINT ["python"]