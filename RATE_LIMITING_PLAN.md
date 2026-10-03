# Rate-Limiting Plan

Audit date: 2026-10-03

## Current implementation

- The backend uses SlowAPI with `get_remote_address` as the key function.
- No storage URI/backend is configured, so SlowAPI uses its in-process memory storage.
- Route limits are configured through settings for authentication, refresh, chat, RAG, uploads, connector sync, and alert generation.
- Counters are process-local: restarts clear them, and multiple API workers/instances do not share limits. A caller can therefore receive a larger aggregate allowance when traffic is distributed across instances.

## Recommended Redis migration

Do not introduce Redis automatically as part of this release. When multi-instance production traffic requires shared counters:

1. Select and operate a Redis service with authentication, TLS where appropriate, persistence/availability settings, and network restrictions.
2. Add a dedicated Redis URL setting with a secret-safe deployment path. Keep local/test environments on the existing in-memory backend unless tests specifically exercise Redis.
3. Configure the SlowAPI limiter storage URI from that setting without changing existing per-route thresholds or response envelopes.
4. Confirm proxy/client-IP handling at the deployment edge. Trust forwarded address headers only from known proxy hops; keep client identity stable across instances.
5. Add integration tests for counter sharing across two app instances, expiry windows, backend connection failures, and the existing 429 envelope.
6. Deploy Redis and the API change in staging, compare observed counts and 429s, then roll out gradually with monitoring and a rollback plan.

The current limiter is suitable only for a single process when a global per-client quota is required. Redis is a planned infrastructure change, not part of the current release.
