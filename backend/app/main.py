from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import db as dbmod
from app.config import get_settings
from app.errors import http_exception_handler, validation_exception_handler
from app.routers import admin, aids, ask, auth, leaves, me, tasks, todos


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    url = settings.database_url
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    dbmod.init_engine(url, **kwargs)
    dbmod.init_db()
    if dbmod.SessionLocal is not None:
        session = dbmod.SessionLocal()
        try:
            from app.models import User
            from app.seed import seed_demo

            if session.query(User).first() is None:
                seed_demo(session, reset=False)
        finally:
            session.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=get_settings().app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.get("/health")
    def health():
        status = {"api": "ok"}
        settings = get_settings()
        try:
            if dbmod.SessionLocal is None:
                status["postgres"] = "error: not_initialized"
            else:
                session = dbmod.SessionLocal()
                try:
                    session.execute(text("SELECT 1"))
                    status["postgres"] = "ok"
                finally:
                    session.close()
        except Exception as exc:  # noqa: BLE001
            status["postgres"] = f"error: {type(exc).__name__}"
        try:
            if settings.redis_url:
                import redis

                r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=3)
                status["redis"] = "ok" if r.ping() else "fail"
            else:
                status["redis"] = "skipped"
        except Exception as exc:  # noqa: BLE001
            status["redis"] = f"error: {type(exc).__name__}"
        ok = status.get("postgres") == "ok" and status.get("redis") in {"ok", "skipped"}
        return {**status, "ok": ok}

    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(ask.router)
    app.include_router(todos.router)
    app.include_router(leaves.router)
    app.include_router(aids.router)
    app.include_router(tasks.router)
    app.include_router(admin.router)
    return app


app = create_app()
