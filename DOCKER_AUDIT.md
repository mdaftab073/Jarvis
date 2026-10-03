# Docker Audit

Audit date: 2026-10-03

## Results

- `docker compose config -q` passed when required variables were supplied as non-production placeholders.
- The checked-in local environment does not currently provide all required Compose values; Compose reports a missing `METRICS_ADMIN_TOKEN`. The remaining required values must also be real deployment credentials.
- Docker image build and container startup could not be verified: the Docker CLI is installed, but the Docker Desktop Linux engine was not running (`docker` could not connect to its named pipe).
- The API image has runtime and test stages. The runtime stage uses Python 3.12 slim, installs CPU PyTorch and backend requirements, runs as UID 10001, exposes port 8000, and applies migrations before launching Uvicorn.

## Startup ordering and health

- PostgreSQL uses `pg_isready` and a Compose healthcheck.
- Chroma has a TCP-port healthcheck. This confirms a listener, not collection-level readiness.
- `jarvis-api` waits for both services with `depends_on: condition: service_healthy`.
- The API command runs `alembic upgrade head` before Uvicorn.
- Production application startup now actively checks PostgreSQL and Chroma and fails with a clear dependency-specific error if either is unavailable.
- The API container healthcheck calls `/system/health`; it requires the enveloped payload's `overall` value to be `healthy`.
- Persistent volumes are declared for PostgreSQL, Chroma, uploads, and the Hugging Face model cache.

## Environment handling

Compose requires `POSTGRES_PASSWORD`, `GROQ_API_KEY`, `CONNECTOR_ENCRYPTION_KEY`, `METRICS_ADMIN_TOKEN`, `GOOGLE_CLIENT_ID`, and `JWT_SECRET_KEY`. `ALLOWED_ORIGINS` must contain the exact frontend origin in production. Compose constructs `DATABASE_URL`, configures the Chroma service host, and forces authenticated-student mode on.

`.env.example` contains placeholders. Do not deploy with placeholders or commit a real `.env`.

## Release risks and follow-up

1. Run `docker compose config -q`, `docker compose build jarvis-api`, and a fresh named-project deployment on a Docker-enabled host with real staging secrets.
2. Confirm container health becomes healthy after migrations, then exercise authenticated API traffic and an OAuth sign-in from the configured frontend origin.
3. The image build was not run in this environment; CPU PyTorch/model-layer downloads, image size, startup timing, and healthcheck timing remain unverified here.
4. Chroma's Compose healthcheck is only a TCP check. The API-level collection count and health endpoint provide the stronger readiness signal after application startup.
