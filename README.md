# JP→VI Document Translation System

> Deterministic, high-performance Japanese→Vietnamese document translation powered by a local LLM.

## Architecture

```
Frontend (HTML/JS)
      │
      ▼ POST /api/upload
FastAPI Server ──→ Orchestrator Pipeline
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    Extractor     Translator    Reconstructor
  (deterministic)  (LLM call)  (deterministic)
  zipfile/xml.etree gemma4:e4b  Clone+Replace
  (Native OOXML)  (Ollama)     format-preserving
         └─────────────┼─────────────┘
                       ▼
              Confidence Scorer  ──→  XLIFF Export (optional)
                       │                    │
                       ▼                    ▼
                  Output File (_vi)    Bilingual .xlf (for review)
```

### Pipeline (3 Phases)

| Phase | Engine | What it does |
|:------|:-------|:-------------|
| **Extract** | Deterministic Python (`zipfile`/`xml.etree`) | Walk XML trees, build inline-tag strings `<tagX>` → `segments[]` |
| **Translate** | gemma4:e4b via Ollama | Batch translate JP→VI with Inline Tag preservation via Omni Skill rules |
| **Reconstruct** | Deterministic Python + Tag Validator | Catch hallucinated tags via RALPH loop. Zip clone original → replace text exactly |

### Key Design Principles

- **100% deterministic reconstruction** — pure Zip binary copy for non-text components, zero data loss (Macros, VML, Charts preserved).
- **Format preservation via Omni Skill** — Trados-style inline tag serialization `<tagX>` to keep rich text styling intra-sentence.
- **LLM Tag Validator (RALPH Loop)** — Python regex validation traps LLM hallucinations/dropped tags and forces automated retries (configurable max attempts per segment).
- **JP Leak Detection** — CJK character regex scan catches untranslated Japanese (Hiragana, Katakana, Kanji) left in translated output; triggers retry with explicit warnings.
- **Translation Cache** — SQLite-based cache (`translations.db`) avoids re-translating already-seen segments across jobs.
- **Unified Native OOXML Engine** — no dependency on volatile `openpyxl`, `python-docx`, `python-pptx` wrappers. All extraction/reconstruction uses `zipfile` + `xml.etree.ElementTree` directly.
- **XLSX Integrity Protection** — regex-based byte surgery on `workbook.xml` preserves original namespace prefixes; cross-sheet formula references and `definedName` ranges auto-updated on sheet rename; `calcChain.xml` dropped with references cleaned from `[Content_Types].xml` and `workbook.xml.rels`; phonetic annotations globally stripped; drawing text translated via ET with direct serialization (bypassing `preserve_xml_declaration` to prevent inline xmlns loss).
- **Environment-based configuration** — all settings externalized to `.env` file with sensible defaults; no `python-dotenv` dependency (custom loader).
- **Single model** — one `gemma4:e4b` handles all translation locally via Ollama.
- **XLIFF Bilingual Exchange** — dual-version (1.2 + 2.1) export/import for CAT tool integration (Trados, memoQ, OmegaT). Inline `<tagX>` mapped to XLIFF `<bpt>/<ept>` (1.2) or `<pc>` (2.1). State machine tracks segment lifecycle: new → translated → needs-review → final.
- **Confidence Scoring** — multi-signal heuristic (JP leak, tag mismatch, length ratio, retry count, cache status) classifies segments into HIGH/MEDIUM/LOW buckets for adaptive human-in-the-loop triage.

## Supported Formats

| Format | Engine | Extraction Strategy | Reconstruction Strategy |
|:-------|:-------|:-------------------|:-----------------------|
| DOCX | `zipfile` + `xml.etree` | `word/document.xml` etc. `<w:p>` aggregation | Non-destructive Zip Clone + Inline Tag Restore |
| XLSX | `zipfile` + `xml.etree` | `xl/sharedStrings.xml` + `xl/worksheets/*.xml` (inlineStr) + `xl/drawings/*.xml` + sheet names from `xl/workbook.xml` | Byte-level surgery: sheet names translated, cross-sheet formula refs updated, drawings translated via ET with direct serialization, phonetic stripped, fonts patched, calcChain dropped + references cleaned |
| PPTX | `zipfile` + `xml.etree` | `ppt/slides/slide*.xml` `<a:p>` aggregation | Non-destructive Zip Clone + Inline Tag Restore |
| TXT/MD | stdlib | Line-by-line + diagram token extraction | Line replacement + grid expansion for ASCII art |
| CSV | csv module | Cell-by-cell | Cell replacement |
| PDF | — | _Not yet implemented_ | _Not yet implemented_ |

> **Note:** PDF is listed as a supported file type in configuration but has no extractor or reconstructor implementation yet. Uploading a PDF will fail at the extraction phase.

## Quick Start

### Prerequisites

- Docker + Docker Compose
- 16GB+ RAM (for Ollama model)

### 1. Configure Environment

```bash
# Copy the example config and customize
cp .env.example .env

# Edit .env to match your setup (defaults work for most cases)
```

### 2. Pre-download Model (on internet-connected machine)

```bash
chmod +x scripts/setup_models.sh
./scripts/setup_models.sh
```

### 3. Start Services

```bash
docker compose up -d
```

### 4. Access UI

Open [http://localhost:8000](http://localhost:8000)

### 5. CLI Usage (alternative to web UI)

```bash
cd backend
pip install -r requirements.txt

# Standard translate
python scripts/translate_cli.py --file samples/japanese-ja.docx
python scripts/translate_cli.py --dir samples/

# Export bilingual XLIFF alongside output
python scripts/translate_cli.py --file doc.docx --export-xliff
python scripts/translate_cli.py --file doc.docx --export-xliff --xliff-version 2.1

# Import reviewed XLIFF (skip LLM entirely)
python scripts/translate_cli.py --file doc.docx --import-xliff data/output/doc_vi.xlf

# Export blank XLIFF for manual translation
python scripts/translate_cli.py --file doc.docx --export-xliff --no-translate
```

## Configuration

All settings are managed via environment variables. Configuration priority:

```
Environment variables > .env file > built-in defaults
```

### Setup

```bash
cp .env.example .env   # Create local config (gitignored)
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

> **Docker Note:** `docker-compose.yml` uses `env_file: .env` and overrides Docker-specific paths (OLLAMA_URL, OUTPUT_DIR, etc.) in its `environment:` block.

## Development

### Setup

```bash
cd backend
pip install -r requirements.txt
```

> **Note:** `python-docx`, `openpyxl`, and `python-pptx` are **not** production dependencies. They are only used in tests for creating fixture files. The production code uses native `zipfile` + `xml.etree.ElementTree`.

### Run Tests

```bash
cd backend
pytest tests/ -v  # ~190 tests
```

### Start Dev Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/upload` | Upload document for translation |
| GET | `/api/jobs` | List recent translation jobs |
| GET | `/api/jobs/{id}` | Get job status + details |
| GET | `/api/download/{id}` | Download translated file |
| GET | `/api/health` | Health check (Ollama connection) |

## Project Structure

```
mvp_jp_vi/
├── .env.example              # Environment config template (committed)
├── .env                      # Local overrides (gitignored)
├── backend/
│   ├── app/
│   │   ├── agent/              # Core translation pipeline
│   │   │   ├── orchestrator.py      # Pipeline coordinator
│   │   │   ├── extractor.py         # Deterministic text extraction (Native OOXML)
│   │   │   ├── translator.py        # LLM batch translation + prompts + cache
│   │   │   └── reconstructor/       # Format-preserving reconstruction
│   │   │       ├── __init__.py          # Dispatcher
│   │   │       ├── _common.py           # Shared: translation map, text matching
│   │   │       ├── _ooxml.py            # Shared: OOXML namespaces, tag serialization, XML preservation
│   │   │       ├── docx.py              # DOCX: Zip clone + inline tag restore
│   │   │       ├── xlsx.py              # XLSX: Byte-level surgery, sheet rename, font patch, phonetic strip
│   │   │       ├── pptx.py              # PPTX: Zip clone + inline tag restore
│   │   │       └── plaintext.py         # TXT/MD/CSV: line replace + ASCII diagram grid expansion
│   │   ├── ollama/             # Ollama HTTP client + model manager
│   │   ├── prompts/            # LLM prompt templates
│   │   ├── routes/             # FastAPI endpoints
│   │   ├── utils/              # Japanese detection, file detect, encoding
│   │   └── config.py           # Environment settings (.env loader + Settings class)
│   └── tests/                  # Unit + integration tests (~160 tests)
├── frontend/
│   └── index.html              # Upload UI + progress tracker
├── data/                       # Runtime data (gitignored contents)
├── docs/
│   └── architecture.md         # Architecture deep-dive
├── scripts/
│   ├── setup_models.sh         # Air-gap model setup
│   ├── translate_cli.py        # CLI translation entry point
│   └── run_e2e_tests.sh        # End-to-end test runner
├── Dockerfile
└── docker-compose.yml
```

## Performance Tuning

| Setting | Default | Tuning Guide |
|:--------|:--------|:-------------|
| `MAX_CONCURRENT_BATCHES` | `2` | Increase for high-VRAM GPUs, decrease for CPU-only |
| `OLLAMA_NUM_PARALLEL` | `4` | Match with `MAX_CONCURRENT_BATCHES` |
| `OLLAMA_KEEP_ALIVE` | `24h` | Keeps model in RAM — eliminates cold-start delay |
| `BATCH_MAX_SEGMENTS` | `5` | Segments per batch — lower reduces mismatch risk |
| `BATCH_MAX_CHARS` | `3000` | Chars per batch — tuned for gemma4:e4b 8K context window |

## Translation Quality Controls

| Control | Implementation |
|:--------|:---------------|
| System prompt | Enforces JP→VI only, keep English/numbers/symbols |
| Omni Skill | `inline_tag_translation_rule.md` loaded into LLM to prevent formatting tag loss |
| Tag Validator | Python regex catches missing/hallucinated `<tagX>` tags post-generation, triggers RALPH loop retry |
| JP Leak Detector | CJK character regex detects untranslated Japanese in output, queues 1-by-1 retry with explicit anti-leak warnings |
| Translation Cache | SQLite `translations.db` — segments with cached translations skip LLM call entirely |
| Glossary injection | User-defined `GlossaryTerm` table injected into system prompt as mandatory translation table |
| Count mismatch fallback | Auto-retries 1-by-1 if batch `|||`-delimited response has wrong segment count |

## License

This project applies a **Dual-licensing** strategy.

**1. Open Source Use (Free):**
This source code is licensed under the [GNU AGPL v3.0](LICENSE). 
You are free to use, learn from, and modify it. However, if you distribute software that includes this source code, or provide it as a network service, you **must** release your product's entire source code to the public under the exact terms of the AGPL v3.0.

**2. Commercial Use (Paid):**
If you are a business looking to use this project in commercial, closed-source products, and you **DO NOT** wish to share your product's source code publicly, you must purchase a Commercial License.

Please contact me via: `vnknowledge2014@gmail.com` for more details.
