"""Integration test for the TTS ADK agent.

Run with:
    pytest tests/integration/test_tts_agent.py -v -s
"""
from __future__ import annotations

import asyncio

import pytest

from story_engine.agent.tts_agent import run_tts


@pytest.mark.asyncio
async def test_tts_returns_audio_bytes():
    """run_tts should return non-empty PCM bytes for a short input."""
    text = "Once upon a time, there was a curious traveller."
    voice = "Kore"

    pcm = await run_tts(text, voice)

    assert isinstance(pcm, bytes), "Expected bytes back from run_tts"
    assert len(pcm) > 0, "Expected non-empty audio data"
    print(f"\nReceived {len(pcm)} bytes of audio data")
