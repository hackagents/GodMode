from __future__ import annotations

import base64
import logging
from typing import Optional

from google.genai import types as genai_types

from story_engine.agent.client import gemini_client
from story_engine.config import settings

logger = logging.getLogger(__name__)

_STYLE = "cinematic illustration, dramatic lighting, highly detailed, painterly"


def _build_image_prompt(scene: Optional[str], reveal: Optional[str], source_story: str) -> str:
    # Prefer the reveal sentence — it's a single vivid dramatic line.
    # Fall back to the opening of the scene.
    if reveal:
        visual = reveal
    elif scene:
        # Take the first paragraph only
        first_para = scene.strip().split("\n\n")[0]
        visual = first_para[:300]
    else:
        visual = source_story

    return f"{visual} — {_STYLE}"


def generate_chapter_image(
    scene: Optional[str],
    reveal: Optional[str],
    source_story: str,
) -> tuple[str, str] | None:
    """Return (base64_string, mime_type) or None if generation fails."""
    prompt = _build_image_prompt(scene, reveal, source_story)
    try:
        response = gemini_client.models.generate_images(
            model=settings.IMAGEN_MODEL,
            prompt=prompt,
            config=genai_types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
            ),
        )
        image = response.generated_images[0].image
        b64 = base64.b64encode(image.image_bytes).decode("utf-8")
        return b64, "image/png"
    except Exception:
        logger.warning("Image generation failed", exc_info=True)
        return None
