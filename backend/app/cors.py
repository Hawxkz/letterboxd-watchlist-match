import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.config  # Ensures .env / tmdb.env are loaded

# Default origins for local development
DEFAULT_ALLOWED_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

# Explicit HTTP methods permitted by the API (principle of least privilege)
ALLOWED_METHODS: List[str] = ["GET", "POST", "OPTIONS"]

# Explicit HTTP headers permitted by the API
ALLOWED_HEADERS: List[str] = [
    "Content-Type",
    "Accept",
    "Authorization",
    "X-Requested-With",
]


def get_allowed_origins() -> List[str]:
    """
    Retrieves allowed CORS origins from environment variable CORS_ALLOWED_ORIGINS
    (comma-separated), falling back to default local dev URLs.
    """
    env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if not env_origins:
        return DEFAULT_ALLOWED_ORIGINS

    parsed = [o.strip() for o in env_origins.split(",") if o.strip()]
    return parsed if parsed else DEFAULT_ALLOWED_ORIGINS


def setup_cors(app: FastAPI) -> None:
    """
    Configures and adds hardened CORS middleware to the FastAPI application.
    Enforces strict origins, methods, and headers.
    """
    origins = get_allowed_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )
