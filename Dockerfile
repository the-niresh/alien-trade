# Alien-Trade agent — containerised for demo deployments.
# Default EXECUTION_BACKEND=paper (no real capital in demo mode).
#
# Build:  docker build -t alien-trade .
# Run:    docker run -p 8000:8000 --env-file .env.local alien-trade

FROM python:3.11-slim AS base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EXECUTION_BACKEND=paper \
    TRADING_MODE=paper \
    SECOND_BRAIN=1 \
    PORT=8000

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# ── Python deps (layer-cached separately from source code) ──────────────────
FROM base AS deps

COPY core/pyproject.toml ./core/pyproject.toml
# Create a minimal stub so the editable install resolves
RUN mkdir -p core/backtest core/data core/risk core/signals core/strategy \
    core/config core/agent && \
    touch core/backtest/__init__.py core/data/__init__.py \
          core/risk/__init__.py core/signals/__init__.py \
          core/strategy/__init__.py core/config/__init__.py \
          core/agent/__init__.py
RUN cd core && uv venv .venv && \
    uv pip install -e ".[server]" --quiet 2>/dev/null || \
    uv pip install -e "." --quiet

# ── Final image ───────────────────────────────────────────────────────────────
FROM base AS final

# Copy the venv built in the deps stage
COPY --from=deps /app/core/.venv /app/core/.venv

# Copy source
COPY core/ ./core/
COPY agent/ ./agent/
COPY .env.example .env.example

ENV PYTHONPATH=/app/core \
    PATH="/app/core/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -sf http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "agent.server:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
