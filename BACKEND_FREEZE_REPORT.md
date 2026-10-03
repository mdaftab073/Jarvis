# Backend Freeze Report

Audit date: 2026-10-03

## Contract and schema

- **159 API operations** across **133 OpenAPI paths**; OpenAPI 3.1.0.
- **160** generated component schemas; every operation has a documented success response and the standard success envelope.
- **50 SQLAlchemy ORM tables** represented by the fresh migration schema.
- OpenAPI does not declare a bearer security scheme. Authentication requirements are listed in the generated frontend reference.
- **92 operations** use `Any` for the inner success `data` payload, so those inner payloads are not schema-frozen.
- The latest migration head is `f0b1c3d5e709`, with one linear head and 25 revisions.

## Validation results

- **211 tests passed** across 35 test modules using the repository's test settings (`ENVIRONMENT=test`, `REQUIRE_AUTHENTICATED_STUDENT=false`).
- Ruff passed: `ruff check app scripts tests`.
- Pylance reported no errors in the changed Python files.
- An isolated empty PostgreSQL database upgraded to head, matched all 50 ORM tables, and passed a full downgrade-to-base/re-upgrade cycle.
- Schema checks verified 146 ORM indexes, 76 foreign keys, 66 check constraints, and 13 unique constraints.
- Production Compose configuration parsed with non-production placeholder values. The checked-in local environment did not provide every required Compose setting.
- The 2.49 GB Docker image built successfully; an isolated Compose deployment reached healthy on PostgreSQL, ChromaDB, and API containers.

## Migration and data risk

The configured local database was backed up and upgraded from `4c8ef6d1a203` to `f0b1c3d5e709`; targeted legacy MIS tables/connector rows were empty. Production databases still require their own backup and data review because the MIS-removal downgrade cannot restore deleted data. See [MIGRATION_AUDIT.md](./MIGRATION_AUDIT.md).
The pre-upgrade backup was restored into a disposable database and verified at revision `4c8ef6d1a203`; the temporary restore database was removed.

## Dependency summary

- Runtime: Python 3.12, FastAPI/Uvicorn, SQLAlchemy/Alembic, PostgreSQL with psycopg2, and ChromaDB.
- AI/retrieval: Groq client, Sentence Transformers/CPU PyTorch, BM25 keyword search, and PDF parsing.
- Authentication/security: Google OAuth token verification, PyJWT, cryptography/Fernet, and SlowAPI.
- Background work: APScheduler.
- Compose provisions PostgreSQL and ChromaDB; Groq and Google remain external providers. Dependency ranges are declared in `backend/requirements.txt`; `pip check` reported no broken installed requirements.

## Technical debt and follow-up

| Priority | Item | Follow-up |
|---|---|---|
| Release gate | Existing databases require review/backups before the destructive MIS-removal migration. | Rehearse upgrade and rollback on a recent restored staging backup. |
| Release gate | A clean Compose deployment was verified with placeholder credentials; staging authentication was not exercised. | Repeat with real staging configuration and exercise Google OAuth/CORS. |
| Recommended | 92 operations have unconstrained `Any` response data. | Add explicit response models incrementally without changing current envelope behavior. |
| Recommended | OpenAPI auth metadata is absent although middleware requires authentication. | Add a bearer security scheme and explicit public-operation declarations in a separately reviewed contract change. |
| Recommended | Rate limiting is in-memory and per process. | Follow [RATE_LIMITING_PLAN.md](./RATE_LIMITING_PLAN.md) before multi-instance production traffic. |
| Recommended | Compose-specific backup/restore is not automated by the host scripts. | Define and test coordinated PostgreSQL, Chroma, and uploads volume backups. |
| Optional | FastAPI publishes `0.1.0` while settings contain `VERSION=1.0.0`. | Decide and align the public version source of truth. |

## Future roadmap

1. Add strongly typed response models for the 92 `Any` operations, without changing existing runtime response envelopes.
2. Add machine-readable bearer auth metadata to OpenAPI with a reviewed public-route exception list.
3. Introduce shared Redis-backed rate limiting if multi-instance deployment becomes necessary.
4. Automate and rehearse coordinated PostgreSQL, Chroma, and uploads backups/restores for Compose and production infrastructure.
5. Add CI/staging coverage for image builds, fresh Compose startup, migration from a representative backup, OAuth, CORS, and readiness.

## Readiness scores

These scores are qualitative audit estimates, not automated measurements.

- **Backend readiness: 90/100.** The contract, tests, lint, fresh migration, schema parity, and production startup dependency checks were verified. Remaining points reflect migration-data risk and OpenAPI typing/auth metadata.
- **Frontend readiness: 82/100.** A full operation reference is available, but 92 payloads are unconstrained and OpenAPI does not encode auth requirements.
- **Production readiness: 80/100.** The configured database has been backed up, migrated, and schema-verified; the backup restored successfully to a disposable database; a fresh Compose deployment reached healthy on all services. Staging OAuth, CORS, and production-scale restore behavior remain to be verified.

## Release decision

The backend API is documented for frontend integration. Production deployment is **not signed off** until the MIS-removal impact is reviewed for each target environment, a restored staging database is migrated, and the Compose image is built and exercised with real staging configuration.
