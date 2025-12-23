FROM python:3.11-slim

WORKDIR /app

COPY packages/schemas /app/packages/schemas
COPY packages/shared /app/packages/shared
COPY apps/db_tool /app/apps/db_tool

RUN pip install --no-cache-dir -e /app/packages/schemas -e /app/packages/shared -e /app/apps/db_tool

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
