FROM python:3.11-slim

WORKDIR /app

COPY packages/schemas /app/packages/schemas
COPY packages/shared /app/packages/shared
COPY apps/flight_tool /app/apps/flight_tool

RUN pip install --no-cache-dir -e /app/packages/schemas -e /app/packages/shared -e /app/apps/flight_tool

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
FROM python:3.11-slim

WORKDIR /app

COPY packages/schemas /app/packages/schemas
COPY packages/shared /app/packages/shared
COPY apps/flight_tool /app/apps/flight_tool

RUN pip install --no-cache-dir -e /app/packages/schemas -e /app/packages/shared -e /app/apps/flight_tool

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
