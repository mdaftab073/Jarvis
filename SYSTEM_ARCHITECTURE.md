# System Architecture

## Components

- **FastAPI:** routing, request/response envelopes, CORS, rate limiting, request tracking, and OpenAPI.
- **Authentication:** Google OAuth ID-token validation issues JWT access/refresh tokens. Middleware validates bearer access tokens and places the authenticated student identity on the request.
- **PostgreSQL:** relational source of truth for accounts, academic records, study artifacts, plans, goals, chat, audit events, and job execution.
- **ChromaDB:** persistent vector collection used for study-material retrieval. Keyword/BM25 index data is synchronized from Chroma during application startup.
- **Agent layer:** the director coordinates specialized agents and registered tools through service modules.
- **Analytics layer:** analytics services and agents derive dashboards, readiness, topic mastery, recommendations, and learning insights from stored student activity.
- **Background jobs:** APScheduler runs registered reminder and analytics work and records executions in PostgreSQL.
- **External services:** Groq provides model inference; Google validates OAuth identity tokens.

## Context diagram

```mermaid
flowchart LR
    Browser[Frontend client] -->|HTTPS / JSON| API[FastAPI backend]
    API --> Auth[JWT / Google OAuth]
    API --> Agents[Agent director and tools]
    Agents --> Services[Domain services]
    Services --> PG[(PostgreSQL)]
    Services --> Chroma[(ChromaDB vectors)]
    Agents --> Groq[Groq inference API]
    Auth --> Google[Google OAuth token verification]
```

## Request and data flow

```mermaid
sequenceDiagram
    participant Client as Frontend
    participant API as FastAPI middleware/routes
    participant Auth as Auth service
    participant Agent as Agent and service layer
    participant DB as PostgreSQL
    participant Vector as ChromaDB

    Client->>API: Request with bearer token
    API->>Auth: Validate access token and resolve student
    Auth->>DB: Read identity / token state
    DB-->>Auth: Authenticated student
    API->>Agent: Execute authorized operation
    Agent->>DB: Read/write domain state
    Agent->>Vector: Retrieve relevant study content (when needed)
    DB-->>Agent: Domain records
    Vector-->>Agent: Relevant chunks
    Agent-->>API: Typed or service payload
    API-->>Client: Standard success envelope
```

## Deployment topology

```mermaid
flowchart TB
    subgraph Compose[Docker Compose deployment]
        API[Jarvis API container\nnon-root, port 8000]
        PG[(PostgreSQL 16\npersistent volume)]
        CH[(ChromaDB\npersistent volume)]
        UP[(Uploads volume)]
        HF[(Model cache volume)]
        API --> PG
        API --> CH
        API --> UP
        API --> HF
    end
    Client[Browser] --> API
    API --> Google[Google OAuth]
    API --> Groq[Groq API]
```

## Trust boundaries

Browser traffic crosses the configured CORS allowlist. Protected `/api/*` routes require a bearer access token except documented public auth and health operations. Student ownership is based on the identity resolved from the token, not a client-supplied student identifier. PostgreSQL and ChromaDB are internal dependencies; production secrets are provided through the deployment environment.
