FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/platform-api/src

WORKDIR /app/services/platform-api

COPY services/platform-api/pyproject.toml services/platform-api/uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e .

COPY services/platform-api /app/services/platform-api
COPY config /app/config
COPY schemas /app/schemas
COPY db /app/db

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
