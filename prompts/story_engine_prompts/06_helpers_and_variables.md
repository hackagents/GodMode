# Helper Prompts & Variable Reference

Supporting prompts and reference material for building the session layer.

---

## Helper prompt — `STORY_SO_FAR` updater

> Run after **every** panel continuation call to keep the summary compact.  
> Use `claude-haiku` — this is a cheap maintenance call, not a creative one.

### Variables

| Variable | Description |
|---|---|
| `{STORY_SO_FAR}` | Current summary string |
| `{NEW_PANEL_1}` | Caption of the first new panel |
| `{NEW_PANEL_2}` | Caption of the second new panel (if any) |
| `{CHOICE_MADE}` | The choice or input that led to this chapter |

### Prompt

```
Current story summary: "{STORY_SO_FAR}"
New panels just added: "{NEW_PANEL_1}" / "{NEW_PANEL_2}"
Choice that led here: "{CHOICE_MADE}"

Update the summary. Rules:
- Max 3 short sentences or a chain of "→" phrases under 40 words.
- Keep all proper nouns, key decisions, and relationship changes.
- Drop scene description and atmosphere — only decisions and consequences.

Return only the updated summary string. No JSON wrapper.
```

### Example output

```
Ella left home at dawn → worked in the laundry → partnered with Sylvie the dressmaker
→ delivered a gown to the palace → met the prince in an antechamber
```

---

## Genre tone guide

Inject the relevant line into panel and continuation prompts to sharpen tone.

| Genre | Inject as |
|---|---|
| `GROUNDED` | `Tone: GROUNDED — realistic consequences, small moments matter, no magic.` |
| `DARK` | `Tone: DARK — things go wrong, tension and moral complexity.` |
| `HOPEFUL` | `Tone: HOPEFUL — setbacks happen but the arc bends forward.` |
| `WILD` | `Tone: WILD — unexpected turns, humour allowed, logic is loose.` |
| `ROMANTIC` | `Tone: ROMANTIC — relationships are the engine, emotional beats first.` |
| `POLITICAL` | `Tone: POLITICAL — power dynamics, alliances, and information as currency.` |

---

## Full variable reference

Every variable used across all prompts.

| Variable | Type | Set when | Updated |
|---|---|---|---|
| `STORY_TITLE` | string | Session start | Never |
| `DIVERGENCE` | string | Session start | Never |
| `GENRE` | string | Session start | Never |
| `MAX_PANELS` | int | Session start | Never |
| `PANELS_USED` | int | Session start (`0`) | After every panel call, += panels returned |
| `PANELS_REMAINING` | int | Session start (`MAX_PANELS`) | After every panel call |
| `STORY_SO_FAR` | string | Session start (`""`) | After every panel call (via helper prompt) |
| `LAST_PANEL_CAPTION` | string | After first panel call | After every panel call |
| `CURRENT_CHOICES` | array | After first checkpoint | After every checkpoint |
| `USER_INPUT` | string | When user types | Cleared after each use |
| `ENDING_TRIGGERED` | bool | `false` | Set to `true` when ending fires |
| `ENDING_TRIGGER_REASON` | string | `""` | Set to `user_choice` / `panel_limit` / `user_ending` |

---

## Scene tag reference

Used in `"scene"` fields of panel JSON. Maps to visual thumbnails in the UI.

| Tag | Visual suggestion |
|---|---|
| `dawn` | Sun rising, road, open horizon |
| `city` | Skyline, rooftops, crowd at distance |
| `room` | Interior, window light, domestic |
| `market` | Stalls, canopies, bustle |
| `night` | Dark sky, moon, lit windows |
| `garden` | Trees, flowers, outdoor stillness |
| `shop` | Storefront, counter, goods |
| `road` | Path, traveller, landscape |
| `crowd` | Many figures, hall, public space |
| `forest` | Trees, path, filtered light |

Extend this list freely — just keep tags lowercase and single-word.

---

## Checkpoint `genre` label guide

Used in the `genre` field of each choice object.

| Label | Tone it signals |
|---|---|
| `Hopeful` | Forward-moving, warm |
| `Dark` | Tension, risk, loss |
| `Bold` | Confrontation, agency |
| `Free` | Escape, autonomy |
| `Romantic` | Relationship-first |
| `Strategic` | Information, power |
| `Twist` | Subverts expectations |
| `Grounded` | Realistic, small moments |
| `Resilient` | Recovery after loss |
| `Political` | Alliances, leverage |
