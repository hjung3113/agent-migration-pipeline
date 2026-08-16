from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="agent-migration target backend")
    register_exception_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
