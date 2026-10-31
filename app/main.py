"""Main FastAPI application for Jankyard.ai"""
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core.config import config
from app.core.logging import setup_logging
from app.routes import auth, challenges, submissions, leaderboard, runs

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Import challenges to register them
import app.challenges

# Initialize FastAPI app
app = FastAPI(
    title="Jankyard.ai",
    description="Turn your prompt crimes into high scores.",
    version="0.1.0",
    debug=config.DEBUG
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jankyard.ai", "https://www.jankyard.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Setup static files and templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Include API routers
app.include_router(auth.router)
app.include_router(challenges.router)
app.include_router(submissions.router)
app.include_router(leaderboard.router)
app.include_router(runs.router)


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Homepage route"""
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.head("/")
async def homepage_head():
    """Health check endpoint for App Engine (HEAD requests)"""
    return Response(status_code=200)


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """Hidden about/origin story page (easter egg)"""
    return templates.TemplateResponse(request, "about.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse(request, "login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse(request, "register.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "jankyard.ai"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=config.DEBUG)
