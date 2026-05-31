"""
Module 4: Media Assembly & Post-processing
==========================================
Video composition, thumbnail generation, and background video management.

Layout: 3 horizontal panels (1920x1080)
- Left (480px): Story title & chapter info
- Center (960px): Mukbang/cooking ASMR background
- Right (480px): Channel branding & subscribe prompts

Usage:
    from module_4_assembly import VideoComposer, ThumbnailGenerator, MukbangFetcher

    composer = VideoComposer(channel_name="MyChannel")
    composer.create_video(
        audio_file="chapter_01.wav",
        mukbang_video="bg_cooking.mp4",
        title="TÊN TRUYỆN",
        chapter="Chương 1",
        output="output.mp4"
    )
"""

from module_4_assembly.mukbang_fetcher import MukbangFetcher
from module_4_assembly.thumbnail_gen import ThumbnailGenerator
from module_4_assembly.video_composer import VideoComposer

__all__ = [
    "VideoComposer",
    "ThumbnailGenerator",
    "MukbangFetcher",
]
