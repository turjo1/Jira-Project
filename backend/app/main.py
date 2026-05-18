import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestLatencyMiddleware
from app.routers import health, dashboard, auth, teams, developers, jira
from app.websocket import router as ws_router, manager as ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("app.main")
    log.info("app.starting", environment=settings.environment)

    # Initialize Redis pub/sub for WebSocket broadcasting
    log.info("Initializing WebSocket Redis pub/sub")
    redis_task = asyncio.create_task(ws_manager.setup_redis(settings.redis_url))

    try:
        yield
    finally:
        log.info("app.stopping")
        await ws_manager.close_redis()
        if not redis_task.done():
            redis_task.cancel()
            try:
                await redis_task
            except asyncio.CancelledError:
                pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Jira Team Performance Analytics",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLatencyMiddleware)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(teams.router)
    app.include_router(developers.router)
    app.include_router(jira.router)
    app.include_router(ws_router.router)
    return app


app = create_app()
