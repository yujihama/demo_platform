"""Standalone FastAPI application for the Dify mock server."""

from __future__ import annotations

from fastapi import FastAPI

from .mock.dify import router as dify_mock_router


def create_app() -> FastAPI:
    app = FastAPI(title="Dify Mock Server", version="1.0.0")
    app.include_router(dify_mock_router)
    return app


app = create_app()
