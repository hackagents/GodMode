Hello.# Architecture — How the Prompts Connect

Each API call has a specific role. Understand the flow before wiring the prompts.

---

## Call flow

| Step | Prompt | Trigger | Returns |
|---|---|---|---|
| 1 | Story bootstrap | Session start | 2 panels + checkpoint |
| 2A | Panel continuation | User picks a preset choice | 2 panels + new checkpoint |
| 2B | Dynamic checkpoint | Mid-story, deep branch | Checkpoint only (no panels) |
| 3-PRE | User input validation | User types own narration | `usable` boolean + sanitised input |
| 3 | User narration injection | User types own narration (post-validation) | 2 panels + checkpoint |
| 4A | AI creative ending | User presses "End story now" | 1 final panel + open last line |
| 4B | AI creative ending | Panel counter hits `MAX_PANELS` | 1 final panel + open last line |
| 4C | User-written ending | User types their own ending | 1 final panel + open last line |

---

## Session state

Maintain this object throughout the session. Update after every call.

```json
{
  "STORY_TITLE":           "Cinderella",
  "DIVERGENCE":            "Cinderella runs away instead of accepting servitude",
  "GENRE":                 "Grounded",
  "MAX_PANELS":            10,
  "PANELS_USED":           0,
  "PANELS_REMAINING":      10,
  "STORY_SO_FAR":          "",
  "LAST_PANEL_CAPTION":    "",
  "CURRENT_CHOICES":       [],
  "USER_INPUT":            "",
  "ENDING_TRIGGERED":      false,
  "ENDING_TRIGGER_REASON": ""
}
```

### `ENDING_TRIGGER_REASON` values
- `"user_choice"` — user clicked "End story now"
- `"panel_limit"` — `PANELS_USED` reached `MAX_PANELS`
- `"user_ending"` — user typed their own ending

---

## Model recommendation

| Call | Recommended model |
|---|---|
| All panel + checkpoint + ending prompts | `claude-sonnet-4-6` |
| `STORY_SO_FAR` summary updater | `claude-haiku-4-5` (cheap, fast) |
| User input validation (3-PRE) | `claude-haiku-4-5` (run in parallel with loading state) |

---

## `STORY_SO_FAR` strategy

Do **not** send the full panel transcript back with every call — it bloats context and adds noise.

Instead, maintain a compact running summary updated after each call:

```
Ella left home → worked in laundry → partnered with Sylvie → delivered gown to palace
```

See `06_helper_summary_updater.md` for the prompt that maintains this automatically.
