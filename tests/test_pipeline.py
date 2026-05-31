"""
Basic smoke tests for the audiobook pipeline.
Run with: python -m pytest tests/ -v
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestTextProcessor:
    """Test Module 2: Text Preprocessing."""

    def test_clean_text(self):
        from module_2_preprocessing import TextProcessor
        processor = TextProcessor()

        # Test HTML removal
        text = "<p>Chào bạn. Đây là <b>câu chuyện</b> hư cấu!</p>"
        cleaned = processor.clean_text(text)
        assert "<p>" not in cleaned
        assert "<b>" not in cleaned
        assert "Chào bạn" in cleaned

    def test_sentence_splitting(self):
        from module_2_preprocessing import TextProcessor
        processor = TextProcessor(max_chars_per_segment=500)

        text = "Chương 1. Cô ấy bước vào phòng. Mọi người đều nhìn cô ấy! Chuyện gì đã xảy ra?"
        result = processor.process_chapter(text)
        assert result.sentence_count > 1

    def test_sensitive_filter(self):
        from module_2_preprocessing import TextProcessor
        processor = TextProcessor()

        text = "Đây là câu chuyện bình thường."
        _, warnings = processor.filter_sensitive(text)
        assert len(warnings) == 0


class TestSEOMetadata:
    """Test Module 5: SEO Metadata."""

    def test_generate_title(self):
        from module_5_publishing import SEOMetadataGenerator

        title = SEOMetadataGenerator.generate_title(
            story_title="TRUYỆN HAY",
            chapter_num=1,
            channel_name="Test Channel",
            style="xaino",
        )
        assert "AUDIO" in title
        assert "TRUYỆN HAY" in title
        assert len(title) <= 100

    def test_generate_tags(self):
        from module_5_publishing import SEOMetadataGenerator

        tags = SEOMetadataGenerator.generate_tags(
            genre="ngon_tinh_hien_dai",
        )
        assert "truyen audio" in tags
        assert len(tags) <= 20


class TestConfig:
    """Test configuration loading."""

    def test_load_config(self):
        from config import load_config

        config = load_config()
        assert "pipeline" in config
        assert "tts" in config
        assert "video" in config
        assert "youtube" in config


class TestModule1StoryGenerator:
    """Test story generator (no API calls)."""

    def test_genres_available(self):
        from module_1_ingestion import GENRES
        assert "ngon_tinh_hien_dai" in GENRES
        assert len(GENRES) >= 8

    def test_list_stories_empty(self):
        from module_1_ingestion import StoryGenerator
        # Should not crash on empty directory
        stories = StoryGenerator.list_stories("/tmp/nonexistent_dir")
        assert isinstance(stories, list)
