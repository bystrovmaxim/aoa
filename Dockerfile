FROM python:3.12-slim

ARG YOUTRACK_TOKEN
ENV YOUTRACK_TOKEN=$YOUTRACK_TOKEN

WORKDIR /app

# Копируем только requirements для кэширования
COPY requirements.txt .

# Устанавливаем зависимости и сразу чистим кэш
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# Копируем весь код одной командой (слоёв меньше)
COPY ActionEngine/ ./ActionEngine/
COPY API/ ./API/
COPY APP/ ./APP/
COPY EntryPoint/ ./EntryPoint/
COPY Utils/ ./Utils/
COPY *.py ./

ENTRYPOINT ["python"]