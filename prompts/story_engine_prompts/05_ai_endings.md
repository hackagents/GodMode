# AI Endings

Endings can be triggered three ways. All produce the same JSON shape.

| Trigger | Prompt | `ENDING_TRIGGER_REASON` |
|---|---|---|
| User clicks "End story now" | Prompt 4A | `"user_choice"` |
| Panel counter hits `MAX_PANELS` | Prompt 4B | `"panel_limit"` |
| User types their own ending | Prompt 4C | `"user_ending"` |

---

## Ending rules (shared across all three)

Embed these rules in every ending prompt:

```
Rules for the ending:
- One final panel — a vivid, still image. No action. A moment held.
- The last line (the "rest" line) is 1–2 sentences. It does NOT resolve the story.
- It should feel like the last panel of a comic issue — the reader turns the page
  and finds only white space.
- No moral. No summary. No "and so she lived..."
- Favour: an image that stays with you, a question left hanging, a door ajar.
```

---

## Prompt 4A — User-triggered ending

> User pressed **"End story here"** at any panel.

### Variables

| Variable | Description |
|---|---|
| `{STORY_SO_FAR}` | Compact running summary |
| `{LAST_PANEL_CAPTION}` | Caption of the most recent panel |
| `{GENRE}` | Session-level genre tag |

### Prompt

```
Story so far: {STORY_SO_FAR}
The last panel was: "{LAST_PANEL_CAPTION}"
Overall tone: {GENRE}

The reader has chosen to end the story here. Write a creative ending.

Rules for the ending:
- One final panel — a vivid, still image. No action. A moment held.
- The last line (the "rest" line) is 1–2 sentences. It does NOT resolve the story.
- It should feel like the last panel of a comic issue — the reader turns the page
  and finds only white space.
- No moral. No summary. No "and so she lived..."
- Favour: an image that stays with you, a question left hanging, a door ajar.

Return JSON:
{
  "final_panel": {
    "caption": "...",
    "scene":   "..."
  },
  "rest": "The floating last line. Open. Unresolved. Memorable."
}
```

---

## Prompt 4B — Hard stop at panel 10

> The panel counter hit `MAX_PANELS`. Same as 4A with one changed framing sentence.

### Prompt

```
Story so far: {STORY_SO_FAR}
The last panel was: "{LAST_PANEL_CAPTION}"
Overall tone: {GENRE}

The story has reached its maximum length. Write a final panel and closing line that
makes this feel like a natural pause, not an interruption. The reader should feel the
story is resting, not broken.

Rules for the ending:
- One final still-image panel.
- A "rest" line that is open, not resolved.
- The ending should feel like it was always going to stop here.

Return JSON:
{
  "final_panel": {
    "caption": "...",
    "scene":   "..."
  },
  "rest": "..."
}
```

### Notes

- The only meaningful difference from 4A is the framing sentence.  
- You can merge 4A and 4B into a single prompt with a flag:  
  `"triggered_by_limit": true` → use the 4B framing sentence.  
  `"triggered_by_limit": false` → use the 4A framing sentence.

---

## Prompt 4C — User writes their own ending

> User typed how they want the story to end. AI renders it as a final panel.

### Variables

| Variable | Description |
|---|---|
| `{STORY_SO_FAR}` | Compact running summary |
| `{USER_ENDING_INPUT}` | What the user typed |
| `{GENRE}` | Session-level genre tag |

### Prompt

```
Story so far: {STORY_SO_FAR}
The reader wants the story to end with: "{USER_ENDING_INPUT}"
Tone: {GENRE}

Write a final panel that honours what the reader described. Then write a "rest" line —
the floating last sentence — that feels like a held breath after the panel.

The rest line should not explain the ending. It should deepen it.

Return JSON:
{
  "final_panel": {
    "caption": "...",
    "scene":   "..."
  },
  "rest": "..."
}
```

---

## Ending JSON schema

```json
{
  "final_panel": {
    "caption": "1–2 sentences. A still image. Present tense. No resolution.",
    "scene":   "One of: dawn|city|room|market|night|garden|shop|road|crowd|forest"
  },
  "rest": "1–2 sentences. The floating last line. Open door, not closed book."
}
```

---

## Examples of good `rest` lines

> These are illustrative — do not feed these to the model as examples, or it will copy them.

- *"The door was still open. She hadn't decided yet whether that was an invitation or a warning."*
- *"No glass slipper. No fairy godmother. Just a woman who left before dawn and built something real enough to come back to."*
- *"He laughed for a long time. It is, by all accounts, the beginning of something."*
- *"Some stories don't end. They just reach a moment worth pausing on."*
