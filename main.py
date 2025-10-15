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
    version="1.0.0",
)

# =====================================================================
# CORS MIDDLEWARE - MUST BE FIRST!
# =====================================================================

# Define origins explicitly
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://harmony-app-frontend.onrender.com",
]

print("🔧 CORS Configuration:")
print(f"   Allowed Origins: {origins}")

# Add CORS middleware with explicit configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use explicit list
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

print("✅ CORS Middleware configured")

# =====================================================================
# DATABASE INITIALIZATION
# =====================================================================

Base.metadata.create_all(bind=engine)

# =====================================================================
# HEALTH CHECK (before routers)
# =====================================================================


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "cors": "enabled"}


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
        "allowed_origins": origins,
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "insights": "/insights",
            "priorities": "/priorities",
            "daily_logs": "/daily_logs",
        },
    }
