# Story Engine

Story Engine is an interactive narrative API that transforms classic source stories into branching, choice-driven adventures powered by Google Gemini. Each session streams vivid prose chapter by chapter, offering the reader four meaningful choices that shape where the story goes next.

---

## Setup

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install dependencies and activate the virtual environment

```bash
uv sync
source .venv/bin/activate
```

### 3. Configure environment

Create a `.env` file in the repo root:

```env
GCP_PROJECT=your-gcp-project-id
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

Authentication uses Application Default Credentials. Run `gcloud auth application-default login` locally, or attach a service account in production.

Optional overrides (defaults shown):

```env
GCP_LOCATION=global
MODEL_NAME=gemini-2.0-flash
MAX_CHAPTERS=10
```

### 4. Build the frontend

Requires Node.js 18+.

```bash
cd frontend
npm install
npm run build
cd ..
```

This produces `frontend/dist/` which the FastAPI server serves as a static SPA.

---

## Run

```bash
uvicorn story_engine.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## Endpoints

### POST /stories — Start a new story

Begin a new branching narrative from a source story. Returns a **Server-Sent Events (SSE)** stream.

```bash
curl -N -X POST http://localhost:8000/stories \
  -H "Content-Type: application/json" \
  -d '{"source_story": "Hamlet"}'
```

**Response stream events:**
- `[SESSION_ID] <uuid>` — the session ID for continuing the story
- Raw prose text chunks streamed as they are generated
- `[CHAPTER_JSON] {...}` — structured chapter data as the final event

---

### POST /stories/{session_id}/chapters — Continue a story

Advance the story by submitting a choice (`A`, `B`, `C`, or `D`) or any free-text action. Returns an SSE stream.

```bash
curl -N -X POST http://localhost:8000/stories/YOUR_SESSION_ID/chapters \
  -H "Content-Type: application/json" \
  -d '{"input": "A"}'
```

Free-text input also works:

```bash
curl -N -X POST http://localhost:8000/stories/YOUR_SESSION_ID/chapters \
  -H "Content-Type: application/json" \
  -d '{"input": "Hamlet confronts his mother directly and demands the truth."}'
```

**Response stream events:**
- Raw prose text chunks as they arrive
- `[CHAPTER_JSON] {...}` — structured chapter data as the final event

When the story reaches its end (natural conclusion or chapter limit), the final `[CHAPTER_JSON]` will have `"is_ending": true` and an `epitaph` field.

---

### GET /stories/{session_id} — Get session summary

Retrieve the full session state including all chapters generated so far.

```bash
curl http://localhost:8000/stories/YOUR_SESSION_ID
```

**Response:**

```json
{
  "session_id": "uuid",
  "source_story": "Hamlet",
  "chapter_count": 3,
  "status": "active",
  "chapters": [
    {
      "chapter_number": 1,
      "scene": "...",
      "reveal": "...",
      "stakes": [...],
      "choices": [...],
      "resolution": "...",
      "threads": [...],
      "epitaph": null,
      "is_ending": false
    }
  ]
}
```

---

### DELETE /stories/{session_id} — Delete a session

Remove a session and all its data.

```bash
curl -X DELETE http://localhost:8000/stories/YOUR_SESSION_ID
```

Returns `204 No Content` on success.

---

## SSE Event Format

All streaming endpoints (`POST /stories` and `POST /stories/{session_id}/chapters`) use the `text/event-stream` media type. Each event is one line prefixed with `data: ` and terminated with `\n\n`.

| Event prefix | Description |
|---|---|
| `data: [SESSION_ID] <uuid>` | Session ID (first event of `POST /stories` only) |
| `data: <prose>` | Raw story text chunk, streamed incrementally |
| `data: [CHAPTER_JSON] <json>` | Structured `ChapterResponse` JSON (last event) |
| `data: [ERROR] <message>` | Error message if generation fails |

### ChapterResponse fields

| Field | Type | Description |
|---|---|---|
| `chapter_number` | int | Sequential chapter index (1-based) |
| `scene` | string | Narrative prose for the chapter |
| `reveal` | string | One-sentence dramatic twist |
| `stakes` | array | 2-4 stakes with `label` (`THREAT`/`OPPORTUNITY`/`UNKNOWN`) and `text` |
| `choices` | array | Up to 4 choices with `key` (`A`-`D`) and `text`; `null` on ending chapters |
| `resolution` | string | Summary of what resolved from the previous chapter |
| `threads` | array | Named plot threads with `status` (`RESOLVED`/`OPEN`) and `detail` |
| `epitaph` | string | Closing poetic summary; only present on the final chapter |
| `is_ending` | bool | `true` when the story has concluded |

---

## Session Resume Workflow

Sessions are held in memory for the lifetime of the server process. To resume a story after losing the session ID, or to inspect current state before continuing:

1. **Store the session ID** from the first `[SESSION_ID]` event when you start a story.

2. **Retrieve current state** at any time:
   ```bash
   curl http://localhost:8000/stories/YOUR_SESSION_ID
   ```

3. **Continue from where you left off** by posting the next choice:
   ```bash
   curl -N -X POST http://localhost:8000/stories/YOUR_SESSION_ID/chapters \
     -H "Content-Type: application/json" \
     -d '{"input": "B"}'
   ```

4. **Check `status`** in the session summary: `"active"` means more chapters can be generated; `"ended"` means the story has concluded and the session is read-only.

5. **Clean up** when done:
   ```bash
   curl -X DELETE http://localhost:8000/stories/YOUR_SESSION_ID
   ```

Note: sessions are not persisted across server restarts. For production use, replace `SessionStore` in `story_engine/session.py` with a persistent backend (Redis, database, etc.).
