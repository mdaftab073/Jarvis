# Migration Audit

Audit date: 2026-10-03

## Revision graph

- Base revision: `fa8adcf42dc6`
- Current workspace head: `f0b1c3d5e709`
- Configured local database revision observed during audit: `4c8ef6d1a203`
- Revision count: 25
- Heads: one; no branches or multiple-head conflict.
- The graph is a single linear chain. `alembic heads`, `alembic history --verbose`, and `alembic current` were run.

The current local database is intentionally not upgraded by this audit. It contains the three legacy MIS tables that the next release migration drops, so the migration was exercised against a separate, temporary PostgreSQL database instead.

## Fresh schema verification

An isolated empty PostgreSQL database was created and removed after validation. `alembic upgrade head` succeeded; `alembic downgrade base` followed by `alembic upgrade head` also succeeded.

After upgrade, the schema matched the registered ORM metadata:

| Check | Result |
|---|---:|
| ORM tables | 50 / 50 present |
| Explicit ORM indexes | 146 / 146 satisfied, including equivalent primary-key indexes |
| Foreign keys | 76 / 76 present |
| Check constraints | 66 / 66 present |
| Unique constraints | 13 / 13 present |
| Missing or unexpected ORM tables | 0 |

The audit initially found 15 ORM-declared check constraints missing from the migrations. Revision `f0b1c3d5e709` adds them. Before adding these constraints, read-only checks against the configured database found zero violating rows for all 15 predicates and no duplicate academic-profile student IDs.

## Risks

1. **MIS data removal:** `e7b4c1d9a260` deletes `student_connectors` rows of type `svnit_mis` and drops `mis_login_sessions`, `mis_accounts`, and `mis_student_profiles`. Its downgrade recreates empty tables; it cannot restore deleted rows. Take and verify a database backup and obtain approval for this removal before upgrading an existing environment.
2. **Existing database not at head:** the configured local database is currently at `4c8ef6d1a203`; the audit did not apply destructive migrations to it. A production database must be reviewed separately before release.
3. **Backups and staging:** a successful disposable-database migration is not a substitute for a production-sized rehearsal using a recent restored backup.

## Upgrade procedure

1. Take and verify a PostgreSQL backup, and back up Chroma and uploads. Review the MIS-removal impact before proceeding.
2. Set `DATABASE_URL` to the intended target database and provide the required application environment.
3. From `backend/`, inspect `alembic current` and `alembic heads`.
4. Run `alembic upgrade head`.
5. Confirm the revision is `f0b1c3d5e709` with `alembic current`, then verify `/health/ready` and the migration/schema checks.

Compose runs `alembic upgrade head` before Uvicorn. Do not point a deployment at an unintended database.

## Rollback procedure

1. Stop API writers and take a fresh backup before rollback.
2. For a rollback that retains schema/data, select a known target revision and run `alembic downgrade <revision>` from `backend/`.
3. The newest constraint-alignment revision can be downgraded to `e7b4c1d9a260`. Downgrading past the MIS-removal revision only recreates empty MIS tables; it does not restore deleted rows.
4. For data recovery, restore the verified pre-upgrade database backup rather than relying on Alembic downgrade.

The complete downgrade-to-base/upgrade-to-head cycle was verified only on the disposable audit database.
