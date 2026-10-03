# Jarvis Backend Deployment Guide

Audit date: 2026-10-03

## Requirements

- Python 3.12 for a direct host deployment, or Docker with the Linux engine and Compose for container deployment.
- PostgreSQL and ChromaDB with persistent storage.
- Real production values for Groq, Google OAuth, JWT signing, connector encryption, metrics administration, and allowed browser origins.
- Persistent storage and tested backups for PostgreSQL, ChromaDB, uploaded files, and the Hugging Face model cache.

Do not deploy `.env.example` placeholders. Production settings reject missing/template credentials, require a JWT key of at least 32 bytes, validate the Fernet connector key, require an explicit CORS origin, and require authenticated-student mode.

## Local host setup

1. Copy `.env.example` to `.env` at the repository root and replace all placeholders.
2. For a direct host run, set `DATABASE_URL` to the local PostgreSQL database URL; Compose constructs this value automatically for its API container. Set `ENVIRONMENT=development`, `REQUIRE_AUTHENTICATED_STUDENT=true`, and configure Chroma for the intended local persistent directory or host.
3. Create and activate a Python 3.12 virtual environment, then install the backend dependencies:

   ```powershell
   cd backend
   python -m pip install -r requirements.txt
   ```

4. Confirm PostgreSQL is reachable and Chroma storage is writable. Apply schema changes and start the service:

   ```powershell
   python -m alembic upgrade head
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. Check `http://127.0.0.1:8000/health/ready` and open `http://127.0.0.1:8000/docs`.

Production startup checks PostgreSQL and Chroma initialization and fails with a clear dependency-specific error. Non-production environments report dependency failures through readiness endpoints without the production startup gate.

## Docker Compose setup

1. From the repository root, copy and complete the environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set real values for `POSTGRES_PASSWORD`, `GROQ_API_KEY`, `CONNECTOR_ENCRYPTION_KEY`, `METRICS_ADMIN_TOKEN`, `GOOGLE_CLIENT_ID`, `JWT_SECRET_KEY`, and `ALLOWED_ORIGINS`. `POSTGRES_DB`, `POSTGRES_USER`, and `JARVIS_PORT` have defaults. Keep `.env` private.

2. Validate interpolation and start the services:

   ```powershell
   docker compose config -q
   docker compose up --build -d
   docker compose ps
   ```

   Compose waits for PostgreSQL and Chroma healthchecks. The API container applies Alembic migrations before launching Uvicorn. Persistent named volumes hold PostgreSQL data, Chroma data, uploads, and the model cache.

3. Verify the service:

   ```powershell
   Invoke-RestMethod http://localhost:8000/health/live
   Invoke-RestMethod http://localhost:8000/health/ready
   Invoke-RestMethod http://localhost:8000/system/health
   ```

   A healthy `/health/ready` response has `data.ready` set to `true`; `/system/health` must report `data.overall` as `healthy`. The API container uses the latter condition for its Docker healthcheck.

`docker compose down` stops services and preserves named volumes. Do not use `docker compose down -v` unless intentional deletion of all named data volumes has been approved.

## Migration procedure

For a direct host deployment, set `DATABASE_URL` explicitly to the intended database. From `backend/`:

```powershell
python -m alembic heads
python -m alembic current
python -m alembic upgrade head
python -m alembic current
```

The release head is `f0b1c3d5e709`. Before upgrading an existing database, take and verify backups and review [MIGRATION_AUDIT.md](./MIGRATION_AUDIT.md). Migration `e7b4c1d9a260` removes legacy MIS data and tables; downgrading past it does not restore deleted data.

## Backups and restore

The host utility `backend/scripts/backup.py` assumes PostgreSQL is reachable at `localhost` and Chroma/uploads are local paths. It is suitable only when those assumptions match the deployment. For Compose or managed infrastructure, use database-native backups and snapshots/copies of the persistent Chroma and uploads volumes coordinated with the database backup.

Example PostgreSQL dump from Compose (run from a shell that supports the command):

```sh
mkdir -p backups
docker compose exec -T postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > backups/jarvis-postgres.dump
```

Also snapshot the Chroma and uploads volumes and retain the matching deployment configuration and encryption keys. Test restore procedures in an isolated environment before relying on the backup. `backend/scripts/restore.py` is destructive and assumes a compatible ZIP archive, local PostgreSQL at `localhost`, and local Chroma/uploads paths; it is not a drop-in Compose restore utility.

## Monitoring

- Liveness: `GET /health/live`
- Readiness/dependencies: `GET /health/ready`, `GET /health/dependencies`
- Detailed system status: `GET /system/health`
- API metrics: `GET /api/system/metrics`
- Administrative metrics summary: `GET /api/metrics/summary` with both normal API authentication and `X-Admin-Token`

Readiness checks cover the database, Chroma, scheduler, tools, migration state, metrics, audit table, and authentication configuration. Monitor health transitions and application logs; do not expose admin tokens or connection strings in monitoring output.

## Release-specific follow-up

The migration cycle was verified against an empty temporary PostgreSQL database, but the configured local database was deliberately left at `4c8ef6d1a203`. Docker image build/startup could not be verified because the Docker daemon was unavailable during this audit. Before production traffic, rehearse on a restored staging backup, verify OAuth and CORS from the deployed frontend origin, and build/start the Compose stack on a Docker-enabled host.
