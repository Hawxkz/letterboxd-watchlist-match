import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.core.config  # Ensures .env is loaded

# Default allowed development origins
DEFAULT_ALLOWED_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

# Permitted HTTP methods (principle of least privilege)
ALLOWED_METHODS: List[str] = ["GET", "POST", "OPTIONS"]

# Permitted HTTP headers
ALLOWED_HEADERS: List[str] = [
    "Content-Type",
    "Accept",
    "Authorization",
    "X-Requested-With",
]


def get_allowed_origins() -> List[str]:
    """Reads allowed CORS origins from CORS_ALLOWED_ORIGINS (comma-separated) or falls back to defaults."""
    env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if not env_origins:
        return DEFAULT_ALLOWED_ORIGINS

    parsed = [o.strip() for o in env_origins.split(",") if o.strip()]
    return parsed if parsed else DEFAULT_ALLOWED_ORIGINS


def setup_cors(app: FastAPI) -> None:
    """
    Configures hardened CORS middleware on the FastAPI application.
    Strictly restricts origins, methods, and headers to those required.
    """
    origins = get_allowed_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )
