"""
FastAPI application entry point.
Mounts API routes and configures CORS for frontend.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.utils.logging_config import setup_logging
from backend.api.routes import router

# Setup logging as soon as app loads
setup_logging()

app = FastAPI(
    title="Skin AI Assistant API",
    version="1.0.0",
    description="Analyze skin and optional blood report for personalized skincare recommendations.",
)

# CORS so frontend (dev or deployed) can call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Keep 500s JSON-friendly so the UI can show a real message instead of a blank error."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}. Please try again."},
    )


@app.get("/")
async def root():
    """Root redirect or info."""
    return {
        "message": "Skin AI Assistant API",
        "docs": "/docs",
        "health": "/api/health",
        "analyze": "POST /api/analyze",
    }
