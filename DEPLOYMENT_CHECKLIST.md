# Jarvis Backend Deployment Checklist

Release checklist for the Docker Compose backend. Commands are for Windows PowerShell from the repository root.

## 1. Configure production secrets

1. Copy the template and edit it:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

2. Replace every `replace-with-...` placeholder with a unique production value:
   - `POSTGRES_PASSWORD`: long, unique, URL-safe characters (Compose inserts it into `DATABASE_URL`).
   - `GROQ_API_KEY`: valid provider key.
   - `METRICS_ADMIN_TOKEN`: long, random admin secret.
   - `GOOGLE_CLIENT_ID`: production Google OAuth Web client ID.
   - `JWT_SECRET_KEY`: random secret of at least 32 bytes.
   - `ALLOWED_ORIGINS`: comma-separated exact frontend origins, including scheme and port where applicable. Production requires at least one; do not use `*`.
   - `CONNECTOR_ENCRYPTION_KEY`: valid Fernet key. Keep it stable; rotating it without re-encrypting stored credentials makes those credentials unreadable.
3. `POSTGRES_DB`, `POSTGRES_USER`, and `JARVIS_PORT` have Compose defaults but may be set explicitly. Set OAuth client origins to match `ALLOWED_ORIGINS`.
4. Do not add `.env` to source control. `DATABASE_URL` is constructed by Compose from the `POSTGRES_*` values; Compose also pins `ENVIRONMENT=production` and `REQUIRE_AUTHENTICATED_STUDENT=true`.
5. Production startup rejects `replace-with-...` placeholders and validates the connector Fernet key. `docker compose config --quiet` checks Compose syntax but does not replace the application startup checks.

## 2. Review the release and preserve existing data

For an existing installation, take and verify a recoverable backup of PostgreSQL, the Chroma persistent volume, and uploaded files using the target platform's backup procedure before upgrading. The API image applies Alembic migrations at startup.

**Critical migration gate:** the [MIS-removal migration](./backend/alembic/versions/e7b4c1d9a260_remove_deprecated_mis.py) deletes legacy MIS data and does not restore it on downgrade. Confirm whether the target database contains any such data, obtain approval for its removal, and retain a verified pre-upgrade backup before continuing.

For an existing database at the pre-removal schema, inspect exactly the records affected before upgrading:

```powershell
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT (SELECT COUNT(*) FROM mis_student_profiles) AS profiles, (SELECT COUNT(*) FROM mis_accounts) AS accounts, (SELECT COUNT(*) FROM mis_login_sessions) AS login_sessions, (SELECT COUNT(*) FROM student_connectors WHERE lower(connector_type) = ''svnit_mis'') AS legacy_connectors;"'
```

If any count is nonzero, pause for explicit data-removal approval. If the legacy tables do not exist because the database is already past this migration, inspect its Alembic revision and follow the backup gate for the actual current schema.

For a local Compose backup, stop API writes and create a SQL dump plus copies of the Chroma and upload directories:

```powershell
$releaseStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
New-Item -ItemType Directory -Force .\backups | Out-Null
docker compose stop jarvis-api
docker compose exec -T postgres sh -c 'pg_dump --no-owner --no-acl -U "$POSTGRES_USER" "$POSTGRES_DB"' |
    Out-File -FilePath ".\backups\postgres-$releaseStamp.sql" -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL backup failed.' }
docker compose cp chroma:/chroma/chroma ".\backups\chroma-$releaseStamp"
if ($LASTEXITCODE -ne 0) { throw 'Chroma backup failed.' }
docker compose cp jarvis-api:/app/uploads ".\backups\uploads-$releaseStamp"
if ($LASTEXITCODE -ne 0) { throw 'Upload backup failed.' }
```

Keep these files outside the deployment host as well. For a new installation, there is no existing application data to back up.

## 3. Validate configuration and deploy

```powershell
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration is invalid.' }
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Compose deployment failed.' }
docker compose ps
docker compose logs --tail 200 jarvis-api
```

Wait for PostgreSQL and Chroma health checks and for `jarvis-api` to finish applying migrations. Review startup logs for migration, dependency, authentication, or scheduler errors.

## 4. Verify migrations and API health

```powershell
docker compose exec -T jarvis-api alembic heads
docker compose exec -T jarvis-api alembic current
$live = Invoke-RestMethod -Uri 'http://localhost:8000/health/live'
if ($live.success -ne $true -or $live.data.status -ne 'alive') {
    throw 'Liveness check failed.'
}
$ready = Invoke-RestMethod -Uri 'http://localhost:8000/health/ready'
if ($ready.success -ne $true -or $ready.data.ready -ne $true) {
    throw 'Readiness check failed; inspect $ready.data and the API logs.'
}
$spec = Invoke-RestMethod -Uri 'http://localhost:8000/openapi.json'
if (-not $spec.openapi -or $spec.paths.Count -eq 0) {
    throw 'OpenAPI document is unavailable.'
}
```

Expect one Alembic head and a current database at that head. Health endpoints use the standard success envelope; health fields are inside `data`. A healthy liveness response does not imply the dependencies are ready.

Check browser-origin preflight using the exact configured frontend origin:

```powershell
$origin = 'https://frontend.example.com'
$preflight = Invoke-WebRequest -Method Options -Uri 'http://localhost:8000/api/auth/google' -Headers @{
    Origin = $origin
    'Access-Control-Request-Method' = 'POST'
    'Access-Control-Request-Headers' = 'content-type,authorization'
}
if ($preflight.Headers['Access-Control-Allow-Origin'] -ne $origin) {
    throw 'CORS did not allow the configured frontend origin.'
}
```

Replace the example origin with the value in `.env`. Never use a wildcard origin with credentialed browser requests.

## 5. Frontend and post-deploy checks

- Use [FRONTEND_API_GUIDE.md](./FRONTEND_API_GUIDE.md) as the frozen route/auth/request/response reference. Public health endpoints and Google login/refresh are exceptions; other `/api/*` operations require an access token. `GET /api/metrics/summary` additionally requires `X-Admin-Token`.
- Confirm the frontend sends the bearer access token and handles both success and error envelopes.
- Exercise Google sign-in and refresh with the actual production OAuth client in staging before enabling the production frontend.
- Confirm uploads, chat, RAG, study plans, and student-scoped access with a disposable test account; do not use a personal account for release tests.
- Recheck `/health/ready`, `docker compose ps`, and `docker compose logs --tail 200 jarvis-api` after initial traffic.
- Monitor API errors, rate limiting, job execution, and persistent-volume capacity.

## Rollback

Do not use `docker compose down -v` during routine rollback; it deletes persistent data. Roll back to the previous API image only after assessing migration compatibility. The MIS-removal migration is not data-restoring on downgrade; if rollback requires returning to the pre-migration state, restore the verified PostgreSQL, Chroma, and uploads backups using the established restore procedure.
