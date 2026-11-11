from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from . import models
from .config import settings
from .db import Base, SessionLocal, engine
from .routers import auth, catalog, deliveries, lots
from .security import hash_secret


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # Alembic fica para a etapa seguinte
    with SessionLocal() as db:
        if not db.scalar(select(func.count()).select_from(models.User).where(models.User.role == "admin")):
            db.add(models.User(name="Administrador", email=settings.admin_email.lower(), role="admin",
                               password_hash=hash_secret(settings.admin_password)))
            db.commit()
    yield


app = FastAPI(title="BIO-AGRO API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return {"status": "ok", "database": "ok"}


for r in (auth.router, catalog.router, lots.router, deliveries.router):
    app.include_router(r)
