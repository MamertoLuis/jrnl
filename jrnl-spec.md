# jrnl — Terminal AI Journal
## Product & Technical Specification (v1.0)

---

## 1. Overview

**jrnl** is a local-first, terminal-based journaling application that uses a locally-run LLM (via Ollama) to enrich entries with automatic tagging, summarization, and mood detection. It supports two entry modes — free-writing and guided conversation — and keeps all data on-device with no external network calls.

### 1.1 Core Philosophy
The AI is a **background collaborator, not a chatbot**. It observes and enriches rather than interrupts. The notebook always comes first — an AI failure should never cost the user their written words.

### 1.2 Goals
- Provide a low-friction way to journal from the terminal
- Automatically enrich entries with tags, mood, and summaries without requiring manual effort
- Offer a conversational fallback for low-energy or distracted days
- Keep all data private and local — no cloud dependency
- Lay groundwork for semantic search (phase 2) without over-building now

### 1.3 Non-Goals (for v1)
- No cloud sync or multi-device support
- No mobile/web interface
- No semantic search / RAG (deferred to phase 2)
- No always-on conversational mode — AI speaks only when addressed or explicitly enabled

---

## 2. User Modes

### 2.1 Free-write (`jrnl new`)
Opens the user's `$EDITOR` with a blank buffer. User writes freely, saves, and exits. No AI interaction during writing.

### 2.2 Conversational (`jrnl talk`)
For days when the user is distracted or feels the day was uneventful. The AI opens with a gentle, low-pressure prompt and engages in a short back-and-forth. At the end of the session, the conversation is **compiled into a standard journal entry**, written in first person, staying close to the user's actual words.

**Design constraints for chat mode:**
- One question at a time
- Short AI responses (1–2 sentences)
- Never interrogates; a flat or short answer is accepted without pushback
- "Nothing happened today" is treated as a valid, complete entry
- May occasionally reference a recent past entry as a callback

---

## 3. AI Enrichment Pipeline

Runs automatically on save, for both entry modes (chat-mode output runs through this after compilation).

### 3.1 Enrichment Outputs
| Field | Type | Description |
|---|---|---|
| `summary` | string | One sentence, <15 words, diary-index style |
| `mood` | enum | AI-classified from a fixed category list |
| `tags` | array of strings | Freeform, 2–5 tags, AI prefers reusing existing tags |

### 3.2 Mood Categories (fixed enum)
`happy`, `sad`, `anxious`, `angry`, `calm`, `excited`, `neutral`, `mixed`

### 3.3 Tag Behavior
- Freeform vocabulary
- AI is given the current tag list as context and instructed to prefer existing tags
- New tags are only introduced when nothing existing fits
- Tags are normalized (lowercase, trimmed) and stored in a shared `tags` table to avoid duplication/drift

### 3.4 Reliability & Fallbacks
Since small local models don't perfectly follow JSON formatting instructions:
- Use Ollama's `format: "json"` parameter as a structural constraint, not just prompt instruction
- Defensively strip markdown code fences before parsing
- Validate `mood` against the enum; fallback to `neutral` if invalid or missing
- Validate `tags` is a list of strings; cap at 5; drop malformed entries
- Validate `summary` is non-empty; fallback to first ~10 words of entry text if missing

**Hard rule:** If the AI enrichment call fails or times out, the entry still saves with `mood = NULL`, `summary = NULL`, no tags. The journal entry itself is never lost due to an AI failure. A `jrnl reprocess <id>` command allows retrying enrichment later.

---

## 4. Prompt Templates

### 4.1 Tagging + Summary + Mood
```
You are analyzing a personal journal entry. Respond with ONLY a JSON object, no other text.

Existing tags in use: {existing_tags_comma_separated}

Journal entry:
"""
{entry_text}
"""

Return JSON in this exact format:
{
  "summary": "<one sentence, under 15 words, capturing the essence of the entry>",
  "mood": "<one of: happy, sad, anxious, angry, calm, excited, neutral, mixed>",
  "tags": ["<2 to 5 short lowercase tags>"]
}

Rules:
- Prefer tags from the existing list above when they fit. Only introduce a new tag if nothing existing applies.
- mood must be exactly one of the listed options.
- summary should sound natural, like a diary index entry, not clinical.
```

### 4.2 Chat Mode System Prompt
```
You are a gentle journaling companion. The user is having a low-effort or
distracted day and wants to talk instead of write. Your job is to help them
surface something worth remembering, without pressure.

Rules:
- Ask only ONE question at a time.
- Keep your responses short — 1 to 2 sentences.
- Never interrogate. If they give a short or flat answer, it's okay —
  don't push for more.
- It's fine if today was uneventful. Saying so is a valid response.
- Occasionally (not every time) you may reference something from their
  recent entries if relevant: {recent_context}
- Do not summarize or analyze during the conversation — that happens after,
  separately.
```

**Opening prompt pool (rotated, not AI-freestyled):**
- "Hey. Anything on your mind today?"
- "How'd today feel, even if nothing much happened?"
- "What's one thing that stuck with you today?"
- "Following up — {callback_reference} — how's that going?"

### 4.3 Chat Compilation Prompt
```
Below is a conversation between a journaling assistant and a user reflecting
on their day. Turn the user's responses into a short first-person journal
entry, as if they had written it themselves.

Rules:
- Use the user's own words and phrasing as much as possible.
- Only add connecting words/sentences needed to make it read naturally.
- Do not add thoughts, interpretations, or details the user didn't say.
- Do not include the assistant's questions in the output.
- If the user indicated nothing much happened, keep the entry short and
  honest rather than padding it.

Conversation:
{transcript}

Write only the journal entry text, nothing else.
```
Compiled output is passed through the tagging/summary/mood prompt (4.1) identically to a free-written entry.

---

## 5. Data Model

### 5.1 `entries`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `created_at` | TEXT (ISO 8601) | used as title/identifier in list views |
| `updated_at` | TEXT | set on edit |
| `source` | TEXT | `'write'` or `'talk'` |
| `raw_text` | TEXT | free-write content or compiled chat entry |
| `summary` | TEXT (nullable) | AI-generated one-liner |
| `mood` | TEXT (nullable) | categorical, from fixed enum |
| `word_count` | INTEGER | computed on save |

### 5.2 `tags`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT UNIQUE | lowercase, trimmed |

### 5.3 `entry_tags` (join table)
| Column | Type |
|---|---|
| `entry_id` | INTEGER FK → entries.id |
| `tag_id` | INTEGER FK → tags.id |

### 5.4 `transcripts`
Populated only when `source = 'talk'`. Kept indefinitely for now (revisit retention policy later).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `entry_id` | INTEGER FK → entries.id | one-to-one |
| `raw_json` | TEXT | `[{"role": "ai"/"user", "text": "..."}]` |
| `created_at` | TEXT | |

### 5.5 Phase 2 addition: `embeddings` (not built in v1, schema reserved)
| Column | Type | Notes |
|---|---|---|
| `entry_id` | INTEGER FK → entries.id | |
| `vector` | BLOB / JSON | from `nomic-embed-text` |
| `model_name` | TEXT | tracks which embedding model produced this vector |

Backfill note: when introduced, a one-time script embeds all existing entries lacking a row in `embeddings`. Editing an entry should invalidate/regenerate its embedding. Switching embedding models requires re-embedding all entries, since vectors across models aren't comparable.

---

## 6. Command Structure

| Command | Behavior |
|---|---|
| `jrnl` (no args) | Prints help text |
| `jrnl new` | Opens `$EDITOR`, saves + enriches on exit |
| `jrnl talk` | Starts conversational session; compiles + enriches on `/done` |
| `jrnl list [--tag] [--mood] [--last Nd] [--source]` | Table view: date, summary, mood, tags |
| `jrnl show <id> [--transcript]` | Full entry; `--transcript` reveals raw chat if source=talk |
| `jrnl edit <id>` | Reopens entry in `$EDITOR`; re-runs enrichment if changed |
| `jrnl delete <id>` | Confirms, then cascades delete across `entry_tags` / `transcripts` |
| `jrnl stats` | Entry count, streaks, source split, top tags, mood distribution |
| `jrnl mood [--last Nd]` | Mood trend over a period |
| `jrnl reprocess <id>` | Re-runs enrichment on an entry that failed or was saved without it |
| `jrnl ask "<query>"` *(phase 2)* | Semantic search over entries |
| `jrnl similar <id>` *(phase 2)* | Surface related past entries |

---

## 7. Technical Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.10+ | Stdlib SQLite, easy HTTP calls, strong terminal UI libraries |
| CLI framework | `click` | Clean subcommand handling |
| Terminal UI | `rich` | Tables, color-coded mood, minimal effort |
| HTTP client | `httpx` | Calls to local Ollama API |
| Database | `sqlite3` (stdlib) | Zero-config, single-file, fits single-user local tool |
| Config format | TOML (`tomllib`/`toml`) | Human-editable |
| Editor invocation | `subprocess` (stdlib) | Shells out to `$EDITOR` via temp file |

### 7.1 Ollama Integration
- Default model: **`llama3.2:3b`** — good instruction-following, fast on typical laptop hardware, reliable JSON output for its size
- Alternatives noted in config for easy swapping: `gemma2:2b` (lighter/faster), `phi3:mini` or `qwen2.5:7b` (higher quality, more RAM/time)
- API: `POST http://localhost:11434/api/generate` for single-shot enrichment/compilation calls; `/api/chat` for multi-turn `jrnl talk` sessions (maintains message history naturally)
- Use `format: "json"` parameter for structured enrichment calls
- Timeout + retry handling required; first call after Ollama starts may be slower due to model load into memory

### 7.2 Config File (`~/.jrnl/config.toml`)
```toml
[ollama]
model = "llama3.2:3b"
host = "http://localhost:11434"
timeout_seconds = 30

[editor]
command = ""  # empty = use $EDITOR env var, fallback to vim, then notepad

[storage]
db_path = "~/.jrnl/journal.db"
```

### 7.3 Error Handling
- **Ollama unreachable** → clear message, not a raw connection error
- **Model not pulled** → check via `/api/tags` on first run; prompt user to `ollama pull <model>`
- **Enrichment failure** → entry still saves (see §3.4 hard rule)
- **Blank entry** → discarded without saving (checked post-`$EDITOR` return)

### 7.4 First-Run Setup
On first launch: create `~/.jrnl/` directory, initialize SQLite schema, write default `config.toml`, verify Ollama connectivity and model availability.

---

## 8. Project Structure

```
jrnl/
├── cli.py               # command routing (click)
├── config.py             # load/save config, defaults
├── db.py                 # schema init, queries
├── ollama_client.py     # wraps Ollama API calls
├── prompts.py             # prompt templates (§4)
├── commands/
│   ├── new.py
│   ├── talk.py
│   ├── list.py
│   ├── show.py
│   ├── edit.py
│   ├── delete.py
│   ├── stats.py
│   ├── mood.py
│   └── reprocess.py
└── ~/.jrnl/               # runtime data (not in repo)
    ├── config.toml
    └── journal.db
```

Phase 2 additions slot in without touching existing files: `phase2/embeddings.py`, `commands/ask.py`, `commands/similar.py`.

---

## 9. Testing Approach
- Unit tests (`pytest`) for JSON validation/fallback logic — highest-risk area for silent breakage
- Manual testing for prompt quality and conversational tone — inherently iterative, not meaningfully unit-testable

---

## 10. Open Items for Future Phases
- Transcript retention policy (currently: keep indefinitely; revisit once compilation quality is trusted)
- Embedding model selection and backfill tooling (phase 2)
- Possible export commands (`--md`, `--pdf`) for reading entries outside the terminal
- Possible `fzf` integration for fuzzy search over titles/tags

---

*Document version 1.0 — reflects design decisions finalized through initial planning discussion. No implementation has begun; this spec is the reference for the build phase.*
