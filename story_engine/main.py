from contextlib import asynccontextmanager
from fastapi import FastAPI
from story_engine.routers import stories, chapters, sessions
from story_engine.routers import catalog
from story_engine.catalog import catalog_store
from story_engine.session import session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    catalog_store.init_db()
    session_store.init_db()
    yield


app = FastAPI(title="Story Engine", lifespan=lifespan)
app.include_router(catalog.router)
app.include_router(stories.router)
app.include_router(chapters.router)
app.include_router(sessions.router)
