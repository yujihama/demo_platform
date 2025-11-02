"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .runtime.engine import get_runtime_engine, shutdown_runtime_engine
from .config import config_manager
from .logging import configure_logging, logger


def create_app() -> FastAPI:
    cfg = config_manager.features

    configure_logging(cfg.backend.log_level)

    app = FastAPI(
        title="Demo Platform Generation Backend",
        version="0.1.0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
    )

    app.include_router(router)

    allowed_origins = list({cfg.frontend.base_url, "http://localhost:5173", "http://127.0.0.1:5173"})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:  # noqa: D401 - simple startup hook
        """Initialise directories required by the pipeline."""

        generation = cfg.generation
        for path in [generation.output_root, generation.template_root, Path("mock/previews")]:
            Path(path).mkdir(parents=True, exist_ok=True)

        logger.info("Backend started with mock mode: {provider}", provider=config_manager.llm.provider)
        # Load runtime engine once to validate configuration early
        get_runtime_engine()

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # noqa: D401 - simple shutdown hook
        """Gracefully release engine resources."""

        await shutdown_runtime_engine()

    return app


app = create_app()


