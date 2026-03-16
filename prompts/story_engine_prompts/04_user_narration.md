# User Narration

The user writes their own continuation instead of picking a preset choice.  
This is the most powerful feature — and the trickiest to handle correctly.

The AI must **honour the user's idea** without losing the story's coherence.

---

## Flow

```
User types input
      │
      ▼
Prompt 3-PRE  ←── run in parallel with "weaving your idea in..." loading state
(validation)
      │
   usable?
   /     \
 NO       YES
  │         │
Show       Sanitise input
error      then call Prompt 3
message
```

---

## Prompt 3-PRE — Input validation

> Lightweight pre-check before the input enters the story.  
> Use `claude-haiku` for this call — it's fast and cheap.

### Variables

| Variable | Description |
|---|---|
| `{USER_INPUT}` | Raw text typed by the user |
| `{STORY_CONTEXT}` | 1–2 sentences describing the current story state |

### Prompt

```
A reader has submitted this story direction: "{USER_INPUT}"
Story context: {STORY_CONTEXT}

Evaluate it. Return JSON only:
{
  "usable": true or false,
  "reason": "If false: one sentence why. If true: leave empty.",
  "sanitised": "If usable: the input cleaned of any offensive language but preserving intent. If not usable: empty string."
}

Mark as NOT USABLE if:
- Nonsensical or completely incoherent
- Harmful, violent in a gratuitous way, or sexually explicit
- Targets or names a real person
- Completely breaks the established story world with no charitable interpretation

Mark as USABLE if:
- Creative, surprising, or unconventional
- Dark but not gratuitously harmful
- Vague (e.g. "something unexpected") — these are interpreted creatively
- Even a single word that suggests a direction
```

### Response handling

```js
if (response.usable === false) {
  // Show: "That direction doesn't fit this story — try something else."
  // Do NOT call Prompt 3
} else {
  // Use response.sanitised (or original input if sanitised is empty)
  // Proceed to Prompt 3
}
```

---

## Prompt 3 — User narration injection

> Called after validation passes. Weaves the user's direction into the next panels.

### Variables

| Variable | Description |
|---|---|
| `{STORY_SO_FAR}` | Compact running summary |
| `{USER_INPUT}` | The sanitised input from Prompt 3-PRE |
| `{PANELS_REMAINING}` | `MAX_PANELS - PANELS_USED` |

### Prompt

```
Story so far:
{STORY_SO_FAR}

The reader wrote their own direction: "{USER_INPUT}"

Your job:
1. Honour the spirit and intent of what the reader wrote.
2. If the input is a full sentence or scene, weave it in as-is or lightly adapted.
3. If the input is vague (e.g. "something surprising happens"), interpret it creatively.
4. If the input contradicts established canon, find the most charitable reading that preserves both.
5. Never ignore the user's input. Never replace it with something unrelated.

Panels remaining: {PANELS_REMAINING}

Return JSON:
{
  "panels": [
    { "caption": "...", "scene": "..." },
    { "caption": "...", "scene": "..." }
  ],
  "absorbed": "One sentence: how you interpreted the user's input.",
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

### Notes

- The `absorbed` field is shown to the user as a small confirmation banner:  
  `✦ Your idea: she decides to confront the stepmother directly.`  
  This closes the loop and makes the user feel genuinely heard.
- If `PANELS_REMAINING` is 2 or fewer, set `checkpoint` to `null`.
