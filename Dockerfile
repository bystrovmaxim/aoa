FROM python:3.12-slim

ARG YOUTRACK_TOKEN
ENV YOUTRACK_TOKEN=$YOUTRACK_TOKEN

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ActionEngine/ ./ActionEngine/
COPY YouTrackMCP/ ./YouTrackMCP/
COPY Utils/ ./Utils/
COPY *.py ./

ENTRYPOINT ["python"]