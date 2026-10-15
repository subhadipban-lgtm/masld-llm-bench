# MASLD-Bench API service image.
# Heavy local-model deps (torch/transformers/peft) are intentionally excluded:
# frontier runs + scoring are fully containerized; local HF eval runs on the
# host or via the Colab bridge.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Package first for layer caching.
COPY pyproject.toml README.md ./
COPY core/ core/
COPY api/ api/
COPY agents/ agents/
COPY persistence/ persistence/

RUN pip install --no-cache-dir ".[api]"

# Non-root runtime user.
RUN useradd --create-home --uid 10001 masld && chown -R masld /app
USER masld

EXPOSE 8000

# Research repo (prompts/, results/) is mounted read-only at /research by compose.
ENV MASLD_ROOT=/research

CMD ["uvicorn", "masld_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
