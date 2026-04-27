# Architecture Deep-Dive

> Deterministic Extract → Translate → Reconstruct pipeline with multilingual support.

---

## System Overview

```
┌─── Deployment (Docker Compose) ──────────────────────────┐
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  SvelteKit   │  │  FastAPI App │  │    Ollama      │  │
│  │  Frontend    │  │  :8000       │  │    :11434      │  │
│  │  (Static SPA)│─→│              │─→│                │  │
│  │  Paraglide   │  │ Orchestrator │  │ gemma4:e4b     │  │
│  │  i18n        │  │ Pipeline     │  │ (or custom)    │  │
│  └──────────────┘  │              │  └────────────────┘  │
│                    │ ┌─ SQLite ─┐ │                       │
│                    │ │ jobs     │ │                       │
│                    │ │ glossary │ │                       │
│                    │ │ cache    │ │  translations.db      │
│                    │ └──────────┘ │                       │
│                    └──────────────┘                       │
│                                                          │
│  Volume: /data/                                          │
│  ├── uploads/    (original files)                        │
│  ├── output/     (translated files + .xlf bilingual)     │
│  ├── temp/       (temporary files)                       │
│  └── db/         (translations.db)                       │
└──────────────────────────────────────────────────────────┘
```

### Docker Build Pipeline

The Dockerfile uses a **multi-stage build**:

```
Stage 1: node:22-slim (frontend-builder)
  ├── npm ci
  ├── paraglide-js compile (i18n → JS modules)
  └── vite build → /frontend/build/

Stage 2: python:3.13-slim (production)
  ├── pip install requirements.txt
  ├── COPY backend/app/ → /app/app/
  ├── COPY --from=frontend-builder /frontend/build/ → /app/frontend/
  └── CMD uvicorn app.main:app
```

### Configuration

All settings are loaded from `.env` file and environment variables via a custom loader in `config.py` (no `python-dotenv` dependency). Priority: **env vars > `.env` file > defaults**.

See `README.md` → Configuration section for the full settings table.

---

## Frontend Architecture

### Technology Stack

| Technology | Purpose |
|:-----------|:--------|
| **SvelteKit 2** | Component framework + routing |
| **Paraglide-JS** | Compiler-based i18n (type-safe, tree-shakeable) |
| **adapter-static** | Builds SPA served by FastAPI |
| **TypeScript** | Type-safe API client + stores |

### Component Structure

```
src/
├── lib/
│   ├── components/
│   │   ├── LanguageSwitcher.svelte   # 🌐 UI language toggle (EN/VI/JA)
│   │   ├── LanguageBar.svelte        # Source/Target/Domain dropdowns
│   │   ├── UploadZone.svelte         # Drag-drop with XLIFF options
│   │   ├── JobCard.svelte            # Job progress + download
│   │   ├── GlossaryTable.svelte      # Glossary CRUD
│   │   └── BilingualEditor.svelte    # Segment review modal
│   ├── stores/
│   │   ├── config.ts                 # Language/domain state
│   │   └── i18n.ts                   # Paraglide language bindings
│   ├── api.ts                        # Centralized API client
│   └── paraglide/                    # Auto-generated (do not edit)
├── routes/
│   ├── +layout.svelte                # Global layout + CSS variables
│   ├── +layout.ts                    # Paraglide SSR config
│   └── +page.svelte                  # Main page (composes all components)
└── app.css                           # Design system (dark glassmorphism)
```

### i18n Workflow

UI translations are managed through a centralized Excel file:

```
ui_translations.xlsx  ──→  i18n_manager.py  ──→  messages/en.json
                                                  messages/vi.json
                                                  messages/ja.json
```

**Key decisions:**
- **UI Language** (Paraglide) is decoupled from **Translation Languages** (backend API)
- Message keys use underscore format (`header_title`) for valid JS identifiers
- Paraglide compiles JSON → tree-shakeable JS modules at build time

### Design System

Dark glassmorphism aesthetic using CSS custom properties:

```css
--bg-primary: #0a0f1c        /* Deep navy background */
--bg-glass: rgba(255,255,255,0.03)  /* Glass effect */
--accent-cyan: #06b6d4       /* Primary accent */
--accent-emerald: #10b981    /* Success/active states */
--gradient-primary: linear-gradient(135deg, #667eea, #764ba2)
```

---

## Translation Pipeline — Adaptive 5-Phase Architecture

```
Input File ──→ [EXTRACT] ──→ segments[] ──→ [TRANSLATE] ──→ [SCORE] ──→ [REVIEW] ──→ [RECONSTRUCT] ──→ Output File
               XML Zip Scan   with text      LLM call      Confidence   Web Editor   Zip Clone       _vi.ext
               No wrapper     originals      (Ollama)       0.0–1.0      or XLIFF     No corruption
                                                │              │
                                          cache lookup    HIGH → auto-approve
                                       (translations.db)  LOW  → needs human edit
```

> **Note**: The SCORE and REVIEW phases are optional. In `--import-xliff` mode, the TRANSLATE phase is skipped entirely.

### Phase 1: EXTRACT (Deterministic)

Each file type has a dedicated extractor that walks every text-bearing node:

| File Type | Traversal Strategy | Key Behavior |
|:----------|:-------------------|:-------------|
| DOCX / PPTX | `zipfile` XML parsing of `document.xml`, `slide*.xml`, `drawing*.xml` | Zero-loss parsing. Preserves macros/charts. Binds sibling Text Runs into unified tag chunks. |
| XLSX | `zipfile` XML parsing of `xl/sharedStrings.xml` + `xl/worksheets/*.xml` + `xl/drawings/*.xml` | Extracts shared strings, inline strings, drawing text, and sheet names. |
| TXT/MD | Line-by-line scan | Detects ASCII diagram blocks. Extracts JP tokens from diagrams separately. |
| CSV | Cell-by-cell scan | Skips numeric/date cells |

**Source Language Detection**: Auto-detection uses Unicode block analysis (Hiragana, Katakana, CJK, Arabic, Devanagari, Hangul, Thai, Cyrillic) to identify the source language when set to `auto`.

**Tag Stripping & Long Segment Splitting** (in extractor):
- Paragraphs with >8 inline tags (`MAX_INLINE_TAGS`) are stripped for plain-text translation
- Segments exceeding 400 characters (`MAX_SEGMENT_CHARS`) are split at sentence boundaries

### Phase 2: TRANSLATE (LLM)

```
segments[] ──→ chunk_segments(max_chars, max_segs)
                    │
                    ▼
              batches[] ──→ asyncio.gather (semaphore)
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
               translate_batch() × N concurrent
                    │
                    ▼
              cache lookup (translations.db)
              ├─ hit  → return cached translation
              └─ miss → build prompt + call Ollama
                    │
                    ▼
              "text_A|||text_B"  ──→  Ollama /api/generate
                    │
              "dịch_A|||dịch_B"  ──→  split("|||")
                    │
                    ├─ source leak check ── fail ──→ 1-by-1 retry
                    ├─ tag validation    ── fail ──→ RALPH Loop
                    └─ count match       → cache result
```

**Prompt Architecture**: The system prompt is dynamically assembled from:
1. **Base translation instruction** (source → target)
2. **Source language rules** (`prompts/skills/languages/source/{lang}.md`)
3. **Target language rules** (`prompts/skills/languages/target/{lang}.md`)
4. **Domain rules** (`prompts/skills/domains/{domain}.md`)
5. **Format rules** (`prompts/rules/formats/{format}.md`)
6. **Glossary terms** (user-defined mandatory translations)

**RALPH Loop** (Retry After Lost Prompt Hallucination): When tag validation fails, segments are retried 1-by-1 with cumulative warning messages. Max attempts configurable via `TRANSLATION_MAX_RETRIES`.

### Phase 3: RECONSTRUCT (Deterministic)

| File Type | Strategy |
|:----------|:---------|
| DOCX / PPTX | Non-destructive `zipfile` stream clone. Deserializes `<tagX>` into inline XML runs. |
| XLSX | Multi-strategy: workbook.xml regex surgery, formula ref updates, drawings via ET, sharedStrings with phonetic stripping, font patching, calcChain cleanup. |
| TXT/MD | Line replacement with Markdown prefix preservation + ASCII diagram grid expansion. |

---

## XLIFF Bilingual Exchange Layer

### Dual-Version Support

| Feature | XLIFF 1.2 (default) | XLIFF 2.1 |
|:--------|:--------------------|:----------|
| Segment element | `<trans-unit>` | `<unit>/<segment>` |
| Inline tags | `<bpt>`/`<ept>`, `<x/>` | `<pc>`, `<ph/>` |
| CAT compatibility | Universal (Trados, memoQ, OmegaT) | Partial |

### In-App Review Editor

- **Web Editor**: Split-pane grid highlighting LOW/MEDIUM segments with auto-save.
- **CLI TUI**: `python cli.py review` for terminal-based review.
- **Direct Reconstruction**: Edit segments and trigger rebuild without XLIFF roundtrip.

---

## Confidence Scoring

| Signal | Penalty | Trigger |
|:-------|:--------|:--------|
| Source Leak | -0.50 | Source language characters remaining in output |
| Tag Mismatch | -0.40 | Missing or hallucinated `<tagX>` markers |
| Length Anomaly | -0.30 | Target/source length ratio < 0.3 or > 3.0 |
| Retry Penalty | -0.10/retry | Segments that required RALPH loop retries |
| Cache Boost | +0.20 | Previously validated translation from cache |

**Classification**: HIGH (≥ 0.85) → auto-approved, MEDIUM (0.60–0.85) → optional review, LOW (< 0.60) → needs review.

---

## Data Model

### Job Table
```
jobs
├── id (UUID hex, PK)
├── filename, file_type, file_path
├── source_lang, target_lang, domain
├── output_path (nullable — set on completion)
├── status: pending → extracting → translating → scoring → reconstructing → completed | failed
├── progress (0.0–1.0), progress_message
├── segments_count, duration_seconds
├── created_at, updated_at
└── → job_attempts (1:N)
```

### GlossaryTerm Table
```
glossary
├── id (auto PK)
├── source_term (unique), target_term, context
└── created_at
```

---

## Security Notes

- **No code generation** — the system never generates or executes arbitrary code
- **No sandbox needed** — all extraction/reconstruction is hardcoded library traversal
- **Air-gapped capable** — Ollama runs locally, no outbound network calls required
- **Docker isolation** — app container has limited filesystem access via volume mounts
- **Per-pipeline OllamaClient** — each job creates a fresh HTTP client to prevent state corruption
- **Environment secrets** — `.env` file is gitignored; `.env.example` template committed without secrets