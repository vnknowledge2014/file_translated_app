# Project Map (Agent-Friendly Context)

> This document provides semantic summaries, structural metadata, and dependency relationships for all core project files.

## 0. Execution Flow (Pipeline)
The core translation process follows a strictly deterministic sequential pipeline:
1. **Web Upload:** `backend/app/routes/upload.py` accepts the file.
2. **Orchestration:** `backend/app/agent/orchestrator.py` manages jobs and retries.
3. **Extraction:** `backend/app/agent/extractor.py` strips OOXML/JSON/Markdown into clean translation segments.
4. **Translation:** `backend/app/agent/translator.py` batches segments to Ollama via HTTP.
5. **Reconstruction:** `backend/app/agent/reconstructor/*.py` puts translated strings back into exactly the right structure.

## 1. Core Application (backend/app)


### `backend/app/__init__.py`
- **Purpose:** No docstring provided.

### `backend/app/agent/__init__.py`
- **Purpose:** Agent package — orchestrator, extractor, translator, reconstructor.

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
- **Functions:** register_namespaces, deserialize_tags_to_xml, replace_paragraph_runs, preserve_xml_declaration

### `backend/app/agent/reconstructor/docx.py`
- **Purpose:** DOCX (Word) deterministic reconstruction.
- **Functions:** _is_docx_xml, reconstruct_docx

### `backend/app/agent/reconstructor/plaintext.py`
- **Purpose:** Plaintext (txt, md, csv) deterministic reconstruction.
- **Functions:** visual_width, insert_at_visual_col, _truncate_to_visual_width, _strip_hallucinated_prefix, reconstruct_plaintext

### `backend/app/agent/reconstructor/pptx.py`
- **Purpose:** PPTX (PowerPoint) deterministic reconstruction.
- **Functions:** _is_pptx_xml, reconstruct_pptx

### `backend/app/agent/reconstructor/xlsx.py`
- **Purpose:** XLSX (Excel) deterministic reconstruction.
- **Functions:** _sanitize_sheet_name, _build_sheet_name_map, _safe_replace, _fix_sheet_refs_in_text, _fix_formula_sheet_refs

### `backend/app/agent/translator.py`
- **Purpose:** Batch translation via LLM with ||| delimiter.
- **Classes:** Translator
- **Functions:** _load_omni_skill, build_glossary_prompt, chunk_segments

### `backend/app/config.py`
- **Purpose:** Application configuration loaded from environment variables.
- **Classes:** Settings

### `backend/app/database.py`
- **Purpose:** Async SQLite database with CRUD operations for job tracking.

### `backend/app/main.py`
- **Purpose:** FastAPI application with lifespan, CORS, and route registration.

### `backend/app/models.py`
- **Purpose:** SQLAlchemy ORM models for the JP→VI translation tool.
- **Classes:** Base, Job, JobAttempt, GlossaryTerm

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

### `backend/app/prompts/inline_tag_translation_rule.md`
- **Type:** Non-Python resource/config file.

### `backend/app/routes/__init__.py`
- **Purpose:** Routes package.

### `backend/app/routes/download.py`
- **Purpose:** Download route — GET /api/download/{job_id} → serve output file.

### `backend/app/routes/jobs.py`
- **Purpose:** Job listing and detail routes.

### `backend/app/routes/upload.py`
- **Purpose:** Upload route — POST /api/upload → save file + create job + start pipeline.
- **Functions:** _on_pipeline_done

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

## 3. Configuration & Root


### `Dockerfile`
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

### `docker-compose.yml`
- **Type:** Non-Python resource/config file.

### `docs/architecture.md`
- **Type:** Non-Python resource/config file.

### `e2e_test.log`
- **Type:** Non-Python resource/config file.

### `frontend/index.html`
- **Type:** Non-Python resource/config file.

