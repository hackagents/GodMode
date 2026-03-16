# Panel Generation

The core loop. Called every time the story needs to advance.

---

## Prompt 1 — Story bootstrap

> Run **once** at session start. Opens the story from a known tale and give out set of divergence points.

### Variables

| Variable | Example |
|---|---|
| `{STORY_TITLE}` | `Cinderella` |
| `{DIVERGENCE}` | `Cinderella runs away instead of accepting servitude` |
| `{GENRE}` | `Grounded` |

### Prompt

```
Start the story "{STORY_TITLE}" but with this change from the original: {DIVERGENCE}

Tone: {GENRE}

Return JSON:
{
  "panels": [
    { "caption": "...", "scene": "one of: dawn|city|room|market|night|garden|shop|road|crowd|forest" },
    { "caption": "...", "scene": "..." }
  ],
  "checkpoint": {
    "moment": "One sentence — where the character stands right now.",
    "choices": [
      { "text": "Short action phrase", "genre": "one word tone label", "hint": "What kind of story this opens" },
      { "text": "...", "genre": "...", "hint": "..." },
      { "text": "...", "genre": "...", "hint": "..." }
    ]
  }
}
```

### Notes

- `DIVERGENCE` is the fork the user selected on the story selection screen.
- `GENRE` should be one of: `Grounded` / `Dark` / `Hopeful` / `Wild` / `Romantic` / `Political`.
- `scene` tags map to visual thumbnails in your UI — keep to the listed values or extend the list in your art layer.

---

## Prompt 2A — Panel continuation (preset choice)

> Called when the user picks **one of the AI-generated choices** at a checkpoint.

### Variables

| Variable | Description |
|---|---|
| `{STORY_SO_FAR}` | Compact running summary (see architecture doc) |
| `{CHOICE_TEXT}` | The choice the user clicked |
| `{CHOICE_GENRE}` | The genre tag attached to that choice |
| `{PANELS_REMAINING}` | `MAX_PANELS - PANELS_USED` |

### Prompt

```
Story so far:
{STORY_SO_FAR}

The reader chose: "{CHOICE_TEXT}"
Tone for this chapter: {CHOICE_GENRE}
Panels remaining in the story: {PANELS_REMAINING}

Continue the story. Return JSON:
{
  "panels": [
    { "caption": "...", "scene": "..." },
    { "caption": "...", "scene": "..." }
  ],
  "checkpoint": {
    "moment": "One sentence — where the character stands right now.",
    "choices": [
      { "text": "...", "genre": "...", "hint": "..." },
      { "text": "...", "genre": "...", "hint": "..." },
      { "text": "...", "genre": "...", "hint": "..." }
    ]
  }
}

If PANELS_REMAINING is 2 or fewer, still return the panels but set "checkpoint" to null.
```

### Notes

- When `checkpoint` is `null`, show only the panels and then the ending trigger options (End / Write your own).
- `CHOICE_GENRE` shifts the tone for this chapter only — it does not override the session-level `GENRE`.
