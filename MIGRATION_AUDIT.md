# Migration Audit

Audit date: 2026-10-03

## Revision graph

- Base revision: `fa8adcf42dc6`
- Current workspace head: `f0b1c3d5e709`
- Configured local database revision before the requested upgrade: `4c8ef6d1a203`
- Revision count: 25
- Heads: one; no branches or multiple-head conflict.
- The graph is a single linear chain. `alembic heads`, `alembic history --verbose`, and `alembic current` were run.

The first migration verification used a separate, temporary PostgreSQL database. After a verified PostgreSQL custom-format backup was created, the requested upgrade was also applied to the configured local database. The legacy MIS tables and matching connector rows had zero records before migration.

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

## Configured database upgrade

- Pre-upgrade revision: `4c8ef6d1a203`
- Post-upgrade revision: `f0b1c3d5e709` (head)
- `alembic upgrade head` completed successfully, including the MIS-removal and constraint-alignment revisions.
- Before applying the MIS-removal revision, counts were zero for `mis_accounts`, `mis_login_sessions`, `mis_student_profiles`, and `student_connectors` rows with `connector_type='svnit_mis'`.
- A PostgreSQL custom-format backup was created in the persistent session artifact directory before upgrade at `C:\Users\mdaft\.copilot\session-state\304c3431-2b22-49d5-973d-945e97b589a2\files\jarvis-pre-migration-20261003T120532Z.dump` and verified with `pg_restore --list` (596 archive entries; SHA-256 `5bed5e80f42c6cb3092d8f86299f5b86501c78b97e4749fa4e36500a4b031231`). It was also restored successfully into a disposable PostgreSQL database; the restored database reported revision `4c8ef6d1a203`, 54 tables including Alembic's version table, and zero rows in the three legacy MIS tables. The disposable restore database was removed afterward.
- Post-upgrade schema validation confirmed all 50 tables, 146 indexes, 76 foreign keys, 66 check constraints, and 13 unique constraints; no missing/unexpected tables or constraints.

## Risks

1. **MIS data removal:** `e7b4c1d9a260` deletes `student_connectors` rows of type `svnit_mis` and drops `mis_login_sessions`, `mis_accounts`, and `mis_student_profiles`. Its downgrade recreates empty tables; it cannot restore deleted rows. Take and verify a database backup and obtain approval for this removal before upgrading an existing environment.
2. **Production data and staging:** the configured local database upgrade does not substitute for a production-sized rehearsal using a recent restored backup. Review production data and the MIS-removal impact separately.
3. **Backups:** retain the verified pre-upgrade backup; the downgrade cannot restore deleted MIS data.

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

The complete downgrade-to-base/upgrade-to-head cycle was verified only on the disposable audit database. The configured database was upgraded forward to head; it was not downgraded.
