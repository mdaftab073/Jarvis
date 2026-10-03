# Healthcheck Audit

Audit date: 2026-10-03

## Endpoints and checks

- `GET /health/live` reports process liveness.
- `GET /health/ready`, `/health/dependencies`, and `/health` check PostgreSQL (`SELECT 1`), Chroma collection access/count, scheduler state, tool registry uniqueness, migration state, metrics collector, audit-log table presence, and authentication configuration. Readiness endpoints return HTTP 503 when a required check is not `ok`.
- `GET /system/health` additionally reports configured Groq credentials, migration state, registered agents, and uptime. It can return a healthy HTTP response with `overall: degraded`; callers must inspect the payload.
- The system router registers `/system/health`, not `/system/readiness`. Use `/health/ready` for deployment readiness.
- API health response bodies use the standard success envelope. Failures use the standard error envelope.
- Compose's API healthcheck calls `/system/health` and explicitly requires `success == true` and `data.overall == "healthy"`.

The dependency checks are synchronous and include database inspection and a Chroma count on each call. The schema validator recognizes equivalent database indexes by indexed columns, including indexes supplied by primary-key constraints. These checks are appropriate for readiness/audit use but should not be polled at high frequency.

## Startup readiness

Production configuration validates required credentials before serving. Production startup now checks PostgreSQL connectivity and initializes/accesses the Chroma collection; failures are logged and raised as dependency-specific startup errors. Compose also waits for database and Chroma healthchecks before starting the API. Non-production startup does not hard-fail on those external checks, while health/readiness endpoints still expose dependency status.

The application does not perform a live Google OAuth round trip at startup; it validates required OAuth configuration and lets the login operation validate provider tokens when called.

## Recommendations

1. Keep liveness lightweight and use `/health/ready` for orchestrator readiness where the orchestrator supports it.
2. Consider caching or throttling deep checks if an external monitor polls them more frequently than once per 15 seconds.
3. Retain the current application-level Chroma check; the Compose Chroma TCP check alone does not prove collection readiness.
4. Monitor dependency failures and readiness transitions without exposing secrets or connection strings.
