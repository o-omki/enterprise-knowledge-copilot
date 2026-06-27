FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md /build/
COPY packages /build/packages
COPY configs /build/configs
COPY apps /build/apps

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

FROM python:3.11-slim AS runner

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md /app/
COPY configs /app/configs
COPY packages /app/packages
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker

RUN groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -m -d /home/appuser appuser && \
    chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD celery -A apps.worker.celery_app inspect ping --timeout 5 || exit 1

CMD ["celery", "-A", "apps.worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
