from __future__ import annotations

from story_engine.agent.parser import parse_chapter

_CHAPTER = """\
─── SCENE ───
The castle loomed against a stormy sky.

[REVEAL: The ghost was the king all along]

─── STAKES ───
THREAT — Claudius suspects Hamlet
OPPORTUNITY — The players can expose the truth
UNKNOWN — Ophelia's loyalty

─── CHOICES ───
A. **Confront Claudius directly**
B. **Stage the play** to catch the king's conscience
C. Flee Denmark and seek allies abroad
D. **Surrender** to fate and do nothing

─── RESOLUTION ───
This is the beginning.
OPEN — The murder: still unproven
"""


def test_choices_strip_asterisks():
    chapter = parse_chapter(_CHAPTER, chapter_number=1)
    assert chapter.choices is not None
    texts = [c.text for c in chapter.choices]
    assert texts[0] == "Confront Claudius directly"
    assert texts[1] == "Stage the play to catch the king's conscience"
    assert texts[2] == "Flee Denmark and seek allies abroad"
    assert texts[3] == "Surrender to fate and do nothing"
    for text in texts:
        assert "*" not in text


def test_choices_keys():
    chapter = parse_chapter(_CHAPTER, chapter_number=1)
    assert [c.key for c in chapter.choices] == ["A", "B", "C", "D"]


def test_scene_parsed():
    chapter = parse_chapter(_CHAPTER, chapter_number=1)
    assert chapter.scene is not None
    assert "castle" in chapter.scene


def test_reveal_parsed():
    chapter = parse_chapter(_CHAPTER, chapter_number=1)
    assert chapter.reveal == "The ghost was the king all along"


def test_stakes_parsed():
    chapter = parse_chapter(_CHAPTER, chapter_number=1)
    assert chapter.stakes is not None
    assert len(chapter.stakes) == 3
    labels = [s.label for s in chapter.stakes]
    assert "THREAT" in labels
    assert "OPPORTUNITY" in labels
    assert "UNKNOWN" in labels
