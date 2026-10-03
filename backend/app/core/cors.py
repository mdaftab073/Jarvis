from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors_middleware(app: FastAPI, allowed_origins: list[str]) -> None:
    if "*" in allowed_origins:
        raise ValueError("CORS origins must be explicit when credentials are enabled")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Admin-Token",
            "X-Request-ID",
            "X-Correlation-ID",
        ],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )
