# Architecture Deep-Dive

> Deterministic Extract → Translate → Reconstruct pipeline.

---

## System Overview

```
┌─── Deployment (Docker Compose) ──────────────────────────┐
│                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │ Frontend │    │  FastAPI App │    │    Ollama      │  │
│  │ :8000    │───→│  :8000       │───→│    :11434      │  │
│  │          │    │              │    │                │  │
│  │ index.   │    │ Orchestrator │    │ gemma4:e4b     │  │
│  │ html     │    │ Pipeline     │    │ (9.6GB)        │  │
│  └──────────┘    │              │    └────────────────┘  │
│                  │ ┌─ SQLite ─┐ │                        │
│                  │ │ jobs     │ │                        │
│                  │ │ glossary │ │                        │
│                  │ │ cache    │ │  translation_cache.db  │
│                  │ └──────────┘ │                        │
│                  └──────────────┘                        │
│                                                          │
│  Volume: /data/                                          │
│  ├── uploads/    (original files)                        │
│  ├── output/     (translated files)                      │
│  ├── temp/       (temporary files)                       │
│  └── db/         (translations.db)                       │
└──────────────────────────────────────────────────────────┘
```

### Environment Variables (Docker Compose defaults)

| Variable | Default | Description |
|:---------|:--------|:------------|
| `OLLAMA_URL` | `http://ollama:11434` | Ollama API endpoint |
| `MODEL` | `gemma4:e4b` | Translation LLM model |
| `DATABASE_URL` | `sqlite:///data/db/translations.db` | Job tracking database |
| `UPLOAD_DIR` | `/data/uploads` | Uploaded source documents |
| `OUTPUT_DIR` | `/data/output` | Translated output files |
| `TEMP_DIR` | `/data/temp` | Temporary files directory |
| `MAX_WORKERS` | `1` | Background worker count |
| `MAX_CONCURRENT_BATCHES` | `2` | Parallel translation batches |
| `OLLAMA_TIMEOUT` | `1800` | Ollama request timeout (seconds) |

---

## Pipeline — 3 Deterministic Phases

```
Input File ──→ [EXTRACT] ──→ segments[] ──→ [TRANSLATE] ──→ segments[] ──→ [RECONSTRUCT] ──→ Output File
               XML Zip Scan   with text      LLM call        + tags          Zip Clone       _vi.ext
               No wrapper     originals      gemma4:e4b      validated       No corruption
                                               │
                                         cache lookup
                                      (translation_cache.db)
```

### Phase 1: EXTRACT (Deterministic)

Each file type has a dedicated extractor that walks every text-bearing node:

| File Type | Traversal Strategy | Key Behavior |
|:----------|:-------------------|:-------------|
| DOCX / PPTX | `zipfile` XML parsing of `document.xml`, `slide*.xml`, `drawing*.xml` | Eliminates Python wrappers for zero-loss parsing. Preserves macros/charts. Binds sibling Text Runs into unified tag chunks (e.g., `text<tag1>bold</tag1>`). Skips hyperlink citation anchors. |
| XLSX | `zipfile` XML parsing of `xl/sharedStrings.xml` + `xl/worksheets/*.xml` + `xl/drawings/*.xml` | Extracts shared strings (standard cells), inline strings (`inlineStr`), and drawing text. `xl/workbook.xml` scanned for sheet names to translate. |
| TXT/MD | Line-by-line scan | Detects ASCII diagram blocks via `` ``` `` fences. Extracts JP tokens from diagrams separately as `diagram_token` type. Extracts table cells as `table_cell` type. |
| CSV | Cell-by-cell scan | Skips numeric/date cells |

**Japanese Detection**: Every text node passes through `has_japanese()` which checks Unicode ranges (Hiragana, Katakana, CJK Unified Ideographs, fullwidth digits/latin, halfwidth katakana). Known JP visual symbols (・〇△ー etc.) are stripped before detection to avoid false positives from retained bullet markers.

**Long Segment Splitting**: Paragraphs exceeding 400 characters are split at sentence boundaries (。！？) to prevent LLM timeout on oversized inputs.

**Output**: `list[dict]` — each segment has `text`, `location`, `type`.

### Phase 2: TRANSLATE (LLM)

```
segments[] ──→ chunk_segments(max_chars=3000, max_segs=5)
                    │
                    ▼
              batches[] ──→ asyncio.gather (semaphore=MAX_CONCURRENT_BATCHES)
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
               translate_batch() × N concurrent
                    │
                    ▼
              cache lookup (translation_cache.db)
              ├─ hit  → return cached translation
              └─ miss → build prompt + call Ollama
                    │
                    ▼
              "text_A|||text_B|||text_C"  ──→  Ollama /api/generate
                    │
                    ▼
              "dịch_A|||dịch_B|||dịch_C"  ──→  split("|||")
                    │
                    ├─ JP leak check (CJK chars in output?) ── fail ──→ 1-by-1 retry
                    ├─ tag validation (match original tags?) ── fail ──→ RALPH Loop (retry)
                    ├─ count match  → assign translated_text, cache result
                    └─ count mismatch → fallback to 1-by-1
```

**Translation Cache**: SQLite database (`translation_cache.db`) maps source text → target text. Before calling Ollama, each segment is checked against the cache. Cache hits skip the LLM call entirely, reducing latency and cost. Only clean translations (no JP leaks, valid tags) are cached.

**Performance**: Parallel batches with `asyncio.Semaphore(MAX_CONCURRENT_BATCHES)`.
Ollama configured with `OLLAMA_NUM_PARALLEL=4` and `OLLAMA_KEEP_ALIVE=24h`.

**RALPH Loop (Retry After Lost Prompt Hallucination)**: When a batch translation fails tag validation or count matching, segments are retried 1-by-1 with cumulative warning messages appended to the system prompt. Max 2 attempts per segment. On final failure, the best-effort output is used (not cached).

**Per-file-type Context Hints**: The system prompt is extended with format-specific guidance:
- `docx`: Heading → concise, body → natural, table cells → short labels
- `xlsx`: Headers → column labels, includes common status translations (完了→Hoàn thành, 未着手→Chưa bắt đầu, 進行中→Đang tiến hành)
- `pptx`: Titles → impactful, maintain bullet structure, translate only JP portions
- `md`: PRESERVE ALL markup, only translate text between markup elements
- `txt` / `csv`: Translate naturally / text values only

### Phase 3: RECONSTRUCT (Deterministic)

| File Type | Strategy |
|:----------|:---------|
| DOCX / PPTX | Non-destructive `zipfile` stream clone. Deserializes `<tagX>` into inline XML runs `<r><rPr>...</rPr><t>...`. Skips modifying pure binary/calc files guaranteeing 100% structural fidelity. XML namespace declarations and declaration headers are preserved via `preserve_xml_declaration()`. |
| XLSX | **Byte-level surgery** (not ET parse/serialize to avoid namespace corruption). Multi-layer approach: (1) `workbook.xml` — regex replaces `<sheet name="...">` only, preserving all namespace prefixes; sheet names sanitized (31-char limit, forbidden chars stripped, collision-free); (2) worksheet `<f>` formulas — sheet name refs updated, `[N]Sheet!` external refs left intact; (3) `<definedName>` — internal sheet refs updated; (4) drawings + charts — sheet name refs in series formulas and hyperlinks patched; (5) **phonetic annotations** (`<rPh>`, `<phoneticPr>`) stripped from `sharedStrings.xml` (furigana indices become invalid after translation); (6) **Japanese font patching** — MS Gothic, Meiryo etc. replaced with Arial/Times New Roman in `styles.xml`, `theme1.xml`, `sharedStrings.xml`, and drawings; (7) **stale cached `<v>` values** containing Japanese text are stripped from formula cells; (8) `calcChain.xml` **dropped entirely** to force Excel recalculation (`fullCalcOnLoad=1` injected). Worksheets without `inlineStr` are passed through byte-for-byte. |
| TXT/MD | Read lines → for each segment find line by index → replace. Markdown prefixes (`#`, `-`, `>`) preserved; LLM-hallucinated duplicate prefixes stripped. ASCII diagrams: **global column expansion** algorithm. |

**ASCII Diagram Grid Expansion**:
When translated Vietnamese text is wider than original Japanese text inside box-drawing diagrams, the reconstructor uses `wcwidth` to calculate visual column widths. If the translation fits within available space (original token width + trailing spaces), it replaces in-place. If wider, the translation is truncated to fill available width via `_truncate_to_visual_width()`. If narrower, padding spaces are added to maintain grid alignment of `│`, `┌`, `└`, `┐`, `┘` characters.

---

## Data Model

### Job Table
```
jobs
├── id (UUID hex, PK)
├── filename, file_type, file_path
├── output_path (nullable — set on completion)
├── status: pending → extracting → translating → reconstructing → verifying → completed | failed
├── progress (0.0–1.0)
├── progress_message (nullable — human-readable status)
├── error_message (nullable)
├── segments_count, duration_seconds
├── created_at, updated_at
└── → job_attempts (1:N)
```

### JobAttempt Table
```
job_attempts
├── id (auto PK)
├── job_id (FK → jobs)
├── attempt_number, phase
├── code_generated, stdout, stderr
├── success, error_message, duration_seconds
└── created_at
```

### GlossaryTerm Table
```
glossary
├── id (auto PK)
├── jp (unique), vi, context
└── created_at
```

---

## API Contract

### POST `/api/upload`
```json
// Request: multipart/form-data with file field
// Response:
{ "job_id": "abc123...", "filename": "report.docx", "file_type": "docx", "status": "pending" }
```

### GET `/api/jobs`
```json
// List recent translation jobs (max 20, newest first)
[
  {
    "id": "abc123...",
    "filename": "report.docx",
    "file_type": "docx",
    "status": "completed",
    "progress": 1.0,
    "progress_message": "Hoàn thành! 42 đoạn, 15.3s",
    "segments_count": 42,
    "duration_seconds": 15.3,
    "created_at": "2026-04-15 10:30:00+00:00"
  }
]
```

### GET `/api/jobs/{job_id}`
```json
{
  "id": "abc123...",
  "filename": "report.docx",
  "file_type": "docx",
  "status": "completed",
  "progress": 1.0,
  "progress_message": "Hoàn thành! 42 đoạn, 15.3s",
  "segments_count": 42,
  "duration_seconds": 15.3,
  "output_path": "/data/output/report_vi.docx",
  "created_at": "2026-04-15 10:30:00+00:00",
  "updated_at": "2026-04-15 10:30:15+00:00",
  "attempts": [{ "attempt": 1, "phase": "translating", "success": true, "duration_seconds": 12.0 }]
}
```

### GET `/api/download/{job_id}`
Binary file download of the translated output. Response filename follows the pattern `original_vi.ext`.

### GET `/api/health`
```json
{ "status": "ok", "ollama": "connected" }
```

---

## Translation Quality Controls

| Control | Implementation |
|:--------|:---------------|
| System prompt | Enforces JP→VI only, keep English/numbers/symbols |
| Omni Skills | `inline_tag_translation_rule.md` loaded into LLM system prompt — strict rules for `<tagX>` preservation with few-shot examples |
| Tag Validator | Python regex catches missing/hallucinated `<tagX>` tags post-generation and triggers RALPH loop retry (max 2 attempts per segment) |
| JP Leak Detector | CJK character regex (`[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF]`) detects untranslated Hiragana, Katakana, and Kanji in output; queues 1-by-1 retry with explicit anti-leak warnings |
| Translation Cache | SQLite `translation_cache.db` — segments with cached translations skip LLM call entirely; only clean translations (no leaks, valid tags) are cached |
| Glossary injection | User-defined `GlossaryTerm` table injected into system prompt as mandatory translation table |
| Count mismatch fallback | Auto-retries 1-by-1 if batch `\|\|\|`-delimited response has wrong segment count |
| Per-file-type context | Format-specific prompt extensions guide LLM behavior (e.g., "PRESERVE ALL markup" for Markdown) |
| Hallucinated prefix strip | Plaintext reconstructor strips duplicate Markdown prefixes (`#`, `-`, `>`) and trailing pipes that LLM may hallucinate into translations |

---

## Security Notes

- **No code generation** — the system never generates or executes arbitrary code
- **No sandbox needed** — all extraction/reconstruction is hardcoded library traversal
- **Air-gapped** — Ollama runs locally, no outbound network calls
- **Docker isolation** — app container has limited filesystem access via volume mounts
- **Per-pipeline OllamaClient** — each translation job creates a fresh HTTP client to prevent timeout-corrupted state from affecting other requests