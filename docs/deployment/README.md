# Jarvis Deployment Operations

## Environment Setup

Copy `.env.example` to `.env` and replace every `replace-with-...` value. Keep `.env` out of version control. Production requires PostgreSQL, a reachable Chroma service, a Groq API key, a Google OAuth client ID, a random JWT signing key of at least 32 bytes, and an admin metrics token.

`REQUIRE_AUTHENTICATED_STUDENT` defaults to `true`; production settings reject an explicit false value during configuration loading. Docker Compose also sets it to true. Local unit tests may patch the setting, but that mode is not production-ready.

## Google OAuth Setup

Create an OAuth 2.0 Web application client in Google Cloud Console. Register the frontend origins and redirect URIs used by the deployed frontend, then set `GOOGLE_CLIENT_ID` to that client ID on the backend. The frontend sends the Google-issued ID token to `POST /api/auth/google`; it must not send a trusted student ID, email, name, or picture as identity evidence. The backend verifies the token signature, issuer, audience, expiry, and verified email with Google's auth library.

Verified accounts are found by Google subject first, then by verified email to link an existing legacy student. An email associated with a different Google subject is rejected. No frontend profile fields are accepted.

## JWT Configuration

Set `JWT_SECRET_KEY` to a randomly generated value with at least 32 bytes of entropy and keep it private. `JWT_ALGORITHM` supports the HMAC algorithms `HS256`, `HS384`, and `HS512`; use `HS256` unless an operational requirement dictates otherwise. Access tokens default to 15 minutes and refresh tokens to 30 days. Set `ACCESS_TOKEN_EXPIRE_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS` as needed.

Refresh tokens are stored by JTI, rotated on refresh, and revoked on logout. Access tokens are short-lived and remain valid until expiry after logout; clients should discard both tokens immediately. Use TLS for every external request and rotate the signing key through a planned session invalidation.

## Docker Startup

From a clean checkout:

```powershell
Copy-Item .env.example .env
# Edit .env and replace all placeholders with real values.
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs --tail 200 jarvis-api
```

Compose waits for PostgreSQL and Chroma health checks. The API container runs `alembic upgrade head` before Uvicorn starts. The scheduler starts with the API process. Confirm startup and readiness with the health endpoints below. To stop without deleting data, run `docker compose down`; do not use `down -v` unless intentionally discarding persistent volumes.

## Migration Process

Inspect the graph and current database before a release:

```powershell
cd backend
alembic heads
alembic current
alembic upgrade head
```

The graph must have exactly one head. Take a database backup before production upgrades. Compose automatically applies migrations at API startup; on an existing deployment, run `docker compose exec jarvis-api alembic upgrade head` during the release window and verify `/health/ready` afterward. The Google identity migration preserves existing student rows and leaves their Google identity unlinked until verified login.

The current forward migration removes deprecated MIS persistence and `svnit_mis` connector rows. Inspect those tables and connector records in the target database before release; the migration does not preserve deleted MIS records for downgrade.

## Health Monitoring

These endpoints are public and contain dependency status only, never credentials:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Aggregate dependency status |
| `GET /health/live` | Process liveness |
| `GET /health/ready` | Traffic readiness |
| `GET /health/dependencies` | Per-dependency status |
| `GET /system/health` | System status used by the Compose health check |

Readiness covers database, ChromaDB, scheduler, tool registry, migrations, metrics, audit logging, and authentication configuration. Run `python backend/scripts/validate_deployment.py` after startup; it writes `deployment_report.md` and exits nonzero on failed checks.

See [API_INVENTORY.md](./API_INVENTORY.md) for the registered routes, methods, authentication treatment, and OpenAPI request/response schemas.

## Authentication Routes

| Method and route | Access | Purpose |
|---|---|---|
| `POST /api/auth/google` | Public | Verify Google ID token and issue access/refresh tokens |
| `POST /api/auth/refresh` | Public, refresh token required | Rotate refresh token and issue a new token pair |
| `GET /api/auth/me` | Bearer access token | Return the trusted current student |
| `POST /api/auth/logout` | Bearer access token and refresh token | Revoke the refresh token |

All other `/api` routes require a Bearer access token when production strict-auth mode is enabled. `request.state.student_id` is set only from a verified access token. Ownership checks must compare any route resource owner to that principal; request payload IDs and email headers are not identity sources.

## End-to-End and Load Checks

For staging, obtain a short-lived Google ID token for a disposable test account and export it as `GOOGLE_ID_TOKEN`. Run `python backend/scripts/run_release_e2e.py`; the runner authenticates through Google and removes tracked run resources while retaining the test account. Audit events and some derived academic history can remain, so use a disposable account and database. Do not use a personal account for staging validation. The runner uses an in-process FastAPI test client against the configured database and vector store, so it validates real dependencies but is not a substitute for a browser-to-deployed-URL smoke test.

Run unit tests in explicit test mode from `backend/`:

```powershell
$env:ENVIRONMENT = "test"
$env:REQUIRE_AUTHENTICATED_STUDENT = "false"
python -m unittest discover -s tests -p "test*.py"
```

For live staging concurrency, set `LOAD_TEST_ACCESS_TOKEN`, `LOAD_TEST_SUBJECT_ID`, and optionally `LOAD_TEST_BASE_URL` and `LOAD_TEST_CONCURRENCY` (1-8), then run `python backend/scripts/validate_load.py`. It concurrently probes identity, chat/session isolation, and PDF uploads, then checks metrics and readiness. It creates records and files, so use a disposable staging student and subject.

## Production Checklist

- Replace every environment placeholder; keep secrets outside source control.
- Confirm `REQUIRE_AUTHENTICATED_STUDENT=true` and an OAuth audience matching the frontend.
- Confirm a strong JWT key, TLS, rate limits, and metrics admin token are configured.
- Back up PostgreSQL, Chroma data, and uploads before deployment.
- Confirm `alembic heads` returns one head and the production database is at that head.
- Confirm all four health endpoints report healthy/ready and `/system/health` is healthy.
- Run the deployment validator and review the generated report for failed or unavailable checks.
- Run authenticated E2E and staging concurrency checks; verify no cross-student access or session crossover.
- Confirm scheduler jobs, tool registration, audit logging, and background job processing after restart.