FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY packages /app/packages
COPY apps/guardrails /app/apps/guardrails

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

ENV NEMOGUARDRAILS_LLM_FRAMEWORK=langchain

EXPOSE 8001

CMD ["uvicorn", "apps.guardrails.main:app", "--host", "0.0.0.0", "--port", "8001"]
