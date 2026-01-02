FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workers/ ./workers/
COPY backend/ ./backend/
COPY shared/ ./shared/

ENV PYTHONPATH=/app

CMD ["python", "-m", "workers.runner"]

