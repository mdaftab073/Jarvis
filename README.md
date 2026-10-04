# Jarvis

Jarvis is a FastAPI academic assistant combining subject-aware retrieval, PYQ intelligence, study planning, learning analytics, student memory, semester tracking, and a modular multi-agent Director.

## Quick Start

The Docker Compose stack runs PostgreSQL, Chroma, and the API. Configure a Groq key and a strong PostgreSQL password once:

```powershell
Copy-Item .env.example .env
# Edit .env, then:
docker compose up -d
```

The API is available at `http://localhost:8000`; interactive OpenAPI docs are at `http://localhost:8000/docs`. Compose applies Alembic migrations before starting Uvicorn. See [DOCKER_SETUP.md](DOCKER_SETUP.md) for setup and operational details.

For local development, install `backend/requirements-dev.txt`, set `DATABASE_URL` and `GROQ_API_KEY`, then from `backend/` run:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Scanned PDFs use OCR during processing. Local development requires Tesseract OCR and its English language data installed and available in `PATH`. Docker deployment installs `tesseract-ocr` and `tesseract-ocr-eng` automatically; no container-side manual setup is required.

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