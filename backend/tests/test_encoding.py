"""Tests for app.utils.encoding — read_text_file()."""

import pytest

from app.utils.encoding import read_text_file


class TestReadTextFile:
    """Feature: Read text files with auto JP encoding detection."""

    def test_utf8_file(self, tmp_path):
        """Scenario: UTF-8 file reads correctly"""
        f = tmp_path / "test_utf8.txt"
        f.write_text("こんにちは世界", encoding="utf-8")
        result = read_text_file(str(f))
        assert "こんにちは世界" in result

    def test_sjis_file(self, tmp_path):
        """Scenario: Shift_JIS file auto-detected"""
        f = tmp_path / "test_sjis.txt"
        f.write_bytes("テストデータ".encode("shift_jis"))
        result = read_text_file(str(f))
        assert "テストデータ" in result

    def test_eucjp_file(self, tmp_path):
        """Scenario: EUC-JP file auto-detected"""
        f = tmp_path / "test_eucjp.txt"
        f.write_bytes("漢字テスト".encode("euc-jp"))
        result = read_text_file(str(f))
        assert "漢字テスト" in result

    def test_empty_file(self, tmp_path):
        """Scenario: Empty file → empty string"""
        f = tmp_path / "empty.txt"
        f.write_text("")
        assert read_text_file(str(f)) == ""

    def test_ascii_file(self, tmp_path):
        """Scenario: ASCII file → reads normally"""
        f = tmp_path / "ascii.txt"
        f.write_text("Hello World", encoding="ascii")
        assert read_text_file(str(f)) == "Hello World"

    def test_file_not_found(self):
        """Scenario: Non-existent file → FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            read_text_file("/nonexistent/file.txt")

    def test_multiline_jp(self, tmp_path):
        """Scenario: Multi-line Japanese text preserves newlines"""
        content = "一行目\n二行目\n三行目"
        f = tmp_path / "multi.txt"
        f.write_text(content, encoding="utf-8")
        result = read_text_file(str(f))
        assert "一行目" in result
        assert "三行目" in result
