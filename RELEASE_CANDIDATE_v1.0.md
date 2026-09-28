# Jarvis v1.0 Release Candidate Checklist

## Git Release Checklist

- [x] Tests passing: recursive `unittest` suite passes.
- [x] Validation passing: database, migration, tables, indexes, foreign keys, Chroma, registry, and API routes verified.
- [x] E2E passing: realistic upload-to-Director workflow passed; see [END_TO_END_REPORT.md](END_TO_END_REPORT.md).
- [x] Documentation complete: setup, architecture, API, release notes, validation, and known limitations documented.

## Deployment Gate

- [x] PostgreSQL migrated to `f2c8a4d1b709`.
- [x] `/system/health` reports configured local dependencies healthy.
- [x] Docker Compose configuration parses.
- [x] Verify `docker build` and `docker compose up -d` on the release host.
- [ ] Configure secrets and authenticated access at the deployment boundary.
- [ ] Exercise backup/restore and retention for PostgreSQL, Chroma, uploads, and model cache.

Candidate is ready for deployment work, not a production-ready security sign-off. Authentication remains a known limitation.