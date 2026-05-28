from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import geo_runs, health, merchants, prompts, reports
from app.core.arq import create_arq_pool
from app.core.config import settings
from app.core.logging import TraceIdMiddleware, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("DEBUG" if settings.debug else "INFO")
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.env)
    app.state.arq = await create_arq_pool()
    try:
        yield
    finally:
        await app.state.arq.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(TraceIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(merchants.router, prefix=settings.api_prefix)
    app.include_router(prompts.router, prefix=settings.api_prefix)
    app.include_router(geo_runs.router, prefix=settings.api_prefix)
    app.include_router(reports.router, prefix=settings.api_prefix)
    return app


app = create_app()
