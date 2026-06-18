from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import time
import os

# حذفنا سطر sys.path المسبب للمشاكل، بايثون سيجد المكتبات تلقائياً من الـ venv
from app.core.config import settings
from app.db.database import engine, Base
from app.api.v1.endpoints import (
    auth, products, categories, cart, orders, 
    payments, admin, wishlist, addresses
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: إنشاء الجداول والمجلدات
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "products"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "categories"), exist_ok=True)

    # إنشاء Admin افتراضي
    from app.db.database import SessionLocal
    from app.models.models import User, UserRole
    from app.core.security import get_password_hash
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == settings.FIRST_ADMIN_EMAIL).first()
        if not admin_user:
            admin_user = User(
                email=settings.FIRST_ADMIN_EMAIL,
                full_name="Super Admin",
                hashed_password=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
                role=UserRole.super_admin,
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"✅ Admin created: {settings.FIRST_ADMIN_EMAIL}")
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routers
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX, tags=["auth"])
app.include_router(products.router, prefix=API_PREFIX, tags=["products"])
app.include_router(categories.router, prefix=API_PREFIX, tags=["categories"])
app.include_router(cart.router, prefix=API_PREFIX, tags=["cart"])
app.include_router(orders.router, prefix=API_PREFIX, tags=["orders"])
app.include_router(payments.router, prefix=API_PREFIX, tags=["payments"])
app.include_router(wishlist.router, prefix=API_PREFIX, tags=["wishlist"])
app.include_router(admin.router, prefix=API_PREFIX, tags=["admin"])
app.include_router(addresses.router, prefix=API_PREFIX, tags=["addresses"])
# ─── Health Check ─────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"أهلاً بيك في {settings.APP_NAME} API 🌿",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }
