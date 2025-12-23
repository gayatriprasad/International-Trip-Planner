import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FLIGHT_TOOL_URL = os.getenv("FLIGHT_TOOL_URL", "http://localhost:8001")
DB_TOOL_URL = os.getenv("DB_TOOL_URL", "http://localhost:8002")
