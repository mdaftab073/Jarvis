FROM python:3.12-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgomp1 libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2,<3" \
    && python -m pip install -r requirements.txt

RUN useradd --create-home --uid 10001 jarvis \
    && mkdir -p /app/uploads /app/chroma_db /opt/huggingface \
    && chown -R jarvis:jarvis /app /opt/huggingface

COPY --chown=jarvis:jarvis app ./app
COPY --chown=jarvis:jarvis alembic ./alembic
COPY --chown=jarvis:jarvis alembic.ini ./alembic.ini

FROM runtime-base AS test
COPY --chown=jarvis:jarvis tests ./tests
RUN DATABASE_URL=sqlite:////tmp/jarvis-tests.db \
    GROQ_API_KEY=ci-test-key-not-used-by-mocked-tests \
    ENVIRONMENT=test \
    REQUIRE_AUTHENTICATED_STUDENT=false \
    python -m unittest discover -s tests

FROM runtime-base AS runtime
USER jarvis
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]