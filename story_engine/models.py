from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, model_validator


class CatalogStoryResponse(BaseModel):
    id: int
    title: str
    genre: str
    description: str
    source_story: str
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None
    image_generated_style: Optional[str] = None
    initial_plot: Optional[str] = None
    environment: Optional[str] = None
    text_style: Optional[str] = None


class CatalogWriteRequest(BaseModel):
    title: str
    genre: str
    description: str
    source_story: str
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None
    image_generated_style: Optional[str] = None
    initial_plot: Optional[str] = None
    environment: Optional[str] = None
    text_style: Optional[str] = None


class ThumbnailRequest(BaseModel):
    title: str
    genre: str
    description: str
    source_story: str
    image_generated_style: Optional[str] = None


class ThumbnailResponse(BaseModel):
    image_base64: str
    image_mime_type: str


class StartStoryRequest(BaseModel):
    source_story: Optional[str] = None
    catalog_id: Optional[int] = None

    @model_validator(mode="after")
    def require_one(self) -> "StartStoryRequest":
        if self.source_story is None and self.catalog_id is None:
            raise ValueError("Provide either 'source_story' or 'catalog_id'")
        return self


class ChoiceRequest(BaseModel):
    input: str


class Stake(BaseModel):
    label: Literal["THREAT", "OPPORTUNITY", "UNKNOWN"]
    text: str


class Choice(BaseModel):
    key: Literal["A", "B", "C", "D"]
    text: str


class ResolvedThread(BaseModel):
    status: Literal["RESOLVED", "OPEN"]
    thread: str
    detail: str


class ChapterResponse(BaseModel):
    chapter_number: int
    scene: Optional[str] = None
    reveal: Optional[str] = None
    stakes: Optional[list[Stake]] = None
    choices: Optional[list[Choice]] = None
    resolution: Optional[str] = None
    threads: Optional[list[ResolvedThread]] = None
    epitaph: Optional[str] = None
    is_ending: bool = False
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None


class SessionState(BaseModel):
    session_id: str
    source_story: str
    catalog_id: Optional[int] = None
    chapter_count: int = 0
    status: Literal["active", "ended"] = "active"
    history: list[dict] = []
    chapters: list[ChapterResponse] = []


class SessionSummaryResponse(BaseModel):
    session_id: str
    source_story: str
    chapter_count: int
    status: str
    chapters: list[ChapterResponse]
