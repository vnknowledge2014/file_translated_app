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
                  Output File (_vi)
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
- **LLM Tag Validator (RALPH Loop)** — Python regex validation traps LLM hallucinations/dropped tags and forces automated retries (max 2 attempts per segment).
- **JP Leak Detection** — CJK character regex scan catches untranslated Japanese (Hiragana, Katakana, Kanji) left in translated output; triggers retry with explicit warnings.
- **Translation Cache** — SQLite-based cache (`translation_cache.db`) avoids re-translating already-seen segments across jobs.
- **Unified Native OOXML Engine** — no dependency on volatile `openpyxl`, `python-docx`, `python-pptx` wrappers. All extraction/reconstruction uses `zipfile` + `xml.etree.ElementTree` directly.
- **XLSX Byte-Level Surgery** — regex-based byte surgery on `workbook.xml` preserves original namespace prefixes; cross-sheet formula references (`Sheet!A1`) and `definedName` ranges are auto-updated when sheets are renamed; external workbook refs `[N]Sheet!` are left intact; phonetic annotations (`rPh`) stripped; Japanese fonts patched to Latin equivalents; stale cached `<v>` values stripped; `calcChain.xml` dropped to force recalculation.
- **Single model** — one `gemma4:e4b` handles all translation locally via Ollama.

## Supported Formats

| Format | Engine | Extraction Strategy | Reconstruction Strategy |
|:-------|:-------|:-------------------|:-----------------------|
| DOCX | `zipfile` + `xml.etree` | `word/document.xml` etc. `<w:p>` aggregation | Non-destructive Zip Clone + Inline Tag Restore |
| XLSX | `zipfile` + `xml.etree` | `xl/sharedStrings.xml` + `xl/worksheets/*.xml` (inlineStr) + `xl/drawings/*.xml` + sheet names from `xl/workbook.xml` | Byte-level surgery: sheet names translated, cross-sheet formula refs (`Sheet!A1`, `definedName`) updated, external refs `[N]Sheet!` preserved, drawings/charts refs patched, phonetic stripped, fonts patched, calcChain dropped |
| PPTX | `zipfile` + `xml.etree` | `ppt/slides/slide*.xml` `<a:p>` aggregation | Non-destructive Zip Clone + Inline Tag Restore |
| TXT/MD | stdlib | Line-by-line + diagram token extraction | Line replacement + grid expansion for ASCII art |
| CSV | csv module | Cell-by-cell | Cell replacement |
| PDF | — | _Not yet implemented_ | _Not yet implemented_ |

> **Note:** PDF is listed as a supported file type in configuration but has no extractor or reconstructor implementation yet. Uploading a PDF will fail at the extraction phase.

## Quick Start

### Prerequisites

- Docker + Docker Compose
- 16GB+ RAM (for Ollama model)

### 1. Pre-download Model (on internet-connected machine)

```bash
chmod +x scripts/setup_models.sh
./scripts/setup_models.sh
```

### 2. Start Services

```bash
docker compose up -d
```

### 3. Access UI

Open [http://localhost:8000](http://localhost:8000)

### 4. CLI Usage (alternative to web UI)

```bash
cd backend
pip install -r requirements.txt

python scripts/translate_cli.py --file samples/japanese-ja.docx
python scripts/translate_cli.py --dir samples/
```

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
pytest tests/ -v  # ~70 tests
```

### Start Dev Server

```bash
cd backend
MODEL=gemma4:e4b OLLAMA_URL=http://localhost:11434 \
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

## Environment Variables

| Variable | Default | Description |
|:---------|:--------|:------------|
| `OLLAMA_URL` | `http://ollama:11434` | Ollama API endpoint |
| `MODEL` | `gemma4:e4b` | Translation LLM model |
| `DATABASE_URL` | `sqlite:///data/db/translations.db` | Job database |
| `UPLOAD_DIR` | `/data/uploads` | Upload directory |
| `OUTPUT_DIR` | `/data/output` | Output directory |
| `TEMP_DIR` | `/data/temp` | Temporary files directory |
| `MAX_WORKERS` | `1` | Background worker count |
| `MAX_CONCURRENT_BATCHES` | `2` (config) / `4` (Docker) | Parallel translation batches; Docker Compose overrides to 4 |
| `OLLAMA_TIMEOUT` | `1800` | Ollama request timeout (seconds) |

## Project Structure

```
mvp_jp_vi/
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
│   │   │   ├── client.py            # Async HTTP client (httpx)
│   │   │   ├── model_manager.py     # Model load/unload management
│   │   │   └── exceptions.py        # Custom exceptions (Timeout, Connection, Model errors)
│   │   ├── prompts/            # LLM prompt templates
│   │   │   └── inline_tag_translation_rule.md  # Omni Skill: inline tag preservation rules
│   │   ├── routes/             # FastAPI endpoints
│   │   │   ├── upload.py            # POST /api/upload
│   │   │   ├── jobs.py              # GET /api/jobs, GET /api/jobs/{id}
│   │   │   └── download.py          # GET /api/download/{id}
│   │   ├── utils/              # Japanese detection, file detect, encoding
│   │   │   ├── japanese.py          # has_japanese(), chunk_text()
│   │   │   ├── file_detect.py       # detect_file_type()
│   │   │   └── encoding.py          # read_text_file() with JP encoding detection
│   │   ├── config.py           # Environment settings
│   │   ├── database.py         # Async SQLite CRUD
│   │   ├── models.py           # ORM models (Job, JobAttempt, GlossaryTerm)
│   │   └── main.py             # FastAPI app + lifespan
│   └── tests/                  # Unit + integration tests
├── frontend/
│   └── index.html              # Upload UI + progress tracker
├── data/                       # Runtime data (gitignored contents)
│   ├── uploads/                # Uploaded source documents
│   ├── output/                 # Translated output files
│   └── db/                     # SQLite databases
├── samples/                    # Demo input files (one per format)
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
| Batch size | 5 segs / 3000 chars | Tuned for gemma4:e4b 8K context window |

## Translation Quality Controls

| Control | Implementation |
|:--------|:---------------|
| System prompt | Enforces JP→VI only, keep English/numbers/symbols |
| Omni Skill | `inline_tag_translation_rule.md` loaded into LLM to prevent formatting tag loss |
| Tag Validator | Python regex catches missing/hallucinated `<tagX>` tags post-generation, triggers RALPH loop retry (max 2 attempts) |
| JP Leak Detector | CJK character regex detects untranslated Japanese (Hiragana/Katakana/Kanji) in output, queues 1-by-1 retry with explicit anti-leak warnings |
| Translation Cache | SQLite `translation_cache.db` — segments with cached translations skip LLM call entirely |
| Glossary injection | User-defined `GlossaryTerm` table injected into system prompt as mandatory translation table |
| Count mismatch fallback | Auto-retries 1-by-1 if batch `|||`-delimited response has wrong segment count |

## License / Giấy phép

Dự án này áp dụng chiến lược **Cấp phép kép (Dual-licensing)**.

**1. Sử dụng Mã nguồn mở (Miễn phí):**
Mã nguồn này được cấp phép theo [GNU AGPL v3.0](LICENSE). 
Bạn có thể tự do sử dụng, học tập và sửa đổi. Tuy nhiên, nếu bạn phân phối phần mềm có chứa mã nguồn này, hoặc cung cấp nó như một dịch vụ qua mạng, bạn **bắt buộc** phải công khai toàn bộ mã nguồn sản phẩm của bạn theo đúng điều khoản của AGPL v3.0.

**2. Sử dụng Thương mại (Trả phí):**
Nếu bạn là doanh nghiệp muốn sử dụng dự án này trong các sản phẩm thương mại, phần mềm mã nguồn đóng (closed-source), và **KHÔNG** muốn chia sẻ mã nguồn sản phẩm của mình ra công chúng, bạn cần mua một Giấy phép Thương mại.

Vui lòng liên hệ với tôi qua: `vnknowledge2014@gmail.com` để trao đổi chi tiết.
