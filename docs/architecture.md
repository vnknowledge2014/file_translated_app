# Architecture Deep-Dive

> InfiTrans — Enterprise Document Translation Platform  
> Deterministic Extract → Translate → Score → Review → Reconstruct Pipeline

---

## 1. System Overview

```mermaid
graph TB
    subgraph Browser ["Client (Browser)"]
        SPA["SvelteKit SPA<br/>Paraglide i18n<br/>Solana Web3 Auth"]
    end

    subgraph DC ["Docker Compose Stack"]
        subgraph FastAPI ["FastAPI :8000"]
            AUTH["Auth Module<br/>JWT + Web3/Solana"]
            ROUTES["REST API<br/>Admin, Billing, Jobs"]
            SPA_SERVE["SPA Static Server<br/>Catch-all Fallback"]
            WORKER["Worker Pool<br/>Bounded Async Queue"]
        end

        subgraph Pipeline ["Translation Pipeline"]
            EXT["Extractor<br/>zipfile + xml.etree"]
            TRANS["Translator<br/>Batch + Cache"]
            SCORE["Confidence Scorer<br/>Multi-signal"]
            RECON["Reconstructor<br/>ZIP Clone"]
            PR["Prompt Router<br/>Context Engineering"]
        end

        subgraph Data ["Persistent Storage"]
            SURREAL[("SurrealDB v2.1.4<br/>Jobs · Users · Glossary<br/>Translation Cache")]
            MINIO[("MinIO S3<br/>Uploads · Outputs<br/>SSE-C Encryption")]
        end
    end

    subgraph LLM ["LLM Engine (Multi-Model)"]
        ROUTER["Model Router<br/>Tiered Resolution"]
        OLLAMA["Ollama (Local)"]
        CLOUD["Cloud API<br/>OpenAI-Compat"]
    end

    SPA -->|JWT Bearer| ROUTES
    ROUTES --> AUTH
    ROUTES --> WORKER
    WORKER --> EXT
    EXT --> TRANS
    TRANS -->|Prompt| PR
    TRANS --> ROUTER
    ROUTER -->|HTTP API| OLLAMA
    ROUTER -->|OpenAI-Compat| CLOUD
    TRANS --> SCORE
    SCORE --> RECON
    ROUTES -->|CRUD| SURREAL
    EXT -->|Read| MINIO
    RECON -->|Write| MINIO
    WORKER -->|Status Update| SURREAL
```

### Docker Build Pipeline

```mermaid
graph LR
    subgraph Stage1 ["Stage 1: node:22-slim"]
        NPM["npm ci"] --> PARA["paraglide-js compile"]
        PARA --> VITE["vite build"]
        VITE --> BUILD["/frontend/build/"]
    end

    subgraph Stage2 ["Stage 2: python:3.13-slim"]
        PIP["pip install"] --> COPY_BE["COPY backend/"]
        COPY_BE --> COPY_FE["COPY --from=Stage1<br/>/frontend/build/"]
        COPY_FE --> CMD["CMD uvicorn<br/>app.main:app"]
    end

    Stage1 --> Stage2
```

### Configuration Flow

```
Environment Variables  ─→  os.environ  ─→  config.py Settings singleton
         ↑                                        ↓
   docker-compose.yml                     All modules import
   environment: block                     from app.config import settings
         ↑
   .env file (loaded by
   custom _load_dotenv)
```

Priority: **env vars > docker-compose environment > .env file > built-in defaults**

---

## 2. Frontend Architecture

### Technology Stack

| Technology | Purpose |
|:-----------|:--------|
| **SvelteKit 2** | Component framework + file-based routing |
| **Paraglide-JS** | Compiler-based i18n (type-safe, tree-shakeable) |
| **adapter-static** | Builds SPA for Docker serving |
| **TypeScript** | Type-safe API client + stores |
| **SVG Icon System** | Custom icon components (no emoji) |

### Route Structure

```mermaid
graph TD
    ROOT["/"] --> MARKETING["(marketing)<br/>Landing, API Docs, Pricing"]
    ROOT --> AUTH_GROUP["(auth)<br/>Login, Web3 Auth"]
    ROOT --> APP_GROUP["(app)<br/>Translate, Dashboard, Admin"]
    
    AUTH_GROUP --> LOGIN["/login"]
    AUTH_GROUP --> REGISTER["/register"]
    AUTH_GROUP --> FORGOT["/forgot-password"]
    
    APP_GROUP --> TRANSLATE["/translate<br/>Step 1: Configure<br/>Step 2: Upload<br/>Advanced Tools"]
```

### Component Architecture

```mermaid
graph TD
    LAYOUT["+layout.svelte<br/>Navbar + Auth Guard"] --> PAGE["translate/+page.svelte"]
    PAGE --> LANGBAR["LanguageBar<br/>Source / Target / Domain"]
    PAGE --> UPLOAD["UploadZone<br/>Drag-Drop + Toggle"]
    PAGE --> JOBS["JobCard ×N<br/>Progress + Download"]
    PAGE --> ADV["Advanced Tools Panel"]
    ADV --> GLOSS["GlossaryTable<br/>CRUD + CSV Upload"]
    ADV --> XLIFF["XliffImport<br/>Upload + Reconstruct"]
    PAGE --> EDITOR["BilingualEditor<br/>Segment Review Modal"]
    LAYOUT --> SWITCHER["LanguageSwitcher<br/>EN / VI / JA"]
```

### Design System

Dark glassmorphism with CSS custom properties:

```css
--bg-primary: #0a0f1c        /* Deep navy */
--bg-card: #111827            /* Card surface */
--accent: #14b8a6             /* Teal primary */
--accent-hover: #0d9488       /* Teal hover */
--gradient-primary: linear-gradient(135deg, #667eea, #764ba2)
--shadow-glow: 0 0 20px rgba(20, 184, 166, 0.15)
```

---

## 3. Translation Pipeline — Detail

### Phase 1: EXTRACT (Deterministic)

```mermaid
flowchart LR
    FILE["Input File<br/>.docx/.xlsx/.pptx"] --> ZIP["zipfile.ZipFile<br/>Read-only"]
    ZIP --> XML["xml.etree<br/>Parse XML"]
    XML --> WALK["Walk Paragraphs<br/>&lt;w:p&gt; / &lt;a:p&gt;"]
    WALK --> TAG["Serialize Runs<br/>&lt;tag1&gt;text&lt;/tag1&gt;"]
    TAG --> SEG["segments[]<br/>text + tag_map"]
    
    SEG --> DEDUP["Dedup<br/>Remove duplicates"]
    DEDUP --> SPLIT["Split Long<br/>>400 chars"]
    SPLIT --> LANG["Language Filter<br/>Auto-detect"]
```

| File Type | Traversal | Key Behavior |
|:----------|:----------|:-------------|
| **DOCX** | `word/document.xml` + headers/footers/endnotes | Processes `<w:p>` paragraphs, aggregates `<w:r>` runs into tagged chunks |
| **XLSX** | `xl/sharedStrings.xml` + worksheets + drawings | Shared strings, inline strings, drawing text, sheet names |
| **PPTX** | `ppt/slides/slide*.xml` | Processes `<a:p>` paragraphs with `<a:r>` runs |
| **TXT/MD** | Line-by-line scan | ASCII diagram detection + token extraction |
| **CSV** | Cell-by-cell | Skips numeric/date cells |

**Auto-Detection**: Uses Unicode block analysis (Hiragana, Katakana, CJK, Arabic, Devanagari, Hangul, Thai, Cyrillic) to identify source language when set to `auto`.

### Phase 2: TRANSLATE (LLM)

```mermaid
flowchart TB
    SEGS["segments[]"] --> CHUNK["chunk_segments()<br/>max_chars=3000<br/>max_segs=5"]
    CHUNK --> BATCHES["batches[]"]
    BATCHES --> SEM["asyncio.Semaphore<br/>MAX_CONCURRENT_BATCHES"]
    
    SEM --> B1["translate_batch()"]
    SEM --> B2["translate_batch()"]
    SEM --> BN["translate_batch()"]
    
    B1 --> CACHE{"Cache<br/>Lookup?"}
    CACHE -->|Hit| RET["Return cached"]
    CACHE -->|Miss| PROMPT["Build Prompt"]
    
    PROMPT --> PR["Prompt Router<br/>base + source + target<br/>+ domain + format<br/>+ glossary"]
    PR --> ROUTER["Model Router<br/>Resolves Best LLM"]
    ROUTER --> LLM_CLIENT{"LLM Client<br/>Ollama OR Cloud"}
    LLM_CLIENT --> SPLIT["Split |||"]
    
    SPLIT --> V1{"Source<br/>Leak?"}
    V1 -->|Yes| RETRY1["1-by-1 Retry"]
    V1 -->|No| V2{"Tag<br/>Valid?"}
    V2 -->|No| RALPH["RALPH Loop<br/>Retry with Warning"]
    V2 -->|Yes| V3{"Count<br/>Match?"}
    V3 -->|No| RETRY1
    V3 -->|Yes| SAVE["Cache + Return"]
```

**Prompt Architecture** — dynamically assembled from 6 sources:

| Source | Path | Purpose |
|:-------|:-----|:--------|
| Base instruction | (inline) | "Translate {source} → {target}" |
| Source language rules | `prompts/skills/languages/source/{lang}.md` | Source-specific parsing guidance |
| Target language rules | `prompts/skills/languages/target/{lang}.md` | Target-specific generation rules |
| Domain rules | `prompts/skills/domains/{domain}.md` | Domain terminology/style |
| Format rules | `prompts/rules/formats/{format}.md` | OOXML tag preservation rules |
| Glossary terms | (from DB) | Mandatory translation pairs |

**RALPH Loop** (Retry After Lost Prompt Hallucination): Regex validates `<tagX>` integrity. Failed segments retry 1-by-1 with cumulative warnings. Max: `TRANSLATION_MAX_RETRIES`.

### Phase 3: SCORE (Confidence)

| Signal | Penalty/Boost | Trigger |
|:-------|:-------------|:--------|
| Source Leak | -0.50 | Source language characters in output |
| Tag Mismatch | -0.40 | Missing or hallucinated `<tagX>` markers |
| Length Anomaly | -0.30 | Target/source ratio < 0.3 or > 3.0 |
| Retry Penalty | -0.10/retry | Segments requiring RALPH retries |
| Cache Boost | +0.20 | Previously validated translation |

Classification: **HIGH** (≥ 0.85) → auto-approve · **MEDIUM** (0.60–0.85) → optional review · **LOW** (< 0.60) → needs review

### Phase 4: REVIEW (Human-in-the-Loop)

- **Web Editor**: Split-pane bilingual grid highlighting LOW/MEDIUM segments
- **XLIFF Export**: Dual-version (1.2 + 2.1) for CAT tools (Trados, memoQ, OmegaT)
- **CLI TUI**: `python scripts/cli.py review` for terminal-based review

### Phase 5: RECONSTRUCT (Deterministic)

```mermaid
flowchart LR
    ORIG["Original ZIP"] --> CLONE["Stream Clone<br/>zipfile"]
    TMAP["Translation Map<br/>{original: translated}"] --> REPLACE["replace_paragraph_runs()"]
    CLONE --> REPLACE
    REPLACE --> DESER["deserialize_tags_to_xml()<br/>&lt;tagX&gt; → &lt;w:r&gt;"]
    DESER --> FIX["_fix_run_boundaries()<br/>Vietnamese word spacing"]
    FIX --> NS["preserve_xml_declaration()<br/>Original xmlns preserved"]
    NS --> OUT["Output ZIP<br/>Format-preserved"]
```

| File Type | Strategy |
|:----------|:---------|
| **DOCX/PPTX** | Non-destructive ZIP stream clone. Deserialize `<tagX>` → OOXML runs |
| **XLSX** | Multi-strategy: workbook.xml regex surgery, formula ref updates, drawings via ET, sharedStrings with phonetic stripping |
| **TXT/MD** | Line replacement with Markdown prefix preservation + ASCII diagram grid expansion |

---

## 4. XLIFF Bilingual Exchange

### Dual-Version Support

| Feature | XLIFF 1.2 | XLIFF 2.1 |
|:--------|:----------|:----------|
| Segment element | `<trans-unit>` | `<unit>/<segment>` |
| Inline tags | `<bpt>`/`<ept>`, `<x/>` | `<pc>`, `<ph/>` |
| CAT compatibility | Universal | Partial |

### Workflow

```
Document → Extract → Translate → Export XLIFF → Edit in CAT Tool → Import XLIFF → Reconstruct
                                      ↓                                   ↑
                              Bilingual .xlf file              Reviewed .xlf file
```

---

## 5. Data Model

```mermaid
erDiagram
    USER {
        string id PK
        string username UK
        string hashed_password
        string role
    }
    
    JOBS {
        string id PK
        string filename
        string file_type
        string file_path
        string output_path
        string xliff_path
        string source_lang
        string target_lang
        string domain
        string status
        float progress
        string progress_message
        int segments_count
        float duration_seconds
        string owner_id FK
        datetime created_at
    }
    
    GLOSSARY_TERM {
        string id PK
        string source_term UK
        string target_term
        string context
        string owner_id FK
        datetime created_at
    }
    
    TRANSLATION_MEMORY {
        string id PK
        string source_text
        string target_text
        string source_lang
        string target_lang
        string domain
        float score
    }
    
    USER ||--o{ JOBS : "owns"
    USER ||--o{ GLOSSARY_TERM : "owns"
```

**Job Status Flow:**
```
queued → extracting → translating → scoring → reconstructing → completed
                                                              → failed
```

---

## 6. Authentication & Authorization

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as FastAPI
    participant DB as SurrealDB

    U->>F: Login (username, password)
    F->>A: POST /api/auth/login
    A->>DB: SELECT user WHERE username=$u
    DB-->>A: User record
    A->>A: bcrypt.checkpw(password, hash)
    A-->>F: JWT Token (7-day expiry)
    F->>F: Store in localStorage
    
    Note over F,A: Subsequent requests
    F->>A: GET /api/jobs + Authorization: Bearer {JWT}
    A->>A: jwt.decode(token, SECRET_KEY)
    A->>DB: Query with owner_id filter
    DB-->>A: Results
    A-->>F: Filtered response
```

- **Password Hashing**: Native `bcrypt` (no passlib) — `$2b$12$` format
- **JWT Tokens**: HS256, 7-day expiry, signed with `SECRET_KEY`
- **Owner Isolation**: Jobs and glossary filtered by `owner_id` — users only see their own data

---

## 7. Storage Architecture

```mermaid
graph TB
    subgraph MinIO ["MinIO S3-Compatible Storage"]
        UB["uploads/<br/>Original files"]
        OB["outputs/<br/>Translated files + XLIFF"]
    end
    
    subgraph Features ["Enterprise Features"]
        RET["Auto-Retention<br/>FILE_RETENTION_DAYS=14"]
        ENC["SSE-C Encryption<br/>AES-256 at rest<br/>(requires HTTPS)"]
        LC["Lifecycle Rules<br/>Auto-expiry"]
    end
    
    MinIO --> Features
```

---

## 8. Performance Tuning

| Setting | Default | Tuning Guide |
|:--------|:--------|:-------------|
| `MAX_CONCURRENT_BATCHES` | `2` | Increase for high-VRAM GPUs |
| `BATCH_MAX_SEGMENTS` | `5` | Lower reduces mismatch risk |
| `BATCH_MAX_CHARS` | `3000` | Tuned for 8K context window |
| `MAX_WORKERS` | `1` | Parallel job processing |
| `TRANSLATION_NUM_CTX` | `4096` | LLM context window |
| `OLLAMA_THINK` | `false` | CoT mode — slower but better quality |