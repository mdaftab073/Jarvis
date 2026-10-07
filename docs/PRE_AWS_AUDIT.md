# Jarvis — Pre-AWS Architecture & Readiness Audit

> **Document:** `docs/PRE_AWS_AUDIT.md`  
> **Date:** October 4, 2026  
> **Status:** Completed (Phase 1 Baseline Audit)  
> **Scope:** Full repository inspection of backend, frontend, database, worker, security, and infrastructure.

---

## 1. Current Architecture

The Jarvis platform is an AI-powered academic assistant and Student Operating System designed for higher education students. The application currently consists of a decoupled multi-service architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                  │
│   React 18 + TypeScript + Vite SPA (Browser / Mobile Web)             │
│   Configurable API Base: VITE_API_BASE_URL                             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST (Bearer JWT Auth)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Ingress & API Gateway                             │
│   FastAPI (Python 3.12-slim) + Uvicorn ASGI Server                     │
│   - Middleware: SlowAPI (Rate Limiting), RequestTracking (Correlation),│
│     StudentIdentity (JWT Bearer Auth), Envelope (API Contract), CORS  │
└───────┬───────────────────────────┬────────────────────────────┬───────┘
        │                           │                            │
        ▼                           ▼                            ▼
┌──────────────────┐       ┌──────────────────┐        ┌─────────────────┐
│ PostgreSQL 16    │       │ ChromaDB (1.5.9) │        │ Background      │
│ (Relational DB)  │       │ (Vector DB)      │        │ Worker          │
│ - 50 ORM Tables  │       │ - Study material │        │ - JobWorker     │
│ - 28 Migrations  │       │   embeddings     │        │ - Claim & poll  │
│ - Auth & Tokens  │       │ - MiniLM-L6-v2   │        │ - Heartbeats    │
│ - Academic data  │       │ - Persistent vol │        │ - Async tasks   │
└──────────────────┘       └──────────────────┘        └─────────────────┘
        │                           │                            │
        └───────────────────────────┼────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       External Services                                │
│   - Groq Cloud API (Llama 3.3 70B Versatile / Llama 3.1 8B Instant)   │
│   - Google OAuth 2.0 (Identity token cryptographic verification)       │
│   - SVNIT MIS Portal (Session handshake, RSA PKCS#1 v1.5, Captcha)     │
│   - Hugging Face Hub (Pretrained embedding model weights)              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Services & Containers

The system is defined in `docker-compose.yml` with 4 primary container services:

| Container Service | Base Image / Build Target | Role / Execution Command | Dependencies & Health |
|---|---|---|---|
| **`postgres`** | `postgres:16-alpine` | Primary transactional relational database storing students, credentials, courses, plans, chat, logs, and background jobs. | Healthcheck: `pg_isready -U jarvis -d jarvis` (5s interval, 20 retries). |
| **`chroma`** | `chromadb/chroma:1.5.9` | Standalone vector database hosting study material chunks and semantic embeddings (`study_materials` collection). | Healthcheck: TCP socket check on port 8000 (5s interval, 30 retries). |
| **`jarvis-api`** | `./backend/Dockerfile` (`runtime` target) | FastAPI REST application. Executes `alembic upgrade head` on container entrypoint, then starts `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Starts in-process APScheduler. | Depends on `postgres` (healthy) and `chroma` (healthy). Healthcheck: `GET /system/health` asserting `data.overall == 'healthy'`. |
| **`worker`** | `./backend/Dockerfile` (`runtime` target) | Standalone background task worker executing `python -m app.workers.job_worker`. Polls PostgreSQL `job_executions` queue, writes heartbeats to `worker_heartbeats`. | Depends on `postgres` (healthy), `chroma` (healthy), `jarvis-api` (started). |
| **Frontend (Client)** | Node 20 / Vite | React 18 SPA built with Vite. Developed in `frontend/`. In production, compiled static assets (`dist/`) are served via CDN/web server. | Connects to `jarvis-api` over HTTP. |

---

## 3. Network Ports & Ingress

| Service | Internal Container Port | Published Host Port | Exposure / Scope |
|---|---|---|---|
| `postgres` | `5432` | None (Internal) | Isolated to Docker bridge network; accessed only by `jarvis-api` and `worker`. |
| `chroma` | `8000` | None (Internal) | Isolated to Docker bridge network; accessed by `jarvis-api` via `http://chroma:8000`. |
| `jarvis-api` | `8000` | `${JARVIS_PORT:-8000}:8000` | Publicly published entrypoint for API and health endpoints. |
| `worker` | N/A | None | Background process; no open listening ports. |
| `frontend` (Dev) | `5173` | `5173` | Local Vite development server. Production assets served via port 80/443. |

---

## 4. Persistent Data & Storage Inventory

| Storage Resource | Type / Mount Path | Contents & Criticality | Backup / Recovery Strategy |
|---|---|---|---|
| **`postgres_data`** | Named Docker Volume (`/var/lib/postgresql/data`) | **Critical (Stateful):** Student accounts, Google identity, refresh tokens, courses, study plans, chat sessions, background job executions, audit logs. | Daily pg_dump / AWS RDS automated automated snapshot + point-in-time recovery (PITR). |
| **`chroma_data`** | Named Docker Volume (`/chroma/chroma`) | **Stateful:** Vector embeddings and index metadata for RAG retrieval. Can be recomputed from PDFs via `rebuild_embeddings.py` if needed. | Volume snapshot or periodic backup of persistent collection directory. |
| **`uploads_data`** | Named Docker Volume (`/app/uploads`) | **Critical (Stateful):** Uploaded course materials and past exam papers (PDFs). Stored as `uploads/subject_<id>/<uuid>.pdf`. | Object storage migration (AWS S3) with versioning and lifecycle policies. |
| **`model_cache`** | Named Docker Volume (`/opt/huggingface`) | **Cache (Ephemeral):** Downloaded `sentence-transformers/all-MiniLM-L6-v2` weights (~90MB). | Ephemeral; re-downloadable or pre-baked into container image. |
| **`logs/`** | Local Host Directory (`backend/logs`) | Application logs (`jarvis.log`, JSON format). | Shipped to AWS CloudWatch Logs / OpenSearch via log forwarder. |

---

## 5. Required Environment Variables

The backend configuration is managed by `app.core.config.Settings` (Pydantic Settings). In production mode (`ENVIRONMENT=production`), the application strictly validates that production values are present and contain no placeholders.

| Variable Name | Required in Prod | Validated Format / Criteria | Purpose |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `production`, `test`, or `development` | Dictates strict security validations, auth enforcement, and logging. |
| `DATABASE_URL` | Yes | Valid SQLAlchemy PostgreSQL connection string | Primary PostgreSQL connection (e.g. `postgresql+psycopg2://user:pass@host:5432/db`). |
| `POSTGRES_DB` | Yes (Compose) | String (e.g. `jarvis`) | Database name for PostgreSQL container. |
| `POSTGRES_USER` | Yes (Compose) | String (e.g. `jarvis`) | Database user for PostgreSQL container. |
| `POSTGRES_PASSWORD` | Yes (Compose) | High-entropy string | Master password for PostgreSQL database. |
| `GROQ_API_KEY` | Yes | Valid non-empty string | Key for Groq Cloud API LLM model inference. |
| `GOOGLE_CLIENT_ID` | Yes | Non-empty OAuth Client ID | Google Web OAuth 2.0 Client ID for validating Google ID tokens. |
| `JWT_SECRET_KEY` | Yes | $\ge 32$ bytes | High-entropy cryptographic secret for signing HS256 access & refresh tokens. |
| `JWT_ALGORITHM` | No | Defaults to `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Defaults to `15` | Expiration window for access tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | Defaults to `30` | Expiration window for refresh tokens. |
| `CONNECTOR_ENCRYPTION_KEY` | Yes | Valid Fernet URL-safe base64-encoded 32-byte key | Symmetric encryption key for storing connector/session credentials at rest. |
| `METRICS_ADMIN_TOKEN` | Yes | High-entropy string | Bearer/header token for administrative metrics (`/api/metrics/summary`). |
| `ALLOWED_ORIGINS` | Yes | Comma-separated list (No wildcard `*`) | CORS allowed origins (e.g. `https://jarvis.example.com`). |
| `REQUIRE_AUTHENTICATED_STUDENT` | Yes | Must be `true` in production | Enforces that all non-public `/api/*` endpoints require verified student token. |
| `JARVIS_PORT` | No | Defaults to `8000` | Published HTTP port for API container. |
| `CHROMA_HOST` | Yes (Compose) | `chroma` | Hostname for ChromaDB HTTP client. |
| `CHROMA_PORT` | No | Defaults to `8000` | Port for ChromaDB service. |
| `CHROMA_SSL` | No | `false` | TLS flag for Chroma connection. |
| `HF_HOME` | No | `/opt/huggingface` | Cache directory for sentence transformers. |
| `MAX_UPLOAD_SIZE_BYTES` | No | Defaults to `26214400` (25MB) | Maximum file size for PDF uploads. |
| `JOB_RUNNING_TIMEOUT_MINUTES` | No | Defaults to `30` | Stale background job timeout before marking failed. |
| `JOB_POLL_INTERVAL_SECONDS` | No | Defaults to `5` | Background worker polling interval. |
| `WORKER_HEARTBEAT_INTERVAL_SECONDS` | No | Defaults to `15` | Frequency of worker heartbeat records. |
| `VITE_API_BASE_URL` | Yes (Frontend) | Absolute URL (e.g. `https://api.jarvis.example.com`) | Target API base URL for frontend build. |

---

## 6. Authentication & Authorization Flow

The platform implements Google Identity Services + JWT Bearer token authentication:

```
1. Frontend Sign-In
   ┌─────────┐             ┌─────────────────────┐
   │ Student │ ──────────> │ Google Sign-In SDK  │
   └─────────┘             └──────────┬──────────┘
                                      │ Returns Google ID Token (credential)
                                      ▼
2. Token Exchange
   Frontend ────── POST /api/auth/google {"id_token": "..."} ──────> Backend API
                                                                       │
   Backend calls google.oauth2.id_token.verify_oauth2_token() <────────┘
   - Validates audience == GOOGLE_CLIENT_ID
   - Extracts email, name, picture, google_id
   - Upserts Student record, creates StudentAcademicProfile & Preference
   - Generates Access Token (15m, in-memory)
   - Generates Refresh Token (30d, jti stored in auth_refresh_tokens)
   - Emits audit log event
   Backend ◄───── Returns { student, tokens } ─────────────────────────┘

3. Authenticated Requests
   Frontend ────── Request with "Authorization: Bearer <access_token>" ───> API
   - StudentIdentityMiddleware verifies HS256 signature and type="access"
   - Sets request.state.student_id = student.id
   - require_student_scope / require_record_owner asserts student owns resource

4. Token Refresh & Rotation
   Frontend ────── POST /api/auth/refresh {"refresh_token": "..."} ───────> API
   - Verifies refresh token signature and exp
   - Checks auth_refresh_tokens: must exist, not expired, revoked_at is NULL
   - Rotates: revokes old jti, issues new access + refresh token pair
   - If revoked token reused: reject request (replay protection)

5. Logout
   Frontend ────── POST /api/auth/logout {"refresh_token": "..."} ────────> API
   - Sets revoked_at = now() in auth_refresh_tokens
   - Frontend purges access token from memory and refresh token from sessionStorage
```

---

## 7. Frontend $\leftrightarrow$ Backend Communication Contract

- **Transport:** HTTP/1.1 over TLS (HTTPS).
- **Client Implementation:** `frontend/src/api/client.ts` wraps standard `fetch`.
- **Base URL Resolution:**
  ```typescript
  export const API_BASE = (
    (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000"
  ).replace(/\/$/, "");
  ```
- **Envelope Response Contract:** Every JSON API response follows the envelope format defined in `app.api.responses`:
  - **Success (HTTP 200/201):**
    ```json
    {
      "success": true,
      "data": { ... }
    }
    ```
  - **Error (HTTP 4xx/5xx):**
    ```json
    {
      "success": false,
      "error": {
        "code": "error_code_string",
        "message": "Human-readable description"
      }
    }
    ```
- **Auto-Refresh Mechanism:** On receiving `401 unauthorized`, `client.ts` triggers a single-flight mutex refresh call to `/api/auth/refresh`. If successful, the original request is replayed with the new access token. If refresh fails, `onAuthLost` clears session state and navigates to `/login`.

---

## 8. External Dependencies & Third-Party APIs

| Service / Dependency | Usage in Jarvis | Outage Impact & Resilience |
|---|---|---|
| **Groq Cloud API** | Generates study plans, answers RAG questions, drives Academic Director Agent. | API returns HTTP 503 / graceful degradation for AI features; non-AI endpoints (courses, profile, materials, attendance) remain fully functional. |
| **Google OAuth API** | Validates Google ID token signatures during user login. | New logins fail if Google cert endpoints are unreachable. Existing sessions continue until token expiry. |
| **SVNIT MIS Portal** | Ingests student profiles, attendance records, semester grade cards, schedules. | Background job retry with exponential backoff; portal downtime does not impact core Jarvis study features. |
| **Hugging Face Hub** | Downloads `sentence-transformers/all-MiniLM-L6-v2` embedding model. | Only needed on fresh container cold start if volume is unpopulated. Model is cached in persistent `/opt/huggingface`. |

---

## 9. Potential AWS Deployment Concerns

1. **Stateful Vector DB (ChromaDB):**
   - *Concern:* ChromaDB 1.5.9 is run as a single container with a local disk volume (`chroma_data`). AWS ECS tasks are ephemeral; deploying Chroma on ECS without a persistent EBS/EFS mount will cause index loss across task redeployments.
   - *Mitigation for AWS:* Use an AWS EFS persistent mount on ECS Fargate, or migrate to PostgreSQL `pgvector` inside AWS RDS for consolidated database management.
2. **Local File System Uploads:**
   - *Concern:* Uploaded PDFs reside in `/app/uploads` on local storage. In a multi-task ECS deployment, tasks will not share files stored on container storage.
   - *Mitigation for AWS:* Mount an Amazon EFS filesystem across ECS tasks, or update `file_service.py` to upload directly to Amazon S3 with pre-signed URLs.
3. **In-Process Scheduler Concurrency:**
   - *Concern:* `start_scheduler()` in `app/main.py` runs an in-process APScheduler inside the API container. If `jarvis-api` scales to $\ge 2$ ECS tasks behind an ALB, multiple schedulers will run concurrently, queuing duplicate jobs.
   - *Mitigation for AWS:* `BACKGROUND_JOBS_ENABLED=false` on API instances, or rely exclusively on the dedicated `worker` container / Amazon EventBridge scheduler.
4. **Secret Management:**
   - *Concern:* Local deployment relies on `.env` files. Storing production secrets in plain text or committing them is a severe security vulnerability.
   - *Mitigation for AWS:* Inject secrets into ECS task definitions from **AWS Secrets Manager** or **AWS Systems Manager Parameter Store**.
5. **CORS Origin Pinning:**
   - *Concern:* In production, `ALLOWED_ORIGINS` must match the exact CloudFront/S3 domain (e.g. `https://app.jarvis.com`). Mismatches will block all API calls in the browser.
   - *Mitigation for AWS:* Populate CloudFront distribution URL into `ALLOWED_ORIGINS` during infrastructure provisioning.
6. **Sentence Transformers Cold Start:**
   - *Concern:* Container startup downloads PyTorch CPU and transformer model (~90MB) if cache is missing, which could cause healthcheck timeouts.
   - *Mitigation for AWS:* Pre-warm model cache in Docker build or mount persistent EFS volume with `start_period: 120s` in ECS healthcheck.

---

## 10. Recommended Target AWS Architecture

```
                                [ End Users ]
                                      │
                                      ▼
                        [ AWS Route 53 (DNS) ]
                                      │
             ┌────────────────────────┴────────────────────────┐
             │ HTTPS                                           │ HTTPS
             ▼                                                 ▼
[ AWS CloudFront (CDN) ]                            [ Application Load Balancer ]
             │                                                 │
             ▼                                                 ▼
[ S3: Frontend Assets ]                             [ ECS Fargate Cluster ]
  - React 18 SPA (dist/)                              ┌────────────────────────┐
  - index.html, JS, CSS                               │ jarvis-api (1-4 tasks) │
                                                      │ - Port 8000            │
                                                      │ - Health: /health/ready│
                                                      └───────────┬────────────┘
                                                                  │
                                                      ┌───────────┴────────────┐
                                                      │ worker (1 task)        │
                                                      │ - Background jobs      │
                                                      └───────────┬────────────┘
                                                                  │
                     ┌────────────────────────────────────────────┼───────────────────┐
                     ▼                                            ▼                   ▼
        [ AWS RDS PostgreSQL 16 ]                       [ Amazon EFS / S3 ]   [ ChromaDB Task ]
        - Multi-AZ Deployment                           - /app/uploads        - Standalone ECS
        - Encrypted at rest (KMS)                       - /opt/huggingface    - Port 8000
        - Automated Daily Backups + PITR                - PDF Study Materials - Persistent EFS
```

### Resource Mapping Summary:
- **Frontend Hosting:** Amazon S3 (Static Website / Private OAC) + Amazon CloudFront CDN + ACM SSL Certificate.
- **API Routing:** AWS Route 53 $\rightarrow$ AWS Application Load Balancer (ALB) $\rightarrow$ ECS Target Group.
- **Compute:** AWS ECS Fargate running Linux x86_64 containers:
  - `jarvis-api`: Auto-scaled based on CPU/Request count (Min: 2, Max: 6).
  - `worker`: Single continuous task (Min: 1, Max: 2).
  - `chroma`: Single task with persistent Amazon EFS volume.
- **Database:** Amazon RDS PostgreSQL 16 (`db.t4g.medium` or `db.t4g.large`), Multi-AZ, automated backups, encrypted with AWS KMS.
- **Storage:** Amazon S3 bucket for student PDF uploads; Amazon EFS for shared model cache.
- **Security & Secrets:** AWS Secrets Manager for database credentials, JWT secret, Fernet key, Groq API key, Google client ID.
- **Observability:** Amazon CloudWatch Logs (JSON log streams) + CloudWatch Container Insights + Alarm on 5xx error spikes.
