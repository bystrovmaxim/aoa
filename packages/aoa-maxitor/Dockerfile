FROM python:3.12-slim

RUN pip install --no-cache-dir "aoa-maxitor==1.1.0"

ENV MAXITOR_API_HOST=0.0.0.0
ENV MAXITOR_API_PORT=8101

EXPOSE 8101

CMD ["maxitor-api"]
