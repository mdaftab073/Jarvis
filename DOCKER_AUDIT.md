# Docker Audit

Audit date: 2026-10-03

## Results

- `docker compose config -q` passed when required variables were supplied as non-production placeholders.
- The checked-in local environment does not currently provide all required Compose values; Compose reports a missing `METRICS_ADMIN_TOKEN`. The remaining required values must also be real deployment credentials.
- The runtime image built successfully as `jarvis-rc-audit-jarvis-api:latest` (2.49 GB).
- A full isolated Compose deployment started PostgreSQL and Chroma as healthy, applied migrations in the API container, and reached healthy status itself. The isolated API returned healthy liveness, readiness, and system-health results and documented all 159 operations.
- The API image has runtime and test stages. The runtime stage uses Python 3.12 slim, installs CPU PyTorch and backend requirements, runs as UID 10001, exposes port 8000, and applies migrations before launching Uvicorn.

## Startup ordering and health

- PostgreSQL uses `pg_isready` and a Compose healthcheck.
- Chroma has a TCP-port healthcheck. This confirms a listener, not collection-level readiness.
- `jarvis-api` waits for both services with `depends_on: condition: service_healthy`.
- The API command runs `alembic upgrade head` before Uvicorn.
- Production application startup now actively checks PostgreSQL and Chroma and fails with a clear dependency-specific error if either is unavailable.
- The initial isolated run caught an incorrect top-level `overall` lookup; the Compose probe now matches the standardized envelope and the container reached healthy status.
- Persistent volumes are declared for PostgreSQL, Chroma, uploads, and the Hugging Face model cache.
- After verification, the isolated audit project and its temporary volumes were removed. The unrelated pre-existing Compose project on port 8000 was left running and untouched.

## Environment handling

Compose requires `POSTGRES_PASSWORD`, `GROQ_API_KEY`, `CONNECTOR_ENCRYPTION_KEY`, `METRICS_ADMIN_TOKEN`, `GOOGLE_CLIENT_ID`, and `JWT_SECRET_KEY`. `ALLOWED_ORIGINS` must contain the exact frontend origin in production. Compose constructs `DATABASE_URL`, configures the Chroma service host, and forces authenticated-student mode on.

`.env.example` contains placeholders. Do not deploy with placeholders or commit a real `.env`.

## Release risks and follow-up

1. Repeat the Compose deployment in staging with real, environment-appropriate secrets.
2. Exercise authenticated API traffic and Google OAuth from the configured frontend origin.
3. The API image is large (2.49 GB); account for registry transfer and disk capacity when planning deployments.
4. Chroma's Compose healthcheck is only a TCP check. The API-level collection count and readiness endpoint provide the stronger readiness signal after application startup.
