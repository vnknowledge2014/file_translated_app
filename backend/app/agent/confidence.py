"""Multi-signal heuristic confidence scorer for translation quality.

Assigns a 0.0-1.0 confidence score to each translated segment based on
multiple signals (JP leak, tag preservation, length ratio, retry count,
cache status). Used to triage segments for adaptive Human-in-the-Loop.

No external model needed — runs entirely on local heuristics.
"""

from __future__ import annotations

import re

from app.utils.japanese import has_japanese

_TAG_RE = re.compile(r"</?tag\d+/?>")


def score_segment(seg: dict) -> float:
    """Calculate confidence score for a translated segment.

    Signals:
    - JP Leak: CJK chars in target (-0.5)
    - Tag mismatch: missing/hallucinated tags (-0.4)
    - Length ratio anomaly: too short/long (-0.3)
    - Retry penalty: (-0.1 per retry)
    - Cache boost: (+0.2)

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    source = seg.get("text", "")
    target = seg.get("translated_text", "")

    if not target or not target.strip():
        return 0.0

    score = 1.0

    # Signal 1: JP Leak
    target_clean = _TAG_RE.sub("", target)
    if has_japanese(target_clean):
        score -= 0.5

    # Signal 2: Tag preservation
    src_tags = sorted(_TAG_RE.findall(source))
    tgt_tags = sorted(_TAG_RE.findall(target))
    if src_tags != tgt_tags:
        score -= 0.4

    # Signal 3: Length ratio
    src_len = max(len(source.strip()), 1)
    tgt_len = len(target.strip())
    ratio = tgt_len / src_len
    if ratio < 0.3 or ratio > 3.0:
        score -= 0.3

    # Signal 4: Retry penalty
    retry_count = seg.get("retry_count", 0)
    if retry_count > 0:
        score -= 0.1 * min(retry_count, 3)

    # Signal 5: Cache boost
    if seg.get("cache_hit"):
        score = min(score + 0.2, 1.0)

    return max(0.0, min(1.0, round(score, 2)))


def classify_segments(
    segments: list[dict],
    high_threshold: float = 0.85,
    low_threshold: float = 0.60,
) -> dict:
    """Classify translated segments into confidence buckets.

    Adds 'confidence' key to each segment dict in-place.

    Returns:
        {"high": [...], "medium": [...], "low": [...], "stats": {...}}
    """
    high, medium, low = [], [], []
    total_confidence = 0.0

    for seg in segments:
        if not seg.get("translated_text", "").strip():
            seg["confidence"] = 0.0
            low.append(seg)
            continue

        conf = score_segment(seg)
        seg["confidence"] = conf
        total_confidence += conf

        if conf >= high_threshold:
            high.append(seg)
        elif conf < low_threshold:
            low.append(seg)
        else:
            medium.append(seg)

    total = len(segments)
    return {
        "high": high,
        "medium": medium,
        "low": low,
        "stats": {
            "total": total,
            "high_count": len(high),
            "medium_count": len(medium),
            "low_count": len(low),
            "high_pct": (len(high) / max(total, 1)) * 100,
            "avg_confidence": total_confidence / max(total, 1),
        },
    }
