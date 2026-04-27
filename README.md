# Multilingual Document Translation System

> High-performance multilingual document translation powered by a local LLM, with a modern SvelteKit frontend and full i18n support.

## Architecture

```
SvelteKit Frontend (SPA)
       │
       ▼ POST /api/upload
FastAPI Server ──→ Orchestrator Pipeline
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    Extractor     Translator    Reconstructor
  (deterministic)  (LLM call)  (deterministic)
  zipfile/xml.etree  Ollama     Clone+Replace
  (Native OOXML)   (Cloud/     format-preserving
                    Local)
         └─────────────┼─────────────┘
                       ▼
              Confidence Scorer  ──→  In-App Review
                       │              or XLIFF Export
                       ▼                    ▼
                  Output File           Bilingual .xlf
```

### Pipeline (4 Phases)

| Phase | Engine | What it does |
|:------|:-------|:-------------|
| **Extract** | Deterministic Python (`zipfile`/`xml.etree`) | Walk XML trees, build inline-tag strings `<tagX>` → `segments[]` |
| **Translate** | LLM via Ollama | Batch translate with Inline Tag preservation via prompt rules |
| **Review** | In-App Web Editor / CLI / CAT Tool | Assigns Confidence (HIGH/MEDIUM/LOW). Allows human editing before final reconstruction. |
| **Reconstruct** | Deterministic Python + Tag Validator | Catch hallucinated tags via RALPH loop. Zip clone original → replace text exactly |

### Supported Languages (15)

| Language | Code | Flag |
|:---------|:-----|:-----|
| Japanese | `ja` | 🇯🇵 |
| Vietnamese | `vi` | 🇻🇳 |
| Chinese (Simplified) | `zh` | 🇨🇳 |
| Chinese (Traditional) | `zh-TW` | 🇹🇼 |
| Korean | `ko` | 🇰🇷 |
| English | `en` | 🇬🇧 |
| French | `fr` | 🇫🇷 |
| German | `de` | 🇩🇪 |
| Spanish | `es` | 🇪🇸 |
| Thai | `th` | 🇹🇭 |
| Indonesian | `id` | 🇮🇩 |
| Russian | `ru` | 🇷🇺 |
| Portuguese | `pt` | 🇵🇹 |
| Arabic | `ar` | 🇸🇦 |
| Hindi | `hi` | 🇮🇳 |

Source language supports **Auto Detect** mode based on Unicode block analysis.

### Key Design Principles

- **100% deterministic reconstruction** — pure Zip binary copy for non-text components, zero data loss (Macros, VML, Charts preserved).
- **Format preservation via Inline Tags** — Trados-style inline tag serialization `<tagX>` to keep rich text styling intra-sentence.
- **LLM Tag Validator (RALPH Loop)** — Python regex validation traps LLM hallucinations/dropped tags and forces automated retries.
- **Source Leak Detection** — Unicode character regex scan catches untranslated source text left in translated output; triggers retry.
- **Translation Cache** — SQLite-based cache (`translations.db`) avoids re-translating already-seen segments across jobs.
- **Unified Native OOXML Engine** — no dependency on volatile `openpyxl`, `python-docx`, `python-pptx` wrappers. All extraction/reconstruction uses `zipfile` + `xml.etree.ElementTree` directly.
- **XLSX Integrity Protection** — regex-based byte surgery on `workbook.xml` preserves original namespace prefixes; cross-sheet formula references and `definedName` ranges auto-updated on sheet rename; `calcChain.xml` dropped with references cleaned; phonetic annotations stripped; drawing text translated via ET with direct serialization.
- **Domain-Aware Prompts** — per-language and per-domain prompt injection (general, IT, legal, medical, finance, marketing) for contextual accuracy.
- **i18n UI** — SvelteKit + Paraglide-JS frontend with type-safe, compiler-based translations. UI language managed via Excel spreadsheet.
- **Confidence Scoring** — multi-signal heuristic classifies segments into HIGH/MEDIUM/LOW for adaptive human-in-the-loop triage.
- **XLIFF Bilingual Exchange** — dual-version (1.2 + 2.1) export/import for CAT tool workflows (Trados, memoQ, OmegaT).

## Supported Formats

| Format | Engine | Extraction Strategy | Reconstruction Strategy |
|:-------|:-------|:-------------------|:-----------------------|
| DOCX | `zipfile` + `xml.etree` | `word/document.xml` etc. `<w:p>` aggregation | Non-destructive Zip Clone + Inline Tag Restore |
| XLSX | `zipfile` + `xml.etree` | `xl/sharedStrings.xml` + `xl/worksheets/*.xml` + `xl/drawings/*.xml` + sheet names | Byte-level surgery: sheet names translated, cross-sheet formula refs updated, drawings translated, phonetic stripped, fonts patched, calcChain dropped |
| PPTX | `zipfile` + `xml.etree` | `ppt/slides/slide*.xml` `<a:p>` aggregation | Non-destructive Zip Clone + Inline Tag Restore |
| TXT/MD | stdlib | Line-by-line + diagram token extraction | Line replacement + grid expansion for ASCII art |
| CSV | csv module | Cell-by-cell | Cell replacement |
| PDF | — | _Not yet implemented_ | _Not yet implemented_ |

## Quick Start

### Prerequisites

- Docker + Docker Compose
- 16GB+ RAM (for Ollama model)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env to match your setup (defaults work for most cases)
```

### 2. Pre-download Model (on internet-connected machine)

```bash
python cli.py setup
```

### 3. Start Services

```bash
docker compose up -d --build
```

### 4. Access UI

Open [http://localhost:8000](http://localhost:8000)

The UI supports language switching via the 🌐 globe icon (top-right). Available UI languages: English, Tiếng Việt, 日本語.

### 5. CLI Usage (alternative to web UI)

```bash
cd backend
pip install -r requirements.txt

# Basic translation
python cli.py translate --file samples/japanese-ja.docx

# Override languages
python cli.py translate --file doc.docx --source ja --target vi

# Generate bilingual XLIFF
python cli.py translate --file doc.docx --export-xliff
python cli.py translate --file doc.docx --export-xliff --xliff-version 2.1

# Review XLIFF in terminal
python cli.py review data/output/doc_vi.xlf

# Reconstruct from edited XLIFF (bypasses LLM)
python cli.py translate --file doc.docx --import-xliff data/output/doc_vi.xlf
```

## Configuration

All settings are managed via environment variables. Configuration priority:

```
Environment variables > .env file > built-in defaults
```

### Available Settings

| Variable | Default | Description |
|:---------|:--------|:------------|
| **Ollama Connection** | | |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama API endpoint |
| `OLLAMA_TIMEOUT` | `1800` | Ollama request timeout (seconds) |
| **Model** | | |
| `MODEL` | `gemma4:e4b` | Translation LLM model |
| **Translation Parameters** | | |
| `SOURCE_LANG` | `ja` | Default source language (or `auto` for detection) |
| `TARGET_LANG` | `vi` | Default target language |
| `DEFAULT_DOMAIN` | `general` | Default translation domain |
| `TRANSLATION_TEMPERATURE` | `0.3` | LLM temperature for translation |
| `TRANSLATION_NUM_CTX` | `4096` | LLM context window size |
| `TRANSLATION_MAX_RETRIES` | `3` | Max retry attempts per failed segment |
| `MAX_CONCURRENT_BATCHES` | `2` | Parallel translation batches |
| **Extraction Parameters** | | |
| `MAX_INLINE_TAGS` | `8` | Max inline tags before stripping for plain-text translation |
| `MAX_SEGMENT_CHARS` | `400` | Max chars per segment before sentence-boundary splitting |
| `BATCH_MAX_CHARS` | `3000` | Max character count per translation batch |
| `BATCH_MAX_SEGMENTS` | `5` | Max segment count per translation batch |
| **Paths** | | |
| `DATABASE_URL` | `sqlite:///data/db/translations.db` | Job database |
| `UPLOAD_DIR` | `/data/uploads` | Upload directory |
| `OUTPUT_DIR` | `/data/output` | Output directory |
| `TEMP_DIR` | `/data/temp` | Temporary files directory |
| **Workers** | | |
| `MAX_WORKERS` | `1` | Background worker count |

> **Docker Note:** `docker-compose.yml` uses `env_file: .env` and overrides Docker-specific paths in its `environment:` block.

## Frontend

The frontend is a **SvelteKit** single-page application with **Paraglide-JS** for i18n. It is compiled to static files and served by FastAPI inside the Docker container.

### Stack

| Technology | Purpose |
|:-----------|:--------|
| SvelteKit 2 | Component framework |
| Paraglide-JS | Compiler-based i18n (type-safe, tree-shakeable) |
| `@sveltejs/adapter-static` | Builds SPA for Docker serving |
| Inter + Noto Sans JP | Typography |

### i18n Translation Management

UI translations are managed via an **Excel spreadsheet** (`ui_translations.xlsx`):

```bash
# 1. Edit translations in the Excel file
# 2. Regenerate JSON message files
python i18n_manager.py

# Output: frontend/messages/en.json, vi.json, ja.json
# 3. Rebuild Docker image to include updated translations
docker compose up -d --build
```

### Components

| Component | Responsibility |
|:----------|:---------------|
| `LanguageSwitcher.svelte` | Globe icon to switch UI language (EN/VI/JA) |
| `LanguageBar.svelte` | Source/Target/Domain dropdowns + Swap button |
| `UploadZone.svelte` | Drag-drop area + file type badges + XLIFF options |
| `JobCard.svelte` | Individual job progress/status/download |
| `GlossaryTable.svelte` | Glossary CRUD (list, upload CSV, delete) |
| `BilingualEditor.svelte` | Bilingual review modal with edit/save |

## Development

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

> **Note:** `python-docx`, `openpyxl`, and `python-pptx` are **not** production dependencies. They are only used in tests for creating fixture files.

### Run Tests

```bash
cd backend
pytest tests/ -v
```

### Frontend Dev (requires Node.js)

```bash
cd frontend
npm install
npm run dev    # Starts dev server at localhost:5173
```

The dev server proxies API requests to `localhost:8000` (the backend).

### Docker Build

```bash
docker compose up -d --build
```

The Dockerfile uses a **multi-stage build**:
1. **Stage 1 (Node.js)**: Compiles Paraglide messages → builds SvelteKit SPA
2. **Stage 2 (Python)**: Copies built frontend + backend into production image

## API Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/upload` | Upload document for translation |
| GET | `/api/jobs` | List recent translation jobs |
| GET | `/api/jobs/{id}` | Get job status + details |
| GET | `/api/download/{id}` | Download translated file |
| GET | `/api/languages` | List supported languages |
| GET | `/api/domains` | List supported domains |
| POST | `/api/glossary/upload` | Upload CSV glossary |
| GET | `/api/glossary` | List glossary terms |
| DELETE | `/api/glossary/{id}` | Delete glossary term |
| GET | `/api/health` | Health check (Ollama connection) |

## Project Structure

```
mvp_jp_vi/
├── frontend/                 # SvelteKit + Paraglide i18n
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/       # Svelte UI components
│   │   │   ├── stores/           # Reactive state (config, i18n)
│   │   │   ├── paraglide/        # Auto-generated i18n (do not edit)
│   │   │   └── api.ts            # Centralized API client
│   │   └── routes/               # SvelteKit pages
│   ├── messages/                 # i18n JSON files (en, vi, ja)
│   ├── project.inlang/          # Paraglide config
│   ├── svelte.config.js
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── agent/                # Core translation pipeline
│   │   │   ├── orchestrator.py       # Pipeline coordinator
│   │   │   ├── extractor.py          # Text extraction (Native OOXML)
│   │   │   ├── translator.py         # LLM batch translation + cache
│   │   │   ├── reconstructor/        # Format-preserving reconstruction
│   │   │   ├── confidence.py         # Confidence scoring
│   │   │   ├── prompt_router.py      # Domain/language prompt selection
│   │   │   └── xliff.py              # XLIFF 1.2/2.1 export/import
│   │   ├── ollama/               # Ollama HTTP client + model manager
│   │   ├── llm/                  # LLM abstraction layer
│   │   ├── prompts/              # Per-language + per-domain prompt rules
│   │   │   └── skills/languages/     # Source/target language prompts
│   │   ├── routes/               # FastAPI endpoints
│   │   ├── utils/                # Language detection, file detect, encoding
│   │   ├── languages.py          # Language registry (15 languages)
│   │   ├── domains.py            # Domain registry (7 domains)
│   │   └── config.py             # Environment settings
│   └── tests/                    # Unit + integration tests
├── cli.py                    # Unified CLI tool
├── PROJECT_MAP.md            # Auto-generated project map
├── i18n_manager.py           # Excel → JSON i18n converter
├── ui_translations.xlsx      # Master UI translation file
├── Dockerfile                # Multi-stage build (Node + Python)
└── docker-compose.yml        # Docker deployment config
```

## Performance Tuning

| Setting | Default | Tuning Guide |
|:--------|:--------|:-------------|
| `MAX_CONCURRENT_BATCHES` | `2` | Increase for high-VRAM GPUs, decrease for CPU-only |
| `OLLAMA_NUM_PARALLEL` | `4` | Match with `MAX_CONCURRENT_BATCHES` |
| `OLLAMA_KEEP_ALIVE` | `24h` | Keeps model in RAM — eliminates cold-start delay |
| `BATCH_MAX_SEGMENTS` | `5` | Segments per batch — lower reduces mismatch risk |
| `BATCH_MAX_CHARS` | `3000` | Chars per batch — tuned for 8K context window |

## Translation Quality Controls

| Control | Implementation |
|:--------|:---------------|
| Language-aware prompts | Per-source/target language prompt rules with linguistic guidance |
| Domain-aware prompts | Per-domain terminology and style rules |
| Inline Tag preservation | Tag serialization rules loaded into LLM system prompt |
| Tag Validator | Regex catches missing/hallucinated `<tagX>` tags, triggers RALPH loop retry |
| Source Leak Detector | Unicode regex detects untranslated source text in output, triggers 1-by-1 retry |
| Translation Cache | SQLite cache — clean translations skip LLM call on subsequent encounters |
| Glossary injection | User-defined terms injected into system prompt as mandatory translation table |
| Count mismatch fallback | Auto-retries 1-by-1 if batch response has wrong segment count |
| Confidence Scoring | Multi-signal heuristic (leak, tags, length, retries, cache) → HIGH/MEDIUM/LOW triage |
| In-App Review | Web UI and CLI for direct editing of LOW/MEDIUM segments before reconstruction |

## License

This project applies a **Dual-licensing** strategy.

**1. Open Source Use (Free):**
This source code is licensed under the [GNU AGPL v3.0](LICENSE). 
You are free to use, learn from, and modify it. However, if you distribute software that includes this source code, or provide it as a network service, you **must** release your product's entire source code to the public under the exact terms of the AGPL v3.0.

**2. Commercial Use (Paid):**
If you are a business looking to use this project in commercial, closed-source products, and you **DO NOT** wish to share your product's source code publicly, you must purchase a Commercial License.

Please contact me via: `vnknowledge2014@gmail.com` for more details.
