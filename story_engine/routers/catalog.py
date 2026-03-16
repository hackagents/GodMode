from fastapi import APIRouter
from story_engine.models import CatalogStoryResponse
from story_engine.catalog import catalog_store

router = APIRouter()


@router.get("/catalog", response_model=list[CatalogStoryResponse])
async def list_catalog():
    return [
        CatalogStoryResponse(
            id=s.id,
            title=s.title,
            genre=s.genre,
            description=s.description,
        )
        for s in catalog_store.list_stories()
    ]
