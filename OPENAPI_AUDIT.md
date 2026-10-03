# OpenAPI Audit

Audit date: 2026-10-03

## Generated contract

The schema was generated from the running FastAPI application in the configured test environment.

| Check | Result |
|---|---:|
| OpenAPI version | 3.1.0 |
| Paths | 133 |
| Operations | 159 |
| Component schemas | 160 |
| Operations with a documented success response | 159 / 159 |
| Operations with a standard success envelope | 159 / 159 |
| Operations without a summary or description | 0 |
| Duplicate method/path pairs | 0 |
| Operations without query/path/body input | 17 (no-input operations) |

All request bodies, path/query parameters, response component references, and the shared error responses are represented in `/openapi.json`. Operations that take no input correctly have no request schema.

## Authentication documentation gap

Authentication is enforced by middleware, but the generated schema has no `securitySchemes` declaration and none of its operations has an OpenAPI `security` requirement. The generated [frontend API reference](./docs/FRONTEND_API_REFERENCE.md) lists access-token requirements from the middleware exceptions, but generated clients and schema-only consumers cannot discover them automatically. This audit documents the existing contract and does not change API behavior or add a new security scheme.

## Response schema limitation

The standard success and error envelope shapes are present. However, 92 operations use an unconstrained `Any` payload for `data`; their inner success payloads are not a frozen, machine-validated DTO. Consumers should treat those payload shapes as provisional and confirm them with endpoint examples before relying on generated types.

## Artifacts

- Full operation-by-operation request, authentication, success-response, and common-error reference: [docs/FRONTEND_API_REFERENCE.md](./docs/FRONTEND_API_REFERENCE.md)
- Compact inventory: [docs/API_INVENTORY.md](./docs/API_INVENTORY.md)
- Regenerate both files from the backend with `python scripts/generate_api_inventory.py`.
