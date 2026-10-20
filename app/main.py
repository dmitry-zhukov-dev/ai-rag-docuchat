from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.workspace import router as workspace_router
from app.api.routes.document import workspace_documents_router, documents_router
from app.api.routes.conversation import (
    workspace_conversations_router,
    conversations_router,
)
from app.api.routes.chat import router as chat_router
from app.api.routes.evaluations import router as evaluations_router
from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

# Browser access with credentials requires explicit origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(sessions_router, prefix="/api/v1", tags=["sessions"])
app.include_router(workspace_router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(workspace_documents_router, prefix="/api/v1", tags=["documents"])
app.include_router(documents_router, prefix="/api/v1", tags=["documents"])
app.include_router(
    workspace_conversations_router, prefix="/api/v1", tags=["conversations"]
)
app.include_router(conversations_router, prefix="/api/v1", tags=["conversations"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(evaluations_router, prefix="/api/v1", tags=["evaluations"])

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))
