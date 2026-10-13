# One image, two roles: docker-compose.yml runs this with CMD overridden
# for the "api" vs "worker" service. Build context is the repo root so both
# backend/ and the top-level worker/ script can be copied into the image.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY worker/ ./worker/

RUN mkdir -p /app/uploads

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
