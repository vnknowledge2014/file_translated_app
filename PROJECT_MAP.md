# Project Map (Agent-Friendly Context)

> This document provides semantic summaries, structural metadata, and dependency relationships for all core project files.

## 1. Core Application (backend/app)

### `backend/app/__init__.py`
- **Purpose:** No docstring provided.

### `backend/app/agent/__init__.py`
- **Purpose:** Agent package — orchestrator, extractor, translator, reconstructor.

### `backend/app/agent/confidence.py`
- **Purpose:** Multi-signal heuristic confidence scorer for translation quality.
- **Functions:** score_segment, classify_segments

### `backend/app/agent/extractor.py`
- **Purpose:** Deterministic text extraction for all supported document formats.
- **Functions:** _is_translatable, _dedup_segments, _split_long_segment, extract_docx, extract_xlsx

### `backend/app/agent/orchestrator.py`
- **Purpose:** Orchestrator — fully deterministic Extract → Translate → Reconstruct pipeline.
- **Classes:** Orchestrator

### `backend/app/agent/prompt_router.py`
- **Purpose:** Prompt Router for Context Engineering Matrix.
- **Classes:** PromptRouter

### `backend/app/agent/reconstructor/__init__.py`
- **Purpose:** Deterministic document reconstruction — per-format modules.
- **Functions:** reconstruct_document

### `backend/app/agent/reconstructor/_common.py`
- **Purpose:** Shared utilities for deterministic document reconstruction.
- **Functions:** build_translation_map, replace_in_text

### `backend/app/agent/reconstructor/_ooxml.py`
- **Purpose:** Shared OOXML (Office Open XML) processing utilities.
- **Functions:** register_namespaces, register_document_namespaces, deserialize_tags_to_xml, replace_paragraph_runs, _is_viet_char

### `backend/app/agent/reconstructor/docx.py`
- **Purpose:** DOCX (Word) deterministic reconstruction.
- **Functions:** _is_docx_xml, reconstruct_docx

### `backend/app/agent/reconstructor/plaintext.py`
- **Purpose:** Plaintext (txt, md, csv) deterministic reconstruction.
- **Functions:** _box_top_re, _box_bottom_re, _split_cells, _rebuild_border, _rebuild_cell_line

### `backend/app/agent/reconstructor/pptx.py`
- **Purpose:** PPTX (PowerPoint) deterministic reconstruction.
- **Functions:** _is_pptx_xml, reconstruct_pptx

### `backend/app/agent/reconstructor/xlsx.py`
- **Purpose:** XLSX (Excel) deterministic reconstruction.
- **Functions:** _sanitize_sheet_name, _build_sheet_name_map, _safe_replace, _needs_quoting, _fix_sheet_refs_in_text

### `backend/app/agent/translator.py`
- **Purpose:** Batch translation via LLM with ||| delimiter.
- **Classes:** Translator
- **Functions:** _load_prompt_file, chunk_segments

### `backend/app/agent/xliff.py`
- **Purpose:** XLIFF bilingual translation exchange — dual-version (1.2 + 2.1).
- **Functions:** _tags_to_xliff_v12, _xliff_v12_to_tags, _tags_to_xliff_v21, _xliff_v21_to_tags, detect_xliff_version

### `backend/app/config.py`
- **Purpose:** Application configuration loaded from .env file and environment variables.
- **Classes:** Settings
- **Functions:** _load_dotenv, _env, _env_int, _env_float

### `backend/app/database.py`
- **Purpose:** Async SQLite database with CRUD operations for job tracking.

### `backend/app/domains.py`
- **Purpose:** Domain Registry and Profile definitions for multi-domain translation.
- **Classes:** DomainProfile
- **Functions:** get_domain, list_supported_domains

### `backend/app/languages.py`
- **Purpose:** Language Registry — profiles for all supported languages.
- **Classes:** LanguageProfile
- **Functions:** _register, get_language, get_language_name, list_languages

### `backend/app/llm/__init__.py`
- **Purpose:** LLM client abstraction layer.

### `backend/app/llm/base.py`
- **Purpose:** Abstract base class for LLM clients.
- **Classes:** LLMClient

### `backend/app/llm/factory.py`
- **Purpose:** Factory for creating LLM client instances based on backend configuration.
- **Functions:** create_llm_client

### `backend/app/main.py`
- **Purpose:** FastAPI application with lifespan, CORS, and route registration.

### `backend/app/models.py`
- **Purpose:** SQLAlchemy ORM models for the multilingual translation tool.
- **Classes:** Base, Job, SegmentReview, JobAttempt, GlossaryTerm

### `backend/app/ollama/__init__.py`
- **Purpose:** Ollama client package.

### `backend/app/ollama/client.py`
- **Purpose:** Async HTTP client for Ollama REST API.
- **Classes:** OllamaClient

### `backend/app/ollama/exceptions.py`
- **Purpose:** Custom exceptions for Ollama client.
- **Classes:** OllamaError, OllamaConnectionError, OllamaTimeoutError, OllamaModelError

### `backend/app/ollama/model_manager.py`
- **Purpose:** Model loading/unloading manager for 16GB RAM constraint.
- **Classes:** ModelManager

### `backend/app/prompts/rules/formats/ooxml.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/rules/formats/plaintext.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/domains/finance.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/domains/general.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/domains/it.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/domains/it_software.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/domains/legal.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/domains/marketing.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/domains/medical.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/ar.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/de.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/en.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/es.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/fr.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/hi.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/id.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/ja.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/ko.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/pt.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/ru.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/th.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/vi.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/zh-TW.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/source/zh.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/ar.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/de.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/en.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/es.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/fr.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/hi.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/id.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/ja.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/ko.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/pt.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/ru.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/th.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/vi.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/zh-TW.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/skills/languages/target/zh.md`
- **Type:** Non-Python resource/config file.

### `backend/app/routes/__init__.py`
- **Purpose:** Routes package.

### `backend/app/routes/download.py`
- **Purpose:** Download route — GET /api/download/{job_id} → serve output file.

### `backend/app/routes/glossary.py`
- **Purpose:** Glossary routes — GET, POST (upload CSV), DELETE.

### `backend/app/routes/jobs.py`
- **Purpose:** Job listing and detail routes.

### `backend/app/routes/segments.py`
- **Purpose:** Segments API — GET/PUT/POST for Review Editor.
- **Classes:** SegmentEdit

### `backend/app/routes/upload.py`
- **Purpose:** Upload route — POST /api/upload → save file + create job + queue to worker pool.

### `backend/app/routes/xliff.py`
- **Purpose:** XLIFF routes — import reviewed XLIFF and download XLIFF for jobs.

### `backend/app/utils/__init__.py`
- **Purpose:** No docstring provided.

### `backend/app/utils/encoding.py`
- **Purpose:** Japanese encoding detection and text file reading.
- **Functions:** read_text_file

### `backend/app/utils/file_detect.py`
- **Purpose:** File type detection for supported document formats.
- **Functions:** detect_file_type, get_supported_types

### `backend/app/utils/language_detect.py`
- **Purpose:** Universal language detection and text utilities.
- **Functions:** _build_char_regex, _strip_shared_symbols, has_source_language, detect_language, extract_english_terms

### `backend/app/worker.py`
- **Purpose:** Job Worker Pool — bounded concurrency for translation pipelines.
- **Classes:** JobItem, WorkerPool

## 2. Tests (backend/tests)

### `backend/tests/__init__.py`
- **Purpose:** No docstring provided.

### `backend/tests/test_api.py`
- **Purpose:** Tests for FastAPI routes — upload, jobs, download, health.
- **Classes:** TestHealthEndpoint, TestUploadEndpoint, TestJobsEndpoint, TestDownloadEndpoint
- **Functions:** client

### `backend/tests/test_confidence.py`
- **Purpose:** Tests for multi-signal confidence scorer.
- **Classes:** TestScoreSegment, TestClassifySegments

### `backend/tests/test_config.py`
- **Purpose:** Tests for app.config — Settings.
- **Classes:** TestSettings

### `backend/tests/test_database.py`
- **Purpose:** Tests for app.database — async SQLite with job tracking.
- **Classes:** TestDatabase

### `backend/tests/test_e2e_pipeline.py`
- **Purpose:** No docstring provided.
- **Functions:** test_full_pipeline_xlsx

### `backend/tests/test_encoding.py`
- **Purpose:** Tests for app.utils.encoding — read_text_file().
- **Classes:** TestReadTextFile

### `backend/tests/test_extractor.py`
- **Purpose:** Tests for deterministic document extraction.
- **Classes:** TestIsTranslatable, TestDedupSegments, TestExtractDocx, TestExtractXlsx, TestExtractPptx

### `backend/tests/test_file_detect.py`
- **Purpose:** Tests for app.utils.file_detect — detect_file_type().
- **Classes:** TestDetectFileType, TestGetSupportedTypes

### `backend/tests/test_grid_expansion.py`
- **Purpose:** No docstring provided.
- **Functions:** test_visual_width, test_insert_at_visual_col, test_reconstruct_plaintext_diagram

### `backend/tests/test_language_detect.py`
- **Purpose:** Tests for app.utils.language_detect — universal language detection and chunking.
- **Classes:** TestHasSourceLanguage, TestDetectLanguage, TestAnalyzeSegment, TestChunkText

### `backend/tests/test_model_manager.py`
- **Purpose:** Tests for app.ollama.model_manager — Model switching.
- **Classes:** TestModelManager
- **Functions:** mock_ollama_client

### `backend/tests/test_native_zip_xml.py`
- **Purpose:** No docstring provided.
- **Functions:** test_xlsx_native_extraction, test_zero_corruption_clone, test_tag_validation_logic

### `backend/tests/test_ollama_client.py`
- **Purpose:** Tests for app.ollama.client — Async HTTP client for Ollama API.
- **Classes:** TestOllamaClient
- **Functions:** mock_transport

### `backend/tests/test_reconstructor.py`
- **Purpose:** Tests for deterministic document reconstruction.
- **Classes:** TestBuildTranslationMap, TestReplaceInText, TestReconstructDocx, TestReconstructXlsx, TestReconstructPptx

### `backend/tests/test_translator.py`
- **Purpose:** Tests for app.agent.translator — Batch translation.
- **Classes:** TestChunkSegments, TestTranslator

### `backend/tests/test_xliff.py`
- **Purpose:** Tests for XLIFF dual-version bilingual translation exchange.
- **Classes:** TestExportV12, TestExportV21, TestImportRoundtrip, TestVersionDetect, TestInlineTagsV12

## 3. Configuration & Root

### `.dockerignore`
- **Type:** Non-Python resource/config file.

### `.env`
- **Type:** Non-Python resource/config file.

### `.env.example`
- **Type:** Non-Python resource/config file.

### `.gitignore`
- **Type:** Non-Python resource/config file.

### `Dockerfile`
- **Type:** Non-Python resource/config file.

### `PROJECT_MAP.md`
- **Type:** Non-Python resource/config file.

### `README.md`
- **Type:** Non-Python resource/config file.

### `backend/conftest.py`
- **Purpose:** Shared test fixtures for the multilingual translation tool.
- **Functions:** sample_jp_text, sample_vi_text, sample_mixed_text

### `backend/pytest.ini`
- **Type:** Non-Python resource/config file.

### `backend/requirements.txt`
- **Type:** Non-Python resource/config file.

### `docker-compose.yml`
- **Type:** Non-Python resource/config file.

### `docs/architecture.md`
- **Type:** Non-Python resource/config file.

### `frontend/.gitignore`
- **Type:** Non-Python resource/config file.

### `frontend/.npmrc`
- **Type:** Non-Python resource/config file.

### `frontend/README.md`
- **Type:** Non-Python resource/config file.

### `frontend/messages/en.json`
- **Type:** Non-Python resource/config file.

### `frontend/messages/ja.json`
- **Type:** Non-Python resource/config file.

### `frontend/messages/vi.json`
- **Type:** Non-Python resource/config file.

### `frontend/package-lock.json`
- **Type:** Non-Python resource/config file.

### `frontend/package.json`
- **Type:** Non-Python resource/config file.

### `frontend/src/app.css`
- **Type:** Non-Python resource/config file.

### `frontend/src/app.d.ts`
- **Type:** Non-Python resource/config file.

### `frontend/src/app.html`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/api.ts`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/assets/favicon.svg`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/components/BilingualEditor.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/components/GlossaryTable.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/components/JobCard.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/components/LanguageBar.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/components/LanguageSwitcher.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/components/UploadZone.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/index.ts`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/stores/config.ts`
- **Type:** Non-Python resource/config file.

### `frontend/src/lib/stores/i18n.ts`
- **Type:** Non-Python resource/config file.

### `frontend/src/routes/+layout.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/src/routes/+layout.ts`
- **Type:** Non-Python resource/config file.

### `frontend/src/routes/+page.svelte`
- **Type:** Non-Python resource/config file.

### `frontend/static/robots.txt`
- **Type:** Non-Python resource/config file.

### `frontend/svelte.config.js`
- **Type:** Non-Python resource/config file.

### `frontend/tsconfig.json`
- **Type:** Non-Python resource/config file.

### `frontend/vite.config.ts`
- **Type:** Non-Python resource/config file.

### `i18n_manager.py`
- **Purpose:** No docstring provided.
- **Functions:** main

### `ui_translations.xlsx`
- **Type:** Non-Python resource/config file.

