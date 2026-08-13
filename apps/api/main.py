import logging
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .middleware.request_id import RequestTracingMiddleware
from .routes.coding import router as coding_router
from .routes.me import router as me_router
from .routes.models import router as models_router
from .routes.workers import router as workers_router

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("api-gateway")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="SovereignForge Privacy-First AI Control Plane & API Gateway",
)

# Middleware Pipeline
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits VS Code Webviews and local extensions
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware)

# Global Exception Handler for Zero-Leakage Standardized Errors
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "invalid_request_error" if exc.status_code < 500 else "server_error",
                "request_id": req_id,
            }
        },
    )

# Register Routers
app.include_router(coding_router)
app.include_router(me_router)
app.include_router(models_router)
app.include_router(workers_router)

@app.get("/health", tags=["System Health"])
async def gateway_health_check():
    """Returns the operational health of the SovereignForge API Gateway."""
    return {
        "status": "healthy",
        "service": "sovereignforge-gateway",
        "version": settings.version,
        "environment": settings.environment,
    }

@app.get("/ui", tags=["UI Test Bench"])
@app.get("/", tags=["UI Test Bench"])
async def serve_ui_test_bench():
    """Serves the live interactive SovereignForge & PrivyCode test bench."""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=static_file.read_text(encoding="utf-8"))
    return {"message": "UI test bench not found"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
