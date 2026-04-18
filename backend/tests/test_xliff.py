"""Tests for XLIFF dual-version bilingual translation exchange."""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from app.agent.xliff import (
    export_xliff,
    import_xliff,
    merge_xliff_into_segments,
    detect_xliff_version,
    _tags_to_xliff_v12,
    _xliff_v12_to_tags,
    _tags_to_xliff_v21,
    _xliff_v21_to_tags,
)

_NS_V12 = "urn:oasis:names:tc:xliff:document:1.2"
_NS_V21 = "urn:oasis:names:tc:xliff:document:2.1"


# ═══════════════════════════════════════════════════════════════════
# XLIFF 1.2 Export Tests
# ═══════════════════════════════════════════════════════════════════

class TestExportV12:
    def _export(self, segments, filename="test.docx", file_type="docx"):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.xlf")
            result = export_xliff(segments, filename, file_type, path, version="1.2")
            assert os.path.exists(result)
            tree = ET.parse(result)
            return tree, result

    def test_basic_structure(self):
        """Export 3 segments → valid XLIFF 1.2 XML."""
        segs = [
            {"text": "作成者", "location": "p[0]", "type": "paragraph"},
            {"text": "項目名", "location": "p[1]", "type": "paragraph"},
            {"text": "説明", "location": "p[2]", "type": "paragraph"},
        ]
        tree, _ = self._export(segs)
        root = tree.getroot()
        assert root.get("version") == "1.2"
        file_el = root.find(f"{{{_NS_V12}}}file")
        assert file_el.get("original") == "test.docx"
        assert file_el.get("source-language") == "ja"
        tus = list(root.iter(f"{{{_NS_V12}}}trans-unit"))
        assert len(tus) == 3

    def test_with_target_translated(self):
        """Translated segments have state='translated'."""
        segs = [{"text": "作成者", "translated_text": "Người tạo"}]
        tree, _ = self._export(segs)
        tu = list(tree.getroot().iter(f"{{{_NS_V12}}}trans-unit"))[0]
        target = tu.find(f"{{{_NS_V12}}}target")
        assert target.text == "Người tạo"
        assert target.get("state") == "translated"

    def test_without_target_new(self):
        """Untranslated segments have state='new'."""
        segs = [{"text": "作成者"}]
        tree, _ = self._export(segs)
        tu = list(tree.getroot().iter(f"{{{_NS_V12}}}trans-unit"))[0]
        target = tu.find(f"{{{_NS_V12}}}target")
        assert target.get("state") == "new"

    def test_low_confidence_needs_review(self):
        """Low confidence → state='needs-review-translation'."""
        segs = [{"text": "テスト", "translated_text": "Kiểm tra", "confidence": 0.4}]
        tree, _ = self._export(segs)
        tu = list(tree.getroot().iter(f"{{{_NS_V12}}}trans-unit"))[0]
        target = tu.find(f"{{{_NS_V12}}}target")
        assert target.get("state") == "needs-review-translation"

    def test_metadata_notes(self):
        """location/type stored as <note> elements."""
        segs = [{"text": "テスト", "location": "xl/ss:si[5]", "type": "cell"}]
        tree, _ = self._export(segs)
        tu = list(tree.getroot().iter(f"{{{_NS_V12}}}trans-unit"))[0]
        notes = tu.findall(f"{{{_NS_V12}}}note")
        note_texts = [n.text for n in notes]
        assert "location: xl/ss:si[5]" in note_texts
        assert "type: cell" in note_texts

    def test_special_chars(self):
        """XML special characters are properly escaped."""
        segs = [{"text": "A & B", "translated_text": "A < B"}]
        tree, _ = self._export(segs)
        tu = list(tree.getroot().iter(f"{{{_NS_V12}}}trans-unit"))[0]
        source = tu.find(f"{{{_NS_V12}}}source")
        target = tu.find(f"{{{_NS_V12}}}target")
        assert source.text == "A & B"
        assert target.text == "A < B"

    def test_empty_segments(self):
        """Empty segment list → valid XLIFF with no trans-units."""
        tree, _ = self._export([])
        tus = list(tree.getroot().iter(f"{{{_NS_V12}}}trans-unit"))
        assert len(tus) == 0

    def test_skips_empty_text(self):
        """Segments with empty/whitespace text are skipped."""
        segs = [{"text": ""}, {"text": "   "}, {"text": "テスト"}]
        tree, _ = self._export(segs)
        tus = list(tree.getroot().iter(f"{{{_NS_V12}}}trans-unit"))
        assert len(tus) == 1

    def test_xlsx_datatype(self):
        """File type is encoded in datatype attribute."""
        segs = [{"text": "テスト"}]
        tree, _ = self._export(segs, filename="data.xlsx", file_type="xlsx")
        file_el = tree.getroot().find(f"{{{_NS_V12}}}file")
        assert file_el.get("datatype") == "x-xlsx"


# ═══════════════════════════════════════════════════════════════════
# XLIFF 2.1 Export Tests
# ═══════════════════════════════════════════════════════════════════

class TestExportV21:
    def _export(self, segments, filename="test.docx", file_type="docx"):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.xlf")
            result = export_xliff(segments, filename, file_type, path, version="2.1")
            assert os.path.exists(result)
            tree = ET.parse(result)
            return tree, result

    def test_basic_structure(self):
        """Export segments → valid XLIFF 2.1 XML."""
        segs = [
            {"text": "作成者", "translated_text": "Người tạo"},
            {"text": "項目名"},
        ]
        tree, _ = self._export(segs)
        root = tree.getroot()
        assert root.get("version") == "2.1"
        assert root.get("srcLang") == "ja"
        assert root.get("trgLang") == "vi"
        units = list(root.iter(f"{{{_NS_V21}}}unit"))
        assert len(units) == 2

    def test_segment_state(self):
        """Translated → state='translated', empty → state='initial'."""
        segs = [
            {"text": "テスト", "translated_text": "Kiểm tra"},
            {"text": "未翻訳"},
        ]
        tree, _ = self._export(segs)
        segments = list(tree.getroot().iter(f"{{{_NS_V21}}}segment"))
        assert segments[0].get("state") == "translated"
        assert segments[1].get("state") == "initial"

    def test_skips_empty(self):
        """Empty text segments skipped."""
        segs = [{"text": ""}, {"text": "テスト"}]
        tree, _ = self._export(segs)
        units = list(tree.getroot().iter(f"{{{_NS_V21}}}unit"))
        assert len(units) == 1


# ═══════════════════════════════════════════════════════════════════
# Import + Roundtrip Tests
# ═══════════════════════════════════════════════════════════════════

class TestImportRoundtrip:
    def _roundtrip(self, segments, version="1.2"):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xlf")
            export_xliff(segments, "test.docx", "docx", path, version=version)
            return import_xliff(path)

    def test_roundtrip_v12(self):
        """XLIFF 1.2: Export → Import → segments match."""
        original = [
            {"text": "作成者", "translated_text": "Người tạo", "location": "p[0]", "type": "paragraph"},
            {"text": "項目名", "translated_text": "Tên mục", "location": "p[1]", "type": "paragraph"},
        ]
        imported = self._roundtrip(original, version="1.2")
        assert len(imported) == 2
        assert imported[0]["text"] == "作成者"
        assert imported[0]["translated_text"] == "Người tạo"
        assert imported[0]["location"] == "p[0]"
        assert imported[0]["type"] == "paragraph"

    def test_roundtrip_v21(self):
        """XLIFF 2.1: Export → Import → segments match."""
        original = [
            {"text": "作成者", "translated_text": "Người tạo", "location": "p[0]", "type": "paragraph"},
        ]
        imported = self._roundtrip(original, version="2.1")
        assert len(imported) == 1
        assert imported[0]["text"] == "作成者"
        assert imported[0]["translated_text"] == "Người tạo"
        assert imported[0]["location"] == "p[0]"

    def test_import_modified_target(self):
        """Import with edited target → different translated_text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xlf")
            export_xliff(
                [{"text": "テスト", "translated_text": "Kiểm tra"}],
                "test.docx", "docx", path,
            )
            # Modify target in file
            tree = ET.parse(path)
            for target in tree.getroot().iter(f"{{{_NS_V12}}}target"):
                target.text = "Bài kiểm tra"
                target.set("state", "final")
            tree.write(path, encoding="UTF-8", xml_declaration=True)

            imported = import_xliff(path)
            assert imported[0]["translated_text"] == "Bài kiểm tra"
            assert imported[0]["xliff_state"] == "final"


# ═══════════════════════════════════════════════════════════════════
# Version Detection Tests
# ═══════════════════════════════════════════════════════════════════

class TestVersionDetect:
    def test_detect_v12(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xlf")
            export_xliff([{"text": "テスト"}], "t.docx", "docx", path, version="1.2")
            assert detect_xliff_version(path) == "1.2"

    def test_detect_v21(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xlf")
            export_xliff([{"text": "テスト"}], "t.docx", "docx", path, version="2.1")
            assert detect_xliff_version(path) == "2.1"


# ═══════════════════════════════════════════════════════════════════
# Inline Tag Mapping Tests
# ═══════════════════════════════════════════════════════════════════

class TestInlineTagsV12:
    def test_paired_tag_to_xliff(self):
        result = _tags_to_xliff_v12("text<tag1>bold</tag1>more")
        assert '<bpt id="1"' in result
        assert '<ept id="1"' in result
        assert "bold" in result

    def test_self_closing_tag_to_xliff(self):
        result = _tags_to_xliff_v12("before<tag2/>after")
        assert '<x id="2"' in result

    def test_xliff_back_to_tags(self):
        """XLIFF 1.2 inline elements → <tagN> roundtrip."""
        original = "text<tag1>bold</tag1>more<tag3/>end"
        xliff = _tags_to_xliff_v12(original)
        restored = _xliff_v12_to_tags(xliff)
        assert restored == original

    def test_no_tags_passthrough(self):
        """Plain text without tags passes through unchanged."""
        assert _tags_to_xliff_v12("plain text") == "plain text"
        assert _xliff_v12_to_tags("plain text") == "plain text"


class TestInlineTagsV21:
    def test_paired_tag_to_xliff(self):
        result = _tags_to_xliff_v21("text<tag1>bold</tag1>more")
        assert '<pc id="1"' in result
        assert "bold" in result

    def test_self_closing_tag_to_xliff(self):
        result = _tags_to_xliff_v21("before<tag2/>after")
        assert '<ph id="2"' in result

    def test_xliff_back_to_tags(self):
        """XLIFF 2.1 inline elements → <tagN> roundtrip."""
        original = "text<tag1>bold</tag1>more<tag3/>end"
        xliff = _tags_to_xliff_v21(original)
        restored = _xliff_v21_to_tags(xliff)
        assert restored == original

    def test_no_tags_passthrough(self):
        assert _tags_to_xliff_v21("plain text") == "plain text"
        assert _xliff_v21_to_tags("plain text") == "plain text"


# ═══════════════════════════════════════════════════════════════════
# Merge Tests
# ═══════════════════════════════════════════════════════════════════

class TestMergeXliff:
    def test_merge_basic(self):
        original = [
            {"text": "作成者", "location": "p[0]", "type": "paragraph"},
            {"text": "項目名", "location": "p[1]", "type": "paragraph"},
        ]
        xliff_segs = [
            {"text": "作成者", "translated_text": "Người tạo"},
            {"text": "項目名", "translated_text": "Tên mục"},
        ]
        result = merge_xliff_into_segments(original, xliff_segs)
        assert result[0]["translated_text"] == "Người tạo"
        assert result[0]["location"] == "p[0]"
        assert result[1]["translated_text"] == "Tên mục"

    def test_merge_partial(self):
        original = [
            {"text": "作成者", "location": "p[0]"},
            {"text": "未翻訳", "location": "p[1]"},
        ]
        xliff_segs = [{"text": "作成者", "translated_text": "Người tạo"}]
        result = merge_xliff_into_segments(original, xliff_segs)
        assert result[0]["translated_text"] == "Người tạo"
        assert "translated_text" not in result[1]

    def test_merge_empty_xliff(self):
        original = [{"text": "テスト", "location": "p[0]"}]
        result = merge_xliff_into_segments(original, [])
        assert "translated_text" not in result[0]
