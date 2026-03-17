import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from story_engine.routers import stories, chapters, sessions
from story_engine.routers import catalog, narration
from story_engine.catalog import catalog_store
from story_engine.session import session_store

_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    catalog_store.init_db()
    session_store.init_db()
    yield


app = FastAPI(title="Story Engine", lifespan=lifespan)

# API routes — all mounted under /api so the SPA catch-all never intercepts them
app.include_router(catalog.router, prefix="/api")
app.include_router(stories.router, prefix="/api")
app.include_router(chapters.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(narration.router, prefix="/api")

# Serve Vite-built static assets (JS, CSS, images)
_assets_dir = os.path.join(_DIST, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


# SPA catch-all — must be registered last
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    index = os.path.join(_DIST, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return {"detail": "Frontend not built. Run: cd frontend && npm install && npm run build"}
