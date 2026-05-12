"""Tests for app.utils.language_detect — universal language detection and chunking.

Covers: has_source_language(), detect_language(), analyze_segment(), chunk_text()
"""

from app.utils.language_detect import (
    has_source_language,
    detect_language,
    analyze_segment,
    chunk_text,
)


class TestHasSourceLanguage:
    """Feature: Detect source language characters in strings."""

    # ── Japanese ──

    def test_hiragana(self):
        """Scenario: String contains hiragana → True"""
        assert has_source_language("こんにちは", "ja") is True

    def test_katakana(self):
        """Scenario: String contains katakana → True"""
        assert has_source_language("カタカナ", "ja") is True

    def test_kanji(self):
        """Scenario: String contains kanji → True"""
        assert has_source_language("漢字テスト", "ja") is True

    def test_pure_english(self):
        """Scenario: String is pure English → False for JA"""
        assert has_source_language("Hello World", "ja") is False

    def test_pure_vietnamese(self):
        """Scenario: String is Vietnamese → False for JA"""
        assert has_source_language("Xin chào thế giới", "ja") is False

    def test_mixed_jp_en(self):
        """Scenario: String has JP + EN mixed → True for JA"""
        assert has_source_language("Hello こんにちは World", "ja") is True

    def test_empty_string(self):
        """Scenario: Empty string → False"""
        assert has_source_language("", "ja") is False

    def test_none(self):
        """Scenario: None input → False"""
        assert has_source_language(None, "ja") is False

    def test_numbers_only(self):
        """Scenario: Only numbers → False"""
        assert has_source_language("12345", "ja") is False

    def test_fullwidth_numbers(self):
        """Scenario: Fullwidth JP numbers → True"""
        assert has_source_language("１２３", "ja") is True

    def test_formula(self):
        """Scenario: Excel formula → False"""
        assert has_source_language("=SUM(A1:A10)", "ja") is False

    def test_url(self):
        """Scenario: URL → False"""
        assert has_source_language("https://example.com", "ja") is False

    # ── Other languages ──

    def test_chinese_simplified(self):
        """Scenario: Chinese characters detected"""
        assert has_source_language("这是测试", "zh") is True

    def test_korean(self):
        """Scenario: Korean characters detected"""
        assert has_source_language("안녕하세요", "ko") is True

    def test_russian(self):
        """Scenario: Cyrillic characters detected"""
        assert has_source_language("Привет мир", "ru") is True

    def test_arabic(self):
        """Scenario: Arabic characters detected"""
        assert has_source_language("مرحبا", "ar") is True

    def test_thai(self):
        """Scenario: Thai characters detected"""
        assert has_source_language("สวัสดี", "th") is True


class TestDetectLanguage:
    """Feature: Auto-detect dominant language of text."""

    def test_detect_japanese(self):
        """Scenario: Text with kana → detected as JA"""
        assert detect_language("これはテストです") == "ja"

    def test_detect_chinese(self):
        """Scenario: Pure kanji (no kana) → detected as ZH"""
        assert detect_language("这是测试") == "zh"

    def test_detect_korean(self):
        """Scenario: Hangul text → detected as KO"""
        assert detect_language("안녕하세요") == "ko"

    def test_detect_russian(self):
        """Scenario: Cyrillic text → detected as RU"""
        assert detect_language("Привет мир") == "ru"

    def test_cjk_disambiguation_with_kana(self):
        """Scenario: Kanji + kana → JA not ZH"""
        assert detect_language("管理画面のテスト") == "ja"

    def test_cjk_disambiguation_pure_kanji(self):
        """Scenario: Pure kanji without kana → ZH"""
        assert detect_language("管理测试") == "zh"

    def test_empty_returns_none(self):
        assert detect_language("") is None

    def test_none_returns_none(self):
        assert detect_language(None) is None


class TestAnalyzeSegment:
    """Feature: Analyze language composition of mixed-language segments."""

    def test_pure_japanese(self):
        """Scenario: All Japanese text"""
        result = analyze_segment("こんにちは世界")
        assert result["dominant"] == "ja"
        assert result["has_english"] is False

    def test_jp_with_english_terms_it_domain(self):
        """Scenario: Japanese with embedded English technical terms in IT domain"""
        result = analyze_segment(
            "APIキーを設定してDockerコンテナを起動する", domain_code="it"
        )
        assert result["dominant"] == "ja"
        assert result["has_english"] is True
        assert "API" in result["preserve_terms"]
        assert "Docker" in result["preserve_terms"]

    def test_jp_with_english_terms_general_domain(self):
        """Scenario: English terms in General domain should NOT be preserved automatically unless explicitly requested or recognized."""
        # API and Docker might not be preserved in general domain since it doesn't aggressively preserve
        result = analyze_segment(
            "APIキーを設定してDockerコンテナを起動する", domain_code="general"
        )
        assert result["dominant"] == "ja"
        assert result["has_english"] is True
        assert len(result["preserve_terms"]) == 0

    def test_medical_domain(self):
        """Scenario: Medical domain preserves specific Latin/English acronyms like DNA"""
        result = analyze_segment("患者のDNAサンプルを分析する", domain_code="medical")
        assert "DNA" in result["preserve_terms"]

    def test_pure_english(self):
        """Scenario: Pure English text"""
        result = analyze_segment("Hello World")
        assert result["dominant"] is None or result["dominant"] == "en"
        assert result["has_english"] is True

    def test_mixed_chinese_english(self):
        """Scenario: Chinese with English terms"""
        result = analyze_segment("使用Docker部署API服务")
        assert result["dominant"] == "zh"
        assert result["has_english"] is True
        assert "Docker" in result["english_terms"]
        assert "API" in result["english_terms"]

    def test_empty(self):
        result = analyze_segment("")
        assert result["dominant"] is None
        assert result["has_english"] is False
        assert result["english_terms"] == []


class TestChunkText:
    """Feature: Split text into translation-sized chunks."""

    def test_short_text_single_chunk(self):
        """Scenario: Text shorter than max → 1 chunk"""
        result = chunk_text("短いテキスト", lang_code="ja", max_chars=100)
        assert len(result) == 1
        assert result[0] == "短いテキスト"

    def test_long_text_multiple_chunks(self):
        """Scenario: Text longer than max → split at sentence boundary"""
        text = "最初の文。二番目の文。三番目の文。四番目の文。"
        result = chunk_text(text, lang_code="ja", max_chars=20)
        assert len(result) >= 2
        assert "".join(result) == text  # No text lost

    def test_preserves_all_content(self):
        """Scenario: All original text preserved after chunking"""
        text = "テスト" * 100
        chunks = chunk_text(text, lang_code="ja", max_chars=50)
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
        chunks = chunk_text(text, lang_code="ja", max_chars=8)
        assert len(chunks) >= 2
        assert "".join(chunks) == text

    def test_splits_at_newline(self):
        """Scenario: Double newline is a valid split point"""
        text = "パラグラフ1。\n\nパラグラフ2。"
        chunks = chunk_text(text, lang_code="ja", max_chars=20)
        assert len(chunks) >= 1
        assert "".join(chunks) == text

    def test_hard_break_no_boundary(self):
        """Scenario: No sentence boundary → hard break at max_chars"""
        text = "あ" * 100  # No sentence boundary
        chunks = chunk_text(text, lang_code="ja", max_chars=30)
        assert len(chunks) >= 4
        assert "".join(chunks) == text
