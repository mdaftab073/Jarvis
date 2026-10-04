# Jarvis

Jarvis is a FastAPI academic assistant combining subject-aware retrieval, PYQ intelligence, study planning, learning analytics, student memory, semester tracking, and a modular multi-agent Director.

## Background job architecture

Uploads and other registered background tasks are written to PostgreSQL and processed by the independent worker. A worker restart recovers pending jobs and requeues interrupted work after its heartbeat becomes stale.

```text
Frontend
   ↓
FastAPI API
   ↓
PostgreSQL Job Queue
   ↓
Worker
   ↓
PDF/OCR/Chunking
   ↓
Embeddings
   ↓
Chroma
```

## Quick Start

The Docker Compose stack runs PostgreSQL, Chroma, the API, and the durable worker. Configure a Groq key and a strong PostgreSQL password once:

```powershell
Copy-Item .env.example .env
# Edit .env, then:
docker compose up -d
```

The API is available at `http://localhost:8000`; interactive OpenAPI docs are at `http://localhost:8000/docs`. Compose applies Alembic migrations before starting Uvicorn. See [DOCKER_SETUP.md](DOCKER_SETUP.md) for setup and operational details.

For local development, configure `DATABASE_URL`, `GROQ_API_KEY`, and `CHROMA_HOST`, install the backend dependencies, and start PostgreSQL and Chroma:

```powershell
docker compose up -d postgres chroma
Set-Location backend
python -m pip install -r requirements-dev.txt
alembic upgrade head
```

Then run the API and worker in separate terminals from `backend/`:

```powershell
uvicorn app.main:app --reload
```

```powershell
python -m app.workers.job_worker
```

The worker uses the same environment and database as the API.

Scanned PDFs use OCR during processing. Local development requires Tesseract OCR and its English language data installed and available in `PATH`. Docker deployment installs `tesseract-ocr` and `tesseract-ocr-eng` automatically; no container-side manual setup is required.

## Rebuilding RAG embeddings

To rebuild the vector and keyword indexes from stored study materials, start PostgreSQL and Chroma, then run from `backend/`:

```powershell
python scripts/rebuild_embeddings.py
```

The script processes every stored material using the normal PDF/OCR pipeline, reports failures, and removes orphaned or inactive Chroma chunks only after all materials rebuild successfully. It can be rerun safely; configure the same database and Chroma environment as the API.

Subject selection is shared state used by student workflows, so it remains available on Dashboard, Courses, Planner, and Materials after removal from the global navbar.

## Validation

Run the offline test pyramid from `backend/`:

```powershell
python -m unittest discover -s tests
```

Run the live dependency/schema check after PostgreSQL and Chroma are available:

```powershell
python scripts/validate_system.py
```

Run the realistic academic workflow (real PDF extraction, local embeddings, Chroma, and hybrid retrieval; Groq prose is mocked):

```powershell
python scripts/run_release_e2e.py
```

The runner writes [END_TO_END_REPORT.md](END_TO_END_REPORT.md). The latest schema audit is in [VALIDATION_REPORT_v1.0.md](VALIDATION_REPORT_v1.0.md).

## Documentation

- [Frontend API guide](FRONTEND_API_GUIDE.md)
- [Deployment checklist](DEPLOYMENT_CHECKLIST.md)
- [Backend freeze report](BACKEND_FREEZE_REPORT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API summary](docs/API_SUMMARY.md)
- [Release notes](RELEASE_NOTES_v1.0.md)
- [Release candidate checklist](RELEASE_CANDIDATE_v1.0.md)
- [Environment template](.env.example)