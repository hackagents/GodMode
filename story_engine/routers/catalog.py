import asyncio

from fastapi import APIRouter, HTTPException, Response
from story_engine.models import CatalogStoryResponse, CatalogWriteRequest, ThumbnailRequest, ThumbnailResponse
from story_engine.catalog import catalog_store
from story_engine.agent.image_generator import generate_catalog_thumbnail

router = APIRouter()


def _to_response(s) -> CatalogStoryResponse:
    return CatalogStoryResponse(
        id=s.id,
        title=s.title,
        genre=s.genre,
        description=s.description,
        source_story=s.source_story,
        image_base64=s.image_base64,
        image_mime_type=s.image_mime_type,
        image_generated_style=s.image_generated_style,
        initial_plot=s.initial_plot,
        environment=s.environment,
        text_style=s.text_style,
    )


@router.post("/catalog/thumbnail", response_model=ThumbnailResponse)
async def generate_thumbnail(request: ThumbnailRequest):
    result = await asyncio.to_thread(
        generate_catalog_thumbnail,
        request.title,
        request.genre,
        request.description,
        request.source_story,
        request.image_generated_style,
    )
    if not result:
        raise HTTPException(status_code=502, detail="Thumbnail generation failed")
    image_base64, image_mime_type = result
    return ThumbnailResponse(image_base64=image_base64, image_mime_type=image_mime_type)


@router.get("/catalog", response_model=list[CatalogStoryResponse])
async def list_catalog():
    return [_to_response(s) for s in catalog_store.list_stories()]


@router.get("/catalog/{story_id}", response_model=CatalogStoryResponse)
async def get_catalog_story(story_id: int):
    story = catalog_store.get_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Catalog story not found")
    return _to_response(story)


@router.post("/catalog", response_model=CatalogStoryResponse, status_code=201)
async def create_catalog_story(request: CatalogWriteRequest):
    image_base64 = request.image_base64
    image_mime_type = request.image_mime_type

    # Auto-generate thumbnail when the user hasn't supplied one
    if not image_base64:
        result = await asyncio.to_thread(
            generate_catalog_thumbnail,
            request.title,
            request.genre,
            request.description,
            request.source_story,
            request.image_generated_style,
        )
        if result:
            image_base64, image_mime_type = result

    story = catalog_store.create_story(
        title=request.title,
        genre=request.genre,
        description=request.description,
        source_story=request.source_story,
        image_base64=image_base64,
        image_mime_type=image_mime_type,
        image_generated_style=request.image_generated_style,
        initial_plot=request.initial_plot,
        environment=request.environment,
        text_style=request.text_style,
    )
    return _to_response(story)


@router.put("/catalog/{story_id}", response_model=CatalogStoryResponse)
async def update_catalog_story(story_id: int, request: CatalogWriteRequest):
    story = catalog_store.update_story(
        story_id=story_id,
        title=request.title,
        genre=request.genre,
        description=request.description,
        source_story=request.source_story,
        image_base64=request.image_base64,
        image_mime_type=request.image_mime_type,
        image_generated_style=request.image_generated_style,
        initial_plot=request.initial_plot,
        environment=request.environment,
        text_style=request.text_style,
    )
    if story is None:
        raise HTTPException(status_code=404, detail="Catalog story not found")
    return _to_response(story)


@router.delete("/catalog/{story_id}", status_code=204)
async def delete_catalog_story(story_id: int):
    if not catalog_store.delete_story(story_id):
        raise HTTPException(status_code=404, detail="Catalog story not found")
    return Response(status_code=204)
