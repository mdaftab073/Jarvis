# Jarvis Deployment Validation Report

Generated from the current deployment validator run. A failed or unavailable check is not a production sign-off.

## Environment Status
| Check | Status | Detail |
|---|---|---|
| Environment | FAIL | GOOGLE_CLIENT_ID; JWT_SECRET_KEY; METRICS_ADMIN_TOKEN; REQUIRE_AUTHENTICATED_STUDENT must be true; JWT_SECRET_KEY must contain at least 32 bytes |
| Storage | PASS | writable |

## Migration Status
| Check | Status | Detail |
|---|---|---|
| Migrations | PASS | {"current_revisions": ["b9d72e4c1a63"], "latest_heads": ["b9d72e4c1a63"], "status": "up_to_date"} |

## Health Status
| Check | Status | Detail |
|---|---|---|
| Health Live | FAIL | URLError: endpoint unavailable or returned invalid health data |
| Health Ready | FAIL | URLError: endpoint unavailable or returned invalid health data |
| Health Dependencies | FAIL | URLError: endpoint unavailable or returned invalid health data |
| Health | FAIL | URLError: endpoint unavailable or returned invalid health data |
| System Health | FAIL | URLError: endpoint unavailable or returned invalid health data |

## Authentication Status
| Check | Status | Detail |
|---|---|---|
| Authentication | FAIL | REQUIRE_AUTHENTICATED_STUDENT must be true |
| Health Ready | FAIL | URLError: endpoint unavailable or returned invalid health data |

## Scheduler, Jobs, and Metrics
| Check | Status | Detail |
|---|---|---|
| Scheduler | PASS | registered |
| Job Registry | PASS | 7 unique jobs |
| Metrics | PASS | collector operational |
| Audit Logging | PASS | audit_logs table present |
| Tool Registry | PASS | 32 unique tools |

## Known Risks
- Google login requires a live Google-issued ID token and a configured OAuth client ID; the validator checks configuration, not Google user credentials.
- Docker startup, end-to-end workflows, and concurrency checks must be run against the target deployment before release.

## Recommendations
- Resolve every failed check, apply migrations, and rerun this validator against the deployed health URL.
- Run the authenticated E2E and load validation scripts with a short-lived test student token in staging.
