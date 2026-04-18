"""Tests for multi-signal confidence scorer."""

from app.agent.confidence import score_segment, classify_segments


class TestScoreSegment:
    def test_clean_translation(self):
        seg = {"text": "作成者", "translated_text": "Người tạo"}
        assert score_segment(seg) >= 0.85

    def test_jp_leak(self):
        seg = {"text": "作成者", "translated_text": "Người 作成 tạo"}
        assert score_segment(seg) < 0.6

    def test_tag_mismatch(self):
        seg = {"text": "text<tag1>bold</tag1>more", "translated_text": "text bold more"}
        assert score_segment(seg) < 0.7

    def test_tags_preserved(self):
        seg = {"text": "text<tag1>bold</tag1>more", "translated_text": "văn bản<tag1>đậm</tag1>thêm"}
        assert score_segment(seg) >= 0.85

    def test_length_anomaly_short(self):
        seg = {"text": "これは非常に長いテキストです。翻訳してください。", "translated_text": "OK"}
        assert score_segment(seg) < 0.85

    def test_length_anomaly_long(self):
        seg = {"text": "テスト", "translated_text": "A" * 100}
        assert score_segment(seg) < 0.85

    def test_cache_boost(self):
        seg = {"text": "テスト", "translated_text": "Kiểm tra", "cache_hit": True}
        assert score_segment(seg) >= 0.85

    def test_retry_penalty(self):
        seg_no = {"text": "テスト", "translated_text": "Kiểm tra"}
        seg_retry = {"text": "テスト", "translated_text": "Kiểm tra", "retry_count": 2}
        assert score_segment(seg_no) > score_segment(seg_retry)

    def test_empty_target(self):
        assert score_segment({"text": "テスト", "translated_text": ""}) == 0.0

    def test_no_target_key(self):
        assert score_segment({"text": "テスト"}) == 0.0


class TestClassifySegments:
    def test_classify_buckets(self):
        segs = [
            {"text": "テスト", "translated_text": "Kiểm tra"},
            {"text": "作成者", "translated_text": "Người 作成 tạo"},
            {"text": "項目", "translated_text": ""},
        ]
        result = classify_segments(segs)
        assert result["stats"]["total"] == 3
        assert result["stats"]["high_count"] >= 1
        assert result["stats"]["low_count"] >= 1

    def test_confidence_added(self):
        segs = [{"text": "テスト", "translated_text": "Kiểm tra"}]
        classify_segments(segs)
        assert "confidence" in segs[0]
        assert 0.0 <= segs[0]["confidence"] <= 1.0

    def test_custom_thresholds(self):
        segs = [{"text": "テスト", "translated_text": "Kiểm tra"}]
        result = classify_segments(segs, high_threshold=0.99)
        total = result["stats"]["high_count"] + result["stats"]["medium_count"] + result["stats"]["low_count"]
        assert total == 1

    def test_empty_segments(self):
        result = classify_segments([])
        assert result["stats"]["total"] == 0
