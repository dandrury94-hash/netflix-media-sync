FROM python:3.12-slim

WORKDIR /app

RUN mkdir -p /config

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/app/entrypoint.sh"]
