import re
import logging
from typing import Optional
from story_engine.models import ChapterResponse, Stake, Choice, ResolvedThread

logger = logging.getLogger(__name__)


def _extract_between(text: str, start_marker: str, end_markers: list[str]) -> Optional[str]:
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return None
    start_idx += len(start_marker)
    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker, start_idx)
        if idx != -1 and idx < end_idx:
            end_idx = idx
    return text[start_idx:end_idx].strip()


def parse_chapter(raw: str, chapter_number: int) -> ChapterResponse:
    section_headers = [
        "─── SCENE ───",
        "─── STAKES ───",
        "─── CHOICES ───",
        "─── RESOLUTION ───",
    ]

    # SCENE
    scene = None
    try:
        scene_text = _extract_between(raw, "─── SCENE ───", ["─── STAKES ───", "─── CHOICES ───", "─── RESOLUTION ───"])
        if scene_text:
            # Remove the [REVEAL:...] part from scene
            scene = re.sub(r'\[REVEAL:.*?\]', '', scene_text, flags=re.DOTALL).strip()
    except Exception as e:
        logger.warning(f"Failed to parse SCENE: {e}")

    # REVEAL
    reveal = None
    try:
        reveal_match = re.search(r'\[REVEAL:\s*(.+?)\]', raw, re.DOTALL)
        if reveal_match:
            reveal = reveal_match.group(1).strip()
    except Exception as e:
        logger.warning(f"Failed to parse REVEAL: {e}")

    # STAKES
    stakes = None
    try:
        stakes_text = _extract_between(raw, "─── STAKES ───", ["─── CHOICES ───", "─── RESOLUTION ───"])
        if stakes_text:
            stakes = []
            for line in stakes_text.splitlines():
                line = line.strip()
                m = re.match(r'(THREAT|OPPORTUNITY|UNKNOWN)\s*[—-]\s*(.+)', line)
                if m:
                    stakes.append(Stake(label=m.group(1), text=m.group(2).strip()))
    except Exception as e:
        logger.warning(f"Failed to parse STAKES: {e}")

    # CHOICES and is_ending
    choices = None
    is_ending = False
    try:
        choices_text = _extract_between(raw, "─── CHOICES ───", ["─── RESOLUTION ───"])
        if choices_text:
            choices = []
            for line in choices_text.splitlines():
                line = line.strip()
                m = re.match(r'([A-D])\.\s*(.+)', line)
                if m:
                    choices.append(Choice(key=m.group(1), text=m.group(2).strip()))
        elif re.search(r'\[END\s*[—-]', raw):
            is_ending = True
    except Exception as e:
        logger.warning(f"Failed to parse CHOICES: {e}")

    # EPITAPH
    epitaph = None
    try:
        epitaph_match = re.search(r'\[END\s*[—-]\s*(.+?)\]:\s*(.+)', raw)
        if epitaph_match:
            epitaph = f"[END — {epitaph_match.group(1).strip()}]: {epitaph_match.group(2).strip()}"
            is_ending = True
    except Exception as e:
        logger.warning(f"Failed to parse EPITAPH: {e}")

    # RESOLUTION and THREADS
    resolution = None
    threads = None
    try:
        resolution_text = _extract_between(raw, "─── RESOLUTION ───", [])
        if resolution_text:
            threads = []
            resolution_lines = []
            for line in resolution_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                m = re.match(r'(RESOLVED|OPEN)\s*[—-]\s*(.+?):\s*(.+)', line)
                if m:
                    threads.append(ResolvedThread(
                        status=m.group(1),
                        thread=m.group(2).strip(),
                        detail=m.group(3).strip()
                    ))
                else:
                    resolution_lines.append(line)
            resolution = " ".join(resolution_lines).strip() or None
    except Exception as e:
        logger.warning(f"Failed to parse RESOLUTION: {e}")

    return ChapterResponse(
        chapter_number=chapter_number,
        scene=scene,
        reveal=reveal,
        stakes=stakes,
        choices=choices,
        resolution=resolution,
        threads=threads,
        epitaph=epitaph,
        is_ending=is_ending,
    )
