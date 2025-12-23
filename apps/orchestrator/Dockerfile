FROM python:3.11-slim

WORKDIR /app

COPY packages/schemas /app/packages/schemas
COPY packages/shared /app/packages/shared
COPY apps/orchestrator /app/apps/orchestrator

RUN pip install --no-cache-dir -e /app/packages/schemas -e /app/packages/shared -e /app/apps/orchestrator

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
