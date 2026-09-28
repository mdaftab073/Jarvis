# Docker Setup

## Prerequisites

- Docker Desktop with the Linux container engine enabled.
- A Groq API key.
- Disk space for the CPU PyTorch/SentenceTransformer runtime and cached model.

## Start

Create a local environment file once and set real credentials:

```powershell
Copy-Item .env.example .env
```

Then run:

```powershell
docker compose up -d
```

For an explicit rebuild use `docker compose up -d --build`. Compose waits for PostgreSQL and Chroma, applies Alembic migrations, then starts Uvicorn. PostgreSQL, Chroma, uploads, and the Hugging Face cache persist in named volumes. The API uses the Chroma HTTP client in Compose and local persistent Chroma outside it.

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/system/health
```

Swagger UI: `http://localhost:8000/docs`.

## Environment

| Variable | Required | Meaning |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key; automated tests mock model calls |
| `POSTGRES_DB` | No | Database name; defaults to `jarvis` |
| `POSTGRES_USER` | No | Database role; defaults to `jarvis` |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `JARVIS_PORT` | No | Published API port; defaults to `8000` |
| `DATABASE_URL` | Runtime | SQLAlchemy PostgreSQL connection URL |
| `CHROMA_HOST` | Runtime | Chroma host; Compose sets `chroma` |
| `CHROMA_PORT` | Runtime | Chroma HTTP port; defaults to `8000` |
| `CHROMA_SSL` | Runtime | TLS toggle for Chroma; defaults to `false` |
| `HF_HOME` | Runtime | Model cache directory; Compose persists `/opt/huggingface` |

`.env.example` contains placeholders only. Never commit `.env`; rotate credentials before external deployment.

## Operations

```powershell
docker compose logs -f jarvis-api
docker compose down
```

`docker compose down` preserves data. Use `docker compose down -v` only when intentionally deleting local database, vector, upload, and model-cache volumes.

The image uses Python 3.12 slim, CPU PyTorch, no pip cache, a non-root runtime user, and a Docker ignore file that excludes local databases, virtual environments, models, uploads, and tests. CI builds the API image. Verify build and Compose startup on the target Docker host before release.