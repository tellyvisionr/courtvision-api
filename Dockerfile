# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13.12

# ── Stage 1: install dependencies into an isolated venv ─────────────────────
FROM python:${PYTHON_VERSION}-slim AS deps

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Leverage BuildKit cache mount so repeated builds skip re-downloading packages.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# ── Stage 2: lean runtime image ──────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

# Prevent .pyc files and enable unbuffered logging.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Make the venv the active Python environment.
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Non-root user for least-privilege execution.
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Pull in only the pre-built venv — no build tools in the final image.
COPY --from=deps /opt/venv /opt/venv

USER appuser

# Copy application source only (tests, configs, etc. excluded via .dockerignore).
COPY app/ ./app/

EXPOSE 8000

# Lightweight liveness probe using Python's stdlib — no extra packages needed.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
        || exit 1

# Use exec form so the process receives signals directly (no shell wrapper).
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]
