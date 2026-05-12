# InfiTrans — Project Map

> Semantic summaries and structural metadata for the InfiTrans translation platform.
> Auto-generated reference for developers and AI agents.

---

## 1. Root Configuration

| File | Purpose |
|:-----|:--------|
| `.env` / `.env.example` | Environment configuration (Ollama, DB, MinIO, JWT, LLM params) |
| `Dockerfile` | Multi-stage build: Stage 1 (Node.js → SvelteKit SPA), Stage 2 (Python → production) |
| `docker-compose.yml` | 3-service stack: `app` (FastAPI), `surrealdb` (v2.1.4), `minio` (S3 storage) |
| `docs/PROJECT_MAP.md` | This file |
| `scripts/cli.py` | Unified CLI: `translate`, `review`, `setup` commands |
| `scripts/i18n_manager.py` | Excel → JSON i18n converter (`ui_translations.xlsx` → `messages/*.json`) |
| `ui_translations.xlsx` | Master UI translation spreadsheet (EN, VI, JA) |

---

## 2. Backend — `backend/app/`

### Core Application

| File | Purpose | Key Exports |
|:-----|:--------|:------------|
| `main.py` | FastAPI app with lifespan, CORS, SPA serving, route registration | `app` |
| `config.py` | Settings singleton from `.env` + env vars (no python-dotenv) | `settings` |
| `auth.py` | JWT + bcrypt authentication (native, no passlib) | `verify_password`, `get_password_hash`, `create_access_token`, `get_current_user` |
| `database.py` | SurrealDB async client — CRUD for jobs, users, glossary, TM cache | `db`, `init_db`, `create_job`, `get_job`, `update_job_progress` |
| `storage.py` | MinIO S3 client — upload, download, streaming, SSE-C encryption, lifecycle | `storage` |
| `worker.py` | Async job worker pool with bounded concurrency | `WorkerPool`, `JobItem` |
| `models.py` | Pydantic models: `Job`, `User`, `GlossaryTerm`, `SegmentReview` | — |
| `languages.py` | Language registry — 15 language profiles with Unicode patterns | `get_language`, `list_languages` |
| `domains.py` | Domain registry — 7 domain profiles with descriptions | `get_domain`, `list_supported_domains` |
| `logging_config.py` | Structured logging setup (JSON prod / colored dev) | `setup_logging` |

### Translation Pipeline — `backend/app/agent/`

| File | Purpose | Key Exports |
|:-----|:--------|:------------|
| `orchestrator.py` | Pipeline coordinator: Extract → Translate → Score → Reconstruct | `Orchestrator` |
| `extractor.py` | Text extraction for all formats (OOXML, plaintext, CSV) | `extract_docx`, `extract_xlsx`, `extract_pptx`, `extract_text` |
| `translator.py` | LLM batch translation with `\|\|\|` delimiter, cache, retries | `Translator`, `chunk_segments` |
| `confidence.py` | Multi-signal heuristic scorer (leak, tags, length, retries, cache) | `score_segment`, `classify_segments` |
| `prompt_router.py` | Dynamic prompt assembly from 6 sources | `PromptRouter` |
| `xliff.py` | XLIFF 1.2 + 2.1 dual-version export/import | `export_xliff`, `import_xliff`, `detect_xliff_version` |

### Reconstructor — `backend/app/agent/reconstructor/`

| File | Purpose | Key Functions |
|:-----|:--------|:-------------|
| `__init__.py` | Format dispatcher | `reconstruct_document` |
| `_common.py` | Translation map builder, text replacement | `build_translation_map`, `replace_in_text` |
| `_ooxml.py` | Shared OOXML: namespace management, tag deserialization, run replacement, word boundary fix | `register_document_namespaces`, `replace_paragraph_runs`, `preserve_xml_declaration` |
| `docx.py` | DOCX reconstruction (document + headers/footers/notes) | `reconstruct_docx` |
| `xlsx.py` | XLSX reconstruction (shared strings, sheet names, formulas, drawings) | `reconstruct_xlsx` |
| `pptx.py` | PPTX reconstruction (slides + notes) | `reconstruct_pptx` |
| `plaintext.py` | TXT/MD/CSV reconstruction (line replacement, ASCII grid expansion) | `reconstruct_plaintext` |

### LLM Layer — `backend/app/llm/`

| File | Purpose | Key Exports |
|:-----|:--------|:------------|
| `base.py` | Abstract LLMClient interface | `LLMClient` |
| `factory.py` | Backend factory (Ollama or Cloud) | `create_llm_client` |
| `model_router.py` | Tiered model resolution via Env Vars | `model_router` |
| `openai_compat.py` | OpenAI-compatible API client for OpenRouter/Anthropic/Google | `OpenAICompatClient` |

### Ollama Client — `backend/app/ollama/`

| File | Purpose | Key Exports |
|:-----|:--------|:------------|
| `client.py` | Async HTTP client for Ollama REST API | `OllamaClient` |
| `model_manager.py` | Model loading/unloading for RAM constraint | `ModelManager` |
| `exceptions.py` | Custom exceptions | `OllamaError`, `OllamaConnectionError`, `OllamaTimeoutError` |

### Routes — `backend/app/routes/`

| File | Endpoints | Auth |
|:-----|:----------|:-----|
| `auth.py` / `wallet_auth.py` | `/api/auth/*` | Public / Web3 |
| `admin.py` | `/api/admin/*` (Users, System config) | Admin JWT |
| `billing.py` | `/api/billing/*` (Solana Pay transactions) | JWT |
| `api_keys.py` | `/api/keys/*` (API key provisioning) | JWT |
| `upload.py` | `POST /api/upload` | JWT |
| `jobs.py` | `GET /api/jobs`, `GET /api/jobs/{id}` | JWT |
| `download.py` | `GET /api/download/{id}` | JWT |
| `glossary.py` | `GET /api/glossary`, `POST /api/glossary/upload`, `DELETE /api/glossary/{id}` | JWT |
| `segments.py` | `GET /api/segments/{job_id}`, `PUT /api/segments/{id}`, `POST /api/segments/reconstruct` | JWT |
| `xliff.py` | `GET /api/xliff/{job_id}`, `POST /api/xliff/import` | JWT |

### Utilities — `backend/app/utils/`

| File | Purpose | Key Functions |
|:-----|:--------|:-------------|
| `language_detect.py` | Unicode block analysis for auto-detection | `detect_language`, `has_source_language` |
| `file_detect.py` | File type detection by extension | `detect_file_type`, `get_supported_types` |
| `encoding.py` | Text file encoding detection | `read_text_file` |

### Prompt Resources — `backend/app/prompts/`

```
prompts/
├── rules/formats/
│   ├── ooxml.md          # OOXML tag preservation rules
│   └── plaintext.md      # Plaintext format rules
└── skills/
    ├── domains/           # 7 domain prompts
    │   ├── general.md, it.md, it_software.md
    │   ├── legal.md, medical.md, finance.md, marketing.md
    └── languages/
        ├── source/        # 15 source language prompts
        │   ├── ja.md, vi.md, zh.md, zh-TW.md, ko.md
        │   ├── en.md, fr.md, de.md, es.md
        │   ├── th.md, id.md, ru.md, pt.md, ar.md, hi.md
        └── target/        # 15 target language prompts
            └── (same 15 languages)
```

---

## 3. Frontend — `frontend/src/`

### Application Shell

| File | Purpose |
|:-----|:--------|
| `app.html` | HTML template with Google Fonts (Inter + Noto Sans JP) |
| `app.css` | Design system: dark glassmorphism, CSS custom properties, animations |
| `app.d.ts` | TypeScript declarations |

### Routes

| Route Group | Path | Purpose |
|:------------|:-----|:--------|
| `(marketing)` | `/` | Landing page, Pricing, API Docs |
| `(auth)` | `/login`, `/register`, `/forgot-password`, Wallet Auth | Authentication pages |
| `(app)` | `/translate`, `/admin`, `/settings` | Workspace, Dashboard, Admin panels |

### Components — `frontend/src/lib/components/`

| Component | Responsibility |
|:----------|:---------------|
| `LanguageSwitcher.svelte` | UI language toggle (EN/VI/JA/ZH) via Paraglide |
| `LanguageBar.svelte` | Source/Target/Domain dropdowns with swap button |
| `UploadZone.svelte` | Drag-drop upload, file type badges, XLIFF toggle, version select |
| `JobCard.svelte` | Job progress tracking with real-time updates |
| `GlossaryTable.svelte` | Glossary CRUD: add terms, CSV upload, delete, toggle replacement |
| `BilingualEditor.svelte` | Split-pane segment review modal with confidence badges |
| `XliffImport.svelte` | XLIFF file upload for reviewed translations |
| `ToastContainer.svelte` | Global toast notification system |
| `solana-pay.ts` | Solana Web3 connection and payment verification logic |
| `icons/` | SVG icon components (no emoji in UI) |

### Stores — `frontend/src/lib/stores/`

| Store | Purpose |
|:------|:--------|
| `config.ts` | Reactive state: `sourceLang`, `targetLang`, `domain` |
| `i18n.ts` | Paraglide language bindings and locale detection |

### API Client — `frontend/src/lib/api.ts`

Centralized fetch wrapper with JWT token injection, error handling, and typed responses.

---

## 4. Tests — `backend/tests/`

| Test File | Coverage Area |
|:----------|:-------------|
| `test_api.py` | FastAPI routes: upload, jobs, download, health |
| `test_extractor.py` | Document extraction: DOCX, XLSX, PPTX |
| `test_reconstructor.py` | Document reconstruction: all formats |
| `test_translator.py` | Batch translation, chunking, cache |
| `test_xliff.py` | XLIFF 1.2/2.1 export/import/roundtrip |
| `test_confidence.py` | Confidence scoring signals |
| `test_config.py` | Settings loading |
| `test_database.py` | SurrealDB CRUD operations |
| `test_encoding.py` | Text file encoding detection |
| `test_file_detect.py` | File type detection |
| `test_language_detect.py` | Language detection + Unicode analysis |
| `test_ollama_client.py` | Ollama HTTP client mocking |
| `test_model_manager.py` | Model switching |
| `test_native_zip_xml.py` | ZIP/XML integrity |
| `test_grid_expansion.py` | ASCII art grid expansion |
| `test_e2e_pipeline.py` | Full pipeline E2E test |

---

## 5. Documentation — `docs/`

| File | Purpose |
|:-----|:--------|
| `architecture.md` | System architecture deep-dive with Mermaid diagrams |
| `security-audit.md` | Expert security analysis, compliance audit, hardening checklist |
