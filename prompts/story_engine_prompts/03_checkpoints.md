# Checkpoints

The checkpoint is the heartbeat of the experience. It must feel like a real decision, not a menu.

---

## Quality rules addendum

> Add this block **inside every continuation prompt** (Prompt 2A, 2B, 3) to enforce meaningful choices.

```
Rules for checkpoint choices:
- Each choice must lead to a DIFFERENT TYPE of story, not just a different event.
- Choice A should feel warmer or more hopeful than choice B.
- Choice C (if present) should surprise — subvert the expected options.
- No choice should be obviously "the right answer."
- Choices are actions or attitudes, never outcomes.
  BAD:  "She becomes queen."
  GOOD: "She walks into the throne room uninvited."
- Hint text names the genre consequence, not the plot consequence.
  BAD:  "She gets the estate back."
  GOOD: "Justice before romance — she tests what he's made of."
```

---

## Prompt 2B — Dynamic checkpoint generation

> Use this when you want the AI to generate **fresh checkpoint choices** rather than relying on choices returned inside a panel continuation call. Useful for deep branches or when the story has taken an unexpected direction.

### Variables

| Variable | Description |
|---|---|
| `{LAST_PANEL_CAPTION}` | The caption of the most recently shown panel |
| `{STORY_SO_FAR}` | Compact running summary |
| `{PANELS_REMAINING}` | `MAX_PANELS - PANELS_USED` |

### Prompt

```
The last panel ended with: "{LAST_PANEL_CAPTION}"
Story so far: {STORY_SO_FAR}
Panels remaining: {PANELS_REMAINING}

Generate a checkpoint. The moment should feel like the character is at the edge of something.
Return only the checkpoint JSON — no panels:

{
  "checkpoint": {
    "moment": "...",
    "choices": [
      { "text": "...", "genre": "...", "hint": "..." },
      { "text": "...", "genre": "...", "hint": "..." },
      { "text": "...", "genre": "...", "hint": "..." }
    ]
  }
}
```

---

## Checkpoint JSON schema

```json
{
  "moment": "String — one sentence placing the character at a decision point.",
  "choices": [
    {
      "text":  "Short action phrase — what the character does or decides.",
      "genre": "One-word tone label shown to the user: Hopeful / Dark / Bold / Free / etc.",
      "hint":  "One sentence describing what kind of story this choice opens."
    }
  ]
}
```

### `genre` label guide

| Label | Meaning |
|---|---|
| `Hopeful` | Things move forward, warmth |
| `Dark` | Tension, loss, moral complexity |
| `Bold` | Risk, confrontation, agency |
| `Free` | Escape, autonomy, no romance |
| `Romantic` | Relationship is the engine |
| `Strategic` | Information and power |
| `Twist` | Subverts expectations |
| `Grounded` | Realistic, small moments |
