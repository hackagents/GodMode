# Story Engine — Prompt Kit

Complete prompt library for building an interactive AI comic story tool.

## Features covered

- AI-generated story panels in comic caption style
- Checkpoint choices that branch into different genres
- User free-text narration injected mid-story
- Input validation before narration enters the story
- AI creative endings (user-triggered, auto at panel 10, or user-written)
- Compact session state that avoids context bloat

---

## Files

| File | Contents |
|---|---|
| `00_system_prompt.md` | Shared system message — applied to every API call |
| `01_architecture.md` | Call flow diagram, session state object, model recommendations |
| `02_panel_generation.md` | Prompt 1 (bootstrap) and Prompt 2A (continuation) |
| `03_checkpoints.md` | Checkpoint quality rules, Prompt 2B (dynamic checkpoint) |
| `04_user_narration.md` | Prompt 3-PRE (validation) and Prompt 3 (narration injection) |
| `05_ai_endings.md` | Prompts 4A / 4B / 4C — user-triggered, auto, and user-written endings |
| `06_helpers_and_variables.md` | Summary updater, genre guide, full variable reference, scene tags |

---

## Quick start

1. Read `01_architecture.md` to understand the call flow.
2. Set your session state (see `01_architecture.md`).
3. Apply `00_system_prompt.md` as the system message on every call.
4. Call Prompt 1 (`02_panel_generation.md`) to open the story.
5. Loop on Prompt 2A or Prompt 3 at each checkpoint.
6. Trigger an ending with Prompt 4A, 4B, or 4C.

---

## API model split

| Call type | Model |
|---|---|
| Panel generation, checkpoints, endings | `claude-sonnet-4-6` |
| Summary updater, input validation | `claude-haiku-4-5` |
