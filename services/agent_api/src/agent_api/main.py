"""
FastAPI application entry point for agent_api.

Lifespan: MCP pre-warm (background), observability shutdown on exit.
Routes: /v1/chat*, /v1/catalog/*, /v1/sessions/*, /health
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_api.api.agents_router import router as agents_router
from agent_api.api.chat_router import router as chat_router
from agent_api.api.google_calendar_webhook_router import router as gcal_webhook_router
from agent_api.api.routines_router import router as routines_router
from agent_api.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Observability bootstrap
# ---------------------------------------------------------------------------


def _setup_observability(settings) -> None:
    try:
        from blu_observability_bootstrap import bootstrap_observability
        bootstrap_observability(
            service_name=settings.SERVICE_NAME,
            otel_endpoint=getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", None),
        )
        logger.info("Observability bootstrapped")
    except Exception as exc:
        logger.debug("Observability bootstrap skipped: %s", exc)


def _shutdown_observability() -> None:
    try:
        from blu_observability_bootstrap import shutdown_observability
        shutdown_observability()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# MCP pre-warm
# ---------------------------------------------------------------------------


async def _prewarm_mcp() -> None:
    try:
        from agent_api.core.factory import get_mcp_manager
        mcp_mgr = get_mcp_manager()
        await asyncio.wait_for(mcp_mgr.connect(), timeout=30)
        logger.info("[Startup] MCP pre-warmed successfully")
    except Exception as exc:
        logger.warning("[Startup] MCP pre-warm failed (will retry on first request): %s", exc)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _setup_observability(settings)

    # Suppress anyio cross-task cancel-scope RuntimeError that fires during MCP
    # streamablehttp_client teardown when the connection is closed from a different
    # asyncio task than the one that created it. This is a known anyio/MCP SDK
    # issue — the routine output is unaffected.
    loop = asyncio.get_running_loop()
    _prev_handler = loop.get_exception_handler()

    def _exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        if isinstance(exc, RuntimeError) and "cancel scope" in str(exc).lower():
            return
        if _prev_handler is not None:
            _prev_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(_exception_handler)

    # Pre-warm MCP in background — don't block startup
    asyncio.create_task(_prewarm_mcp())

    logger.info("[Startup] %s ready", settings.SERVICE_NAME)
    yield

    loop.set_exception_handler(_prev_handler)
    _shutdown_observability()
    logger.info("[Shutdown] %s stopped", settings.SERVICE_NAME)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    app = FastAPI(
        title="Blu Agent API",
        version="1.0.0",
        description="Unified agent service — supervisor mode + standalone agents",
        lifespan=lifespan,
    )

    # CORS
    raw_origins = os.getenv("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    if not origins or origins == ["*"]:
        # Wildcard mode (dev default): allow all; credentials requires explicit origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            # Also allow any localhost port for dev tooling
            allow_origin_regex=r"http://localhost(:\d+)?",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Routers
    app.include_router(chat_router, prefix="/v1")
    app.include_router(agents_router, prefix="/v1")
    app.include_router(routines_router, prefix="/v1")
    app.include_router(gcal_webhook_router)

    # Health
    @app.get("/health", tags=["infra"])
    async def health():
        return {"status": "ok", "service": settings.SERVICE_NAME}

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent_api.main:app", host="0.0.0.0", port=8000, reload=True)
