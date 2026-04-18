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
- **Functions:** _sanitize_sheet_name, _build_sheet_name_map, _safe_replace, _fix_sheet_refs_in_text, _fix_formula_sheet_refs

### `backend/app/agent/translator.py`
- **Purpose:** Batch translation via LLM with ||| delimiter.
- **Classes:** Translator
- **Functions:** _load_prompt_file, build_glossary_prompt, chunk_segments

### `backend/app/agent/xliff.py`
- **Purpose:** XLIFF bilingual translation exchange — dual-version (1.2 + 2.1).
- **Functions:** _tags_to_xliff_v12, _xliff_v12_to_tags, _tags_to_xliff_v21, _xliff_v21_to_tags, detect_xliff_version

### `backend/app/config.py`
- **Purpose:** Application configuration loaded from .env file and environment variables.
- **Classes:** Settings
- **Functions:** _load_dotenv, _env, _env_int, _env_float

### `backend/app/database.py`
- **Purpose:** Async SQLite database with CRUD operations for job tracking.

### `backend/app/main.py`
- **Purpose:** FastAPI application with lifespan, CORS, and route registration.

### `backend/app/models.py`
- **Purpose:** SQLAlchemy ORM models for the JP→VI translation tool.
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

### `backend/app/prompts/ooxml_tag_rules.md`
- **Type:** Non-Python resource/config file.

### `backend/app/prompts/plaintext_rules.md`
- **Type:** Non-Python resource/config file.

### `backend/app/routes/__init__.py`
- **Purpose:** Routes package.

### `backend/app/routes/download.py`
- **Purpose:** Download route — GET /api/download/{job_id} → serve output file.

### `backend/app/routes/jobs.py`
- **Purpose:** Job listing and detail routes.

### `backend/app/routes/segments.py`
- **Purpose:** Segments API — GET/PUT/POST for Review Editor.
- **Classes:** SegmentEdit

### `backend/app/routes/upload.py`
- **Purpose:** Upload route — POST /api/upload → save file + create job + start pipeline.
- **Functions:** _on_pipeline_done

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

### `backend/app/utils/japanese.py`
- **Purpose:** Japanese text detection and chunking utilities.
- **Functions:** _strip_jp_symbols, has_japanese, chunk_text

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

### `backend/tests/test_japanese.py`
- **Purpose:** Tests for app.utils.japanese — has_japanese() and chunk_text().
- **Classes:** TestHasJapanese, TestChunkText

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

### `.DS_Store`
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
- **Purpose:** Shared test fixtures for the JP→VI translation tool.
- **Functions:** sample_jp_text, sample_vi_text, sample_mixed_text

### `backend/pytest.ini`
- **Type:** Non-Python resource/config file.

### `backend/requirements.txt`
- **Type:** Non-Python resource/config file.

### `backend/server.log`
- **Type:** Non-Python resource/config file.

### `docker-compose.yml`
- **Type:** Non-Python resource/config file.

### `docs/architecture.md`
- **Type:** Non-Python resource/config file.

### `frontend/index.html`
- **Type:** Non-Python resource/config file.

### `samples/.DS_Store`
- **Type:** Non-Python resource/config file.

### `samples/01_requirements.md`
- **Type:** Non-Python resource/config file.

### `samples/API一覧.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/FreeBSD AI Hack Report (Japanese).pptx`
- **Type:** Non-Python resource/config file.

### `samples/HROne様SSO構成.pdf`
- **Type:** Non-Python resource/config file.

### `samples/NDD_skill_sheet_20260408.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/japanese-ja.docx`
- **Type:** Non-Python resource/config file.

### `samples/sample.txt`
- **Type:** Non-Python resource/config file.

### `samples/translate_xlsx_zip.py`
- **Purpose:** Translate xlsx at ZIP/XML level - FIXED version.
- **Functions:** translate_shared_strings_via_regex, update_formula_refs, rename_sheets_in_workbook_via_regex, main

### `samples/translated/01_requirements_vi.md`
- **Type:** Non-Python resource/config file.

### `samples/translated/API一覧_vi.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/translated/FreeBSD_AI_Hack_Report_vi.pptx`
- **Type:** Non-Python resource/config file.

### `samples/translated/NDD_skill_sheet_20260408_vi.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/translated/japanese-vi.docx`
- **Type:** Non-Python resource/config file.

### `samples/translated/sample.txt`
- **Type:** Non-Python resource/config file.

### `samples/translated/【基本設計書】依頼届出_雇保給付金申請_高年齢_画面設計_202510_vi.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/~$【基本設計書】ファイル定義書_書類提出依頼_20250520.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/~$【基本設計書】依頼届出_雇保給付金申請_高年齢_画面設計_202510.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/【基本設計書】ファイル定義書_書類提出依頼_20250520.xlsx`
- **Type:** Non-Python resource/config file.

### `samples/【基本設計書】依頼届出_雇保給付金申請_高年齢_画面設計_202510.xlsx`
- **Type:** Non-Python resource/config file.

