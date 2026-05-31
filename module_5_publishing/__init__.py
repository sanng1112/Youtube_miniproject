"""
Module 5: Publishing & Quản lý
==============================
Tự động hóa upload, SEO metadata, lập lịch publish.

Usage:
    from module_5_publishing import YouTubePublisher, SEOMetadataGenerator

    # Upload
    pub = YouTubePublisher(client_secrets_file="config/client_secrets.json")
    pub.upload_video("video.mp4", metadata, privacy="private")

    # SEO metadata
    meta = SEOMetadataGenerator.generate(
        story, chapter, channel_name="MyChannel"
    )
"""

from module_5_publishing.seo_generator import SEOMetadataGenerator
from module_5_publishing.youtube_uploader import YouTubePublisher

__all__ = [
    "YouTubePublisher",
    "SEOMetadataGenerator",
]
