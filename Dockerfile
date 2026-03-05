FROM python:3.12-slim

ARG YOUTRACK_TOKEN
ENV YOUTRACK_TOKEN=$YOUTRACK_TOKEN

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код проекта
COPY ActionEngine/ ./ActionEngine/
COPY App/ ./App/
COPY MCPServer/ ./MCPServer/
COPY Utils/ ./Utils/
COPY *.py ./

ENTRYPOINT ["python"]