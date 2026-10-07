# Jarvis

AI-Powered Student Academic Assistant

Jarvis is a full-stack AI platform designed to help engineering students manage academics, study materials, attendance, semester planning, previous year papers, and AI-assisted learning from a single workspace.

The platform combines:

- FastAPI
- PostgreSQL
- ChromaDB
- LangChain
- Groq LLMs
- OCR-based PDF Processing
- Retrieval Augmented Generation (RAG)
- Durable Background Workers
- React + TypeScript Frontend

to provide an intelligent academic assistant tailored for students.

---

# Features

## Academic Management

- Subject Management
- Attendance Tracking
- Attendance Prediction
- Academic Profile Management
- Semester Planning
- Study Goal Tracking

---

## AI Study Assistant

- Upload Notes
- Upload Previous Year Papers
- Ask Questions From Notes
- Subject-Specific Retrieval
- AI Generated Study Guidance
- Context-Aware RAG Search

---

## Previous Year Paper Intelligence

Automatically:

- Extracts text
- Detects PYQ patterns
- Builds searchable knowledge
- Supports AI-powered question answering

---

## OCR Support

Supports:

- Normal PDFs
- Scanned PDFs
- Image-based Question Papers
- Mixed PDFs (text + images)

When native text extraction fails:

```text
PDF
 ↓
OCR
 ↓
Text
 ↓
Chunking
 ↓
Embeddings
 ↓
Vector Database
```

---

## Durable Background Processing

Large uploads are processed asynchronously.

Features:

- Persistent job storage
- Worker heartbeats
- Retry mechanism
- Crash recovery
- Safe reprocessing

---

## Authentication

Supports:

### JWT Authentication

- Access Tokens
- Refresh Tokens

### Google OAuth Login

Automatic:

- Account creation
- Academic profile creation
- Preference initialization

---

# System Architecture

```text
                 ┌───────────────┐
                 │ React Frontend│
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ FastAPI API   │
                 └───────┬───────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼

 PostgreSQL       ChromaDB         Background Worker
 (Metadata)      (Embeddings)      (Durable Jobs)

        │                │
        └──────┬─────────┘
               ▼

          Groq LLM
```

---

# Tech Stack

## Backend

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- ChromaDB
- LangChain
- Groq
- PyMuPDF
- PyPDF
- Pytesseract

---

## Frontend

- React
- TypeScript
- React Query
- React Router
- Vite

---

## Infrastructure

- Docker
- Docker Compose

---

# AI Pipeline

## Material Upload

```text
Upload PDF
      ↓
Save File
      ↓
Create Job
      ↓
Worker Picks Job
      ↓
Extract Text
      ↓
OCR Fallback
      ↓
Chunk Text
      ↓
Generate Embeddings
      ↓
Store In ChromaDB
      ↓
Material Ready
```

---

## RAG Query Flow

```text
User Question
      ↓
Embedding Search
      ↓
Retrieve Chunks
      ↓
Context Assembly
      ↓
Groq LLM
      ↓
Answer
```

---

# OCR Pipeline

Jarvis supports scanned PDFs.

If a PDF contains images instead of embedded text:

```text
PyPDF
   ↓
No Text Found
   ↓
PyMuPDF Render
   ↓
Tesseract OCR
   ↓
Recovered Text
```

This enables processing of:

- Question Papers
- Scanned Notes
- Printed Documents
- Mobile Scan PDFs

---

# Safe Reindexing

Jarvis uses generation-based indexing.

```text
Current Index
       ↓

Create New Generation
       ↓

Validate
       ↓

Swap Generation
       ↓

Delete Old Generation
```

Benefits:

- No downtime
- No corrupted search indexes
- Rollback-safe updates

---

# Durable Job System

Unlike FastAPI BackgroundTasks, Jarvis uses database-backed jobs.

### Features

- Persistent queue
- Job retries
- Exponential backoff
- Heartbeats
- Recovery after crashes

Retry Schedule:

```text
Retry 1 → 60 sec
Retry 2 → 120 sec
Retry 3 → 240 sec
```

---

# Database

PostgreSQL stores:

- Users
- Subjects
- Attendance
- Materials
- Study Plans
- Academic Profiles
- Jobs
- Notifications

ChromaDB stores:

- Embeddings
- Chunks
- Search Metadata

---

# Environment Variables

Create:

```env
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=

JWT_SECRET_KEY=
CONNECTOR_ENCRYPTION_KEY=
METRICS_ADMIN_TOKEN=

GOOGLE_CLIENT_ID=
GROQ_API_KEY=

ALLOWED_ORIGINS=
```

---

# Local Development

## Backend

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# Docker Deployment

Build:

```bash
docker compose build
```

Run:

```bash
docker compose up -d
```

Services:

```text
frontend
backend-api
worker
postgres
chromadb
```

---

# Running Worker

The worker is required for:

- PDF Processing
- OCR Processing
- Embedding Generation
- Notifications
- Scheduled Jobs

Worker starts automatically in Docker.

---

# Testing

Backend:

```bash
pytest
```

Frontend:

```bash
npm test
```

Validation:

```bash
ruff check .
```

---

# Security

Implemented:

- JWT Authentication
- OAuth Login
- Input Validation
- File Validation
- Rate Limiting
- Secure Configuration Validation
- CORS Protection
- Dependency Scanning

---

# Production Readiness

Implemented:

- Durable Job Queue
- OCR Support
- Health Monitoring
- Worker Heartbeats
- Safe Reindexing
- Chroma Recovery
- Retry Mechanisms
- Dockerized Deployment
- Alembic Migrations

Recommended before large-scale deployment:

- Managed PostgreSQL
- Object Storage (S3)
- TLS for Database Connections
- Secret Manager
- Automated Backups
- CI/CD Pipeline

---

# Project Status

Current Status:

```text
Backend: Complete
Frontend: Complete
OCR: Complete
RAG: Complete
Authentication: Complete
Deployment: Complete
Production Hardening: Complete
```

---

# License

MIT License

---

# Author

Md Aftab Siddiqui

Jarvis was built to provide engineering students with an AI-powered academic workspace that combines study assistance, academic tracking, intelligent retrieval, and semester planning into a single platform.
