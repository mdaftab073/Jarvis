# Backend Release Notes

Release candidate audit date: 2026-10-03

## Included capabilities

- FastAPI service with documented routes, standardized success/error response envelopes, and OpenAPI schema generation.
- PostgreSQL persistence managed by Alembic, including student, course, subject, learning, academic, chat, connector, audit, and background-job records.
- Google OAuth sign-in with JWT access/refresh tokens and middleware-enforced student identity/ownership.
- Academic agents, tools, study planning, retrieval-augmented generation, analytics, and background jobs.
- ChromaDB vector storage and keyword-search synchronization for study-material retrieval.
- Health/readiness checks, operational metrics, configurable CORS, request tracking, and route rate limits.
- Production startup checks for PostgreSQL and ChromaDB.
- A migration aligning model-declared database check constraints with the fresh schema.

## Removed

- SVNIT MIS integration and its runtime persistence have been removed. Migration `e7b4c1d9a260` deletes legacy MIS accounts, session/profile tables, and matching generic connector rows. Its downgrade does not restore the removed data.

## Architecture

FastAPI routes invoke services and agent/tool orchestration. PostgreSQL stores relational application data; ChromaDB stores retrieval vectors. Authentication middleware maps bearer tokens to the authenticated student. See [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md).

## Known limitations and release gates

- 92 operations expose `Any` as the inner success payload, limiting generated client typing.
- OpenAPI does not declare the bearer security scheme; auth requirements are described in the frontend API reference.
- SlowAPI uses in-memory per-process storage; limits are not shared across API instances.
- Existing databases must be reviewed and backed up before applying the irreversible MIS-removal migration.
- Docker image build and Compose startup were not executable in the audit environment because the Docker daemon was unavailable.
- The configured local database remains at revision `4c8ef6d1a203`; it was intentionally not upgraded.
- Production OAuth, browser CORS, external-provider credentials, and backup restore must be verified in staging.

## Deployment requirements

Python 3.12, PostgreSQL, ChromaDB, and valid production configuration are required. Production requires real Groq, Google OAuth, JWT, connector-encryption, metrics-admin, and frontend-origin settings. Compose provisions PostgreSQL and ChromaDB and runs migrations before the API. See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md).
