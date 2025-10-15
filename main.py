from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Base, engine, settings
from app.api.routers import auth, insights, priorities, daily_logs

# =====================================================================
# CREATE APP
# =====================================================================

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    description="Mental Health & Wellness API",
    version="1.0.0"
)

# =====================================================================
# CORS MIDDLEWARE - PRODUCTION READY
# =====================================================================

# ✅ Use your settings.CORS_ORIGINS instead of "*"
# (You already added Render frontend URL in config.py earlier)
print("🔧 CORS Configuration:")
print(f"   Allowed Origins: {settings.CORS_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("✅ CORS Middleware configured")

# =====================================================================
# DATABASE INITIALIZATION
# =====================================================================

# ✅ This ensures DB tables are created at startup
Base.metadata.create_all(bind=engine)

# =====================================================================
# ROUTES
# =====================================================================

app.include_router(auth.router)
app.include_router(insights.router)
app.include_router(priorities.router)
app.include_router(daily_logs.router)

print("✅ All routers included")

# =====================================================================
# ROOT ENDPOINT
# =====================================================================

@app.get("/")
def root():
    """API root endpoint."""
    return {
        "message": "Welcome to Harmony API",
        "version": "1.0.0",
        "cors_enabled": True,
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "insights": "/insights",
            "priorities": "/priorities",
            "daily_logs": "/daily_logs"
        }
    }
