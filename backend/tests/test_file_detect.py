"""Tests for app.utils.file_detect — detect_file_type()."""

from app.utils.file_detect import detect_file_type, get_supported_types


class TestDetectFileType:
    """Feature: Detect supported document file types."""

    def test_docx(self):
        assert detect_file_type("report.docx") == "docx"

    def test_xlsx(self):
        assert detect_file_type("data.xlsx") == "xlsx"

    def test_pptx(self):
        assert detect_file_type("slides.pptx") == "pptx"

    def test_pdf(self):
        assert detect_file_type("manual.pdf") == "pdf"

    def test_md(self):
        assert detect_file_type("README.md") == "md"

    def test_txt(self):
        assert detect_file_type("notes.txt") == "txt"

    def test_csv(self):
        assert detect_file_type("data.csv") == "csv"

    def test_unsupported_png(self):
        """Scenario: Unknown extension → None"""
        assert detect_file_type("image.png") is None

    def test_unsupported_exe(self):
        assert detect_file_type("virus.exe") is None

    def test_case_insensitive_upper(self):
        """Scenario: .DOCX → 'docx'"""
        assert detect_file_type("FILE.DOCX") == "docx"

    def test_case_insensitive_mixed(self):
        assert detect_file_type("data.XlSx") == "xlsx"

    def test_path_with_dirs(self):
        """Scenario: Full path → only extension matters"""
        assert detect_file_type("/data/uploads/2026/report.pdf") == "pdf"

    def test_empty_string(self):
        assert detect_file_type("") is None

    def test_none(self):
        assert detect_file_type(None) is None

    def test_no_extension(self):
        assert detect_file_type("Makefile") is None


class TestGetSupportedTypes:
    """Feature: List all supported file types."""

    def test_returns_set(self):
        types = get_supported_types()
        assert isinstance(types, set)

    def test_contains_all_7_types(self):
        types = get_supported_types()
        assert len(types) == 7
        assert "docx" in types
        assert "xlsx" in types
        assert "pptx" in types
        assert "pdf" in types
        assert "md" in types
        assert "txt" in types
        assert "csv" in types

    def test_returns_copy(self):
        """Scenario: Modifying returned set doesn't affect original"""
        types = get_supported_types()
        types.add("zip")
        assert "zip" not in get_supported_types()
