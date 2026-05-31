"""
Module 1: Data Ingestion
========================
AI-powered story generation for audiobook content.
All stories are 100% fictional and original.

Usage:
    from module_1_ingestion import StoryGenerator, GENRES

    gen = StoryGenerator(engine="openai")
    story = gen.generate_story(genre="ngon_tinh_hien_dai")
    gen.save_story(story)
"""

from module_1_ingestion.story_generator import (
    DISCLAIMER_EN,
    DISCLAIMER_VI,
    GENRES,
    StoryGenerator,
)

__all__ = [
    "StoryGenerator",
    "GENRES",
    "DISCLAIMER_VI",
    "DISCLAIMER_EN",
]
