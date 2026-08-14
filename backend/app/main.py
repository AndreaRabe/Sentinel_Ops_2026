from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.jobs import scheduler
from app.middleware.logging import RequestLoggingMiddleware, configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Sentinel Ops API",
    version="0.1.0",
    # /docs decrit toute la surface d'API, administration comprise : on la
    # coupe entierement (schema OpenAPI inclus) des que DOCS_ENABLED=false.
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Permet au frontend de relire l'identifiant de requete pour le support.
    expose_headers=["X-Request-ID"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def root_health() -> dict:
    return {"status": "ok"}
