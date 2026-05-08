from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.assets import router as assets_router
from app.routes.alerts import router as alerts_router
from app.routes.chatbot import router as chatbot_router
from app.routes.dashboard import router as dashboard_router
from app.routes.downloads import router as downloads_router
from app.routes.explain import router as explain_router
from app.routes.meta import router as meta_router
from app.routes.analytics import router as analytics_router
from app.routes.anomaly import router as anomaly_router
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)


# ----------------------------
# CORS
# ----------------------------
allow_all = "*" in settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else settings.CORS_ORIGINS,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Root / health
# ----------------------------
@app.get("/")
def root():
    return {
        "message": "Bulk Drug Safety API is running",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ----------------------------
# Routers
# ----------------------------
app.include_router(dashboard_router)
app.include_router(assets_router)
app.include_router(alerts_router)
app.include_router(chatbot_router)
app.include_router(explain_router)
app.include_router(meta_router)
app.include_router(downloads_router)
app.include_router(analytics_router)
app.include_router(anomaly_router)