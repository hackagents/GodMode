from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

from story_engine.agent.image_generator import _build_image_prompt, generate_chapter_image


# ── prompt construction ────────────────────────────────────────────────────────

def test_prompt_prefers_reveal():
    prompt = _build_image_prompt(
        scene="Long scene text spanning many paragraphs.",
        reveal="The ghost was the king all along.",
        source_story="Hamlet by Shakespeare",
    )
    assert "The ghost was the king all along." in prompt


def test_prompt_falls_back_to_scene_first_paragraph():
    scene = "First paragraph text.\n\nSecond paragraph that should be ignored."
    prompt = _build_image_prompt(scene=scene, reveal=None, source_story="Hamlet")
    assert "First paragraph text." in prompt
    assert "Second paragraph" not in prompt


def test_prompt_falls_back_to_source_story_when_no_scene_or_reveal():
    prompt = _build_image_prompt(scene=None, reveal=None, source_story="Hamlet by Shakespeare")
    assert "Hamlet by Shakespeare" in prompt


def test_prompt_truncates_long_scene():
    long_scene = "A" * 500
    prompt = _build_image_prompt(scene=long_scene, reveal=None, source_story="X")
    # Only first 300 chars of scene should be used
    assert len(prompt) < 500


# ── generate_chapter_image ─────────────────────────────────────────────────────

def _make_mock_response(image_bytes: bytes):
    mock_image = MagicMock()
    mock_image.image_bytes = image_bytes
    mock_generated = MagicMock()
    mock_generated.image = mock_image
    mock_response = MagicMock()
    mock_response.generated_images = [mock_generated]
    return mock_response


def test_generate_returns_base64_and_mime_type():
    fake_bytes = b"fake-image-data"
    mock_response = _make_mock_response(fake_bytes)

    with patch("story_engine.agent.image_generator.gemini_client") as mock_client:
        mock_client.models.generate_images.return_value = mock_response
        result = generate_chapter_image(
            scene="A dark castle at midnight.",
            reveal="The prince is alive.",
            source_story="Hamlet by Shakespeare",
        )

    assert result is not None
    b64_str, mime = result
    assert base64.b64decode(b64_str) == fake_bytes
    assert mime == "image/png"


def test_generate_passes_correct_model_and_prompt():
    mock_response = _make_mock_response(b"img")

    with patch("story_engine.agent.image_generator.gemini_client") as mock_client:
        mock_client.models.generate_images.return_value = mock_response
        generate_chapter_image(
            scene=None,
            reveal="Hamlet sees his father's ghost.",
            source_story="Hamlet by Shakespeare",
        )
        call_kwargs = mock_client.models.generate_images.call_args
        assert "Hamlet sees his father's ghost." in call_kwargs.kwargs["prompt"]


def test_generate_returns_none_on_api_failure():
    with patch("story_engine.agent.image_generator.gemini_client") as mock_client:
        mock_client.models.generate_images.side_effect = Exception("API error")
        result = generate_chapter_image(scene="scene", reveal="reveal", source_story="X")

    assert result is None
