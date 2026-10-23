
from fastapi import FastAPI

from app.db.base import Base
from app.db.session import engine
from app import models
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.audit import router as audit_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.documents import router as documents_router
app = FastAPI(
    title="TrustVault API",
    description="Secure document sharing and leak investigation",
    version="0.3.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(documents_router)
app.include_router(audit_router)
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "Welcome to TrustVault",
        "status": "running",
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "project": "TrustVault",
        "database": "configured",
    }
