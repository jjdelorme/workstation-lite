import os

# Disable context aware certificates to prevent segmentation faults during mTLS cert provider command execution
os.environ["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.health import router as health_router
from app.api.workstations import router as workstations_router
from app.api.admin import router as admin_router

app = FastAPI(title="Workstation Lite API")

# Mount API routes
app.include_router(health_router, prefix="/api")
app.include_router(workstations_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

# Static assets routing
static_dir = os.path.join(os.path.dirname(__file__), "static")
assets_dir = os.path.join(static_dir, "assets")

# Ensure directory exists to avoid startup errors during dev
os.makedirs(assets_dir, exist_ok=True)

# Mount the /assets directory for CSS/JS
# Check if assets directory exists before mounting to avoid errors
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.middleware("http")
async def spa_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # If the request is not for /api/ and returned a 404, we assume it's an SPA route
    if response.status_code == 404 and not request.url.path.startswith("/api/"):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
    return response
