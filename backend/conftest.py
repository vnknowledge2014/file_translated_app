"""Shared test fixtures for the JP→VI translation tool."""

import pytest


@pytest.fixture
def sample_jp_text():
    """Sample Japanese text for testing."""
    return "これはテスト文です。翻訳されるべきテキストです。"


@pytest.fixture
def sample_vi_text():
    """Sample Vietnamese text for testing."""
    return "Xin chào thế giới. Đây là văn bản thử nghiệm."


@pytest.fixture
def sample_mixed_text():
    """Sample mixed JP/EN text."""
    return "Hello こんにちは World 世界"
