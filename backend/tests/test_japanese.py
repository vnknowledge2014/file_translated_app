"""Tests for app.utils.japanese — has_japanese() and chunk_text()."""

from app.utils.japanese import has_japanese, chunk_text


class TestHasJapanese:
    """Feature: Detect Japanese text in strings."""

    def test_hiragana(self):
        """Scenario: String contains hiragana → True"""
        assert has_japanese("こんにちは") is True

    def test_katakana(self):
        """Scenario: String contains katakana → True"""
        assert has_japanese("カタカナ") is True

    def test_kanji(self):
        """Scenario: String contains kanji → True"""
        assert has_japanese("漢字テスト") is True

    def test_pure_english(self):
        """Scenario: String is pure English → False"""
        assert has_japanese("Hello World") is False

    def test_pure_vietnamese(self):
        """Scenario: String is Vietnamese → False"""
        assert has_japanese("Xin chào thế giới") is False

    def test_mixed_jp_en(self):
        """Scenario: String has JP + EN mixed → True"""
        assert has_japanese("Hello こんにちは World") is True

    def test_empty_string(self):
        """Scenario: Empty string → False"""
        assert has_japanese("") is False

    def test_none(self):
        """Scenario: None input → False"""
        assert has_japanese(None) is False

    def test_numbers_only(self):
        """Scenario: Only numbers → False"""
        assert has_japanese("12345") is False

    def test_fullwidth_numbers(self):
        """Scenario: Fullwidth JP numbers → True"""
        assert has_japanese("１２３") is True

    def test_formula(self):
        """Scenario: Excel formula → False"""
        assert has_japanese("=SUM(A1:A10)") is False

    def test_url(self):
        """Scenario: URL → False"""
        assert has_japanese("https://example.com") is False


class TestChunkText:
    """Feature: Split text into translation-sized chunks."""

    def test_short_text_single_chunk(self):
        """Scenario: Text shorter than max → 1 chunk"""
        result = chunk_text("短いテキスト", max_chars=100)
        assert len(result) == 1
        assert result[0] == "短いテキスト"

    def test_long_text_multiple_chunks(self):
        """Scenario: Text longer than max → split at sentence boundary"""
        text = "最初の文。二番目の文。三番目の文。四番目の文。"
        result = chunk_text(text, max_chars=20)
        assert len(result) >= 2
        assert "".join(result) == text  # No text lost

    def test_preserves_all_content(self):
        """Scenario: All original text preserved after chunking"""
        text = "テスト" * 100
        chunks = chunk_text(text, max_chars=50)
        assert "".join(chunks) == text

    def test_empty_text(self):
        """Scenario: Empty → empty list"""
        assert chunk_text("") == []

    def test_none_text(self):
        """Scenario: None → empty list"""
        assert chunk_text(None) == []

    def test_splits_at_jp_period(self):
        """Scenario: Splits at Japanese period (。)"""
        text = "文A。文B。文C。文D。"
        chunks = chunk_text(text, max_chars=8)
        assert len(chunks) >= 2
        assert "".join(chunks) == text

    def test_splits_at_newline(self):
        """Scenario: Double newline is a valid split point"""
        text = "パラグラフ1。\n\nパラグラフ2。"
        chunks = chunk_text(text, max_chars=20)
        assert len(chunks) >= 1
        assert "".join(chunks) == text

    def test_hard_break_no_boundary(self):
        """Scenario: No sentence boundary → hard break at max_chars"""
        text = "あ" * 100  # No sentence boundary
        chunks = chunk_text(text, max_chars=30)
        assert len(chunks) >= 4
        assert "".join(chunks) == text
