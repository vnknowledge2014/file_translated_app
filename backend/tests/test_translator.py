"""Tests for app.agent.translator — Batch translation."""

from unittest.mock import AsyncMock

import pytest

from app.agent.translator import Translator, chunk_segments


class TestChunkSegments:
    """Feature: Split segments into translation batches."""

    def test_empty_segments(self):
        assert chunk_segments([]) == []

    def test_single_segment(self):
        segs = [{"text": "テスト"}]
        result = chunk_segments(segs)
        assert len(result) == 1
        assert len(result[0]) == 1

    def test_splits_by_char_count(self):
        """Scenario: Long texts → split by max_chars."""
        segs = [{"text": "あ" * 100} for _ in range(5)]
        result = chunk_segments(segs, max_chars=250, max_segs=100)
        assert len(result) >= 2
        total = sum(len(b) for b in result)
        assert total == 5

    def test_splits_by_segment_count(self):
        """Scenario: Many segments → split by max_segs."""
        segs = [{"text": "短い"} for _ in range(25)]
        result = chunk_segments(segs, max_chars=10000, max_segs=10)
        assert len(result) == 3
        assert len(result[0]) == 10
        assert len(result[1]) == 10
        assert len(result[2]) == 5

    def test_preserves_all_segments(self):
        """Scenario: No segments lost during chunking."""
        segs = [{"text": f"text_{i}"} for i in range(17)]
        result = chunk_segments(segs, max_chars=50, max_segs=5)
        total = sum(len(b) for b in result)
        assert total == 17


@pytest.mark.asyncio
class TestTranslator:
    """Feature: Batch translation via LLM."""

    async def test_translate_batch_success(self):
        """Scenario: Batch translation with matching segment count."""
        client = AsyncMock()
        client.generate = AsyncMock(return_value="Dịch A|||Dịch B")

        translator = Translator(client, "gemma4:e4b")
        segments = [
            {"text": "文A", "location": "p[0]", "type": "body"},
            {"text": "文B", "location": "p[1]", "type": "body"},
        ]
        result = await translator.translate_batch(segments, "docx")

        assert result[0]["translated_text"] == "Dịch A"
        assert result[1]["translated_text"] == "Dịch B"

    async def test_translate_single_segment(self):
        """Scenario: Single segment translation."""
        client = AsyncMock()
        client.generate = AsyncMock(return_value="Xin chào")

        translator = Translator(client, "gemma4:e4b")
        segments = [{"text": "こんにちは", "location": "p[0]", "type": "body"}]
        result = await translator.translate_batch(segments, "docx")

        assert result[0]["translated_text"] == "Xin chào"

    async def test_count_mismatch_fallback(self):
        """Scenario: Count mismatch → falls back to 1-by-1."""
        client = AsyncMock()
        # First call returns wrong count, subsequent calls return single translations
        client.generate = AsyncMock(
            side_effect=["Wrong|||Count|||Extra", "Dịch A", "Dịch B"]
        )

        translator = Translator(client, "gemma4:e4b")
        segments = [
            {"text": "文A", "location": "p[0]", "type": "body"},
            {"text": "文B", "location": "p[1]", "type": "body"},
        ]
        result = await translator.translate_batch(segments, "docx")

        assert result[0]["translated_text"] == "Dịch A"
        assert result[1]["translated_text"] == "Dịch B"

    async def test_empty_segments(self):
        """Scenario: Empty list → no-op."""
        client = AsyncMock()
        translator = Translator(client, "gemma4:e4b")
        result = await translator.translate_batch([], "docx")
        assert result == []
        client.generate.assert_not_called()
