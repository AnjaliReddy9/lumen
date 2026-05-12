import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lumen import __version__
from lumen.api.deps import get_settings
from lumen.api.routes import eval as eval_routes
from lumen.api.routes import health, interpret, query
from lumen.api.routes import schema as schema_routes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("starting lumen api %s", __version__)
    yield
    logger.info("shutting down lumen api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Lumen API", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(schema_routes.router)
    app.include_router(interpret.router)
    app.include_router(query.router)
    app.include_router(eval_routes.router)
    return app


app = create_app()
