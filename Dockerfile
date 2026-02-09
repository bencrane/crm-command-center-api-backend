# --- Build stage ---
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build deps only (no dev tools in final image)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage ---
FROM python:3.13-slim

# Security: non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/

# Own everything by appuser
RUN chown -R appuser:appuser /app

USER appuser

# Railway injects PORT env var
ENV PORT=8000
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen(f'http://localhost:{__import__(\"os\").environ.get(\"PORT\", \"8000\")}/health')" || exit 1

# Run migrations then start server
# Using shell form so $PORT is expanded at runtime
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --loop uvloop
