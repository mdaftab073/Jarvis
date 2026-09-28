# Jarvis v1.0 Release Candidate Notes

## Features by Phase

- Phases 1–8: FastAPI foundation, student/course/subject/material data, PDF extraction, embeddings, subject-aware RAG, hybrid vector/BM25 retrieval, PYQ intelligence, practice generation, study planning, and learning analytics/readiness.
- Phase 9: Academic workflow goal classification, existing-service orchestration, and unified strategies.
- Phase 10: Persistent student profiles, memories, readiness history, automatic topic/readiness capture, and profile APIs.
- Phase 11: Semesters, subject targets, milestones, weekly reviews, weighted health, risk detection, and semester copilot guidance.
- Phase 12: Director Agent, six specialists, registry, failure-isolated aggregation, health checks, pre-production validation, and unit/integration/E2E/regression/API/database/performance test groups.
- Phases 12.1–12.4: Migrated and audited PostgreSQL schema, realistic live E2E report, release documentation, Docker/Compose foundation, and GitHub Actions CI.

## Architecture

FastAPI routes call SQLAlchemy/Alembic-backed services. A deterministic Director selects and orders specialized agents for analytics, study planning, PYQ, retrieval, memory, and semester health. PostgreSQL stores academic state; Chroma stores vectors; SQLite-backed BM25 provides keyword retrieval; Groq generates answer and strategy prose. See [Architecture](docs/ARCHITECTURE.md) and [API summary](docs/API_SUMMARY.md).

## Verification

- Automated tests: 90 tests; rerun `python -m unittest discover -s tests` from `backend/` for the authoritative count.
- Multi-agent package coverage: 94% measured with Coverage.py.
- Live E2E: [END_TO_END_REPORT.md](END_TO_END_REPORT.md); actual PDF extraction, embeddings, Chroma, BM25, database, analytics, planning, memory, semester, and agent APIs; Groq prose/classification mocked.
- Database revision: `f2c8a4d1b709`; 16 application tables; required indexes/FKs present; no orphaned references.
- Validation: `scripts/validate_system.py` passes against the configured local PostgreSQL and Chroma services.
- Load smoke: 100 mocked in-process requests each to RAG, the workflow agent, and Director; zero failures. These measurements are not a production capacity benchmark.

## Known Limitations

- Authentication and authorization are not implemented. Use an authenticated gateway and restrict student-data access.
- Director agents run sequentially; there is no retry queue or distributed orchestration.
- Groq generation is mocked in automated CI/E2E. Runtime requires provider availability, credentials, network connectivity, and quota.
- Readiness and semester health are product heuristics, not accredited grade or CGPA predictions.
- CI builds the Docker image; target-environment Compose startup and operational recovery still require release-host verification.
- BM25 uses a single-host SQLite index, not a distributed multi-writer search service.

## Roadmap

Authentication and consent; background jobs and retry policies; provider abstraction and spend limits; metrics/tracing; shared keyword indexing; backup/restore drills; and production-scale load testing.