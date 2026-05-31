"""
Module 5: SEO Metadata Generator
================================
Tự động tạo title, description, tags tối ưu cho YouTube SEO.

Mẫu tham khảo từ kênh Xài Não Audio (260K subs):
- Title: "AUDIO | [TÊN TRUYỆN IN HOA] | Channel #audio"
- Description: Bilingual (VI + EN), có disclaimer, có CTA
- Tags: Đa dạng, mix broad + specific keywords

Usage:
    from module_5_publishing import SEOMetadataGenerator

    meta = SEOMetadataGenerator.generate(story, chapter, channel_name="MyChannel")
    # meta -> {"title": "...", "description": "...", "tags": [...]}
"""

from datetime import datetime
from typing import Dict, List, Optional


class SEOMetadataGenerator:
    """
    Generate YouTube-optimized metadata for audiobook videos.

    Best practices from successful Vietnamese audiobook channels:
    - ALL CAPS for important keywords
    - Bilingual descriptions (Vietnamese + English)
    - Mandatory fictional disclaimer
    - Clear CTA (Like, Subscribe, Share)
    - Hashtags at the end of description
    """

    CHANNEL_EMAIL = "your-email@gmail.com"  # Override with actual email

    # ============================================================
    # Title Generation
    # ============================================================
    @staticmethod
    def generate_title(
        story_title: str,
        chapter_num: Optional[int] = None,
        channel_name: str = "Audiobook Channel",
        style: str = "xaino",  # xaino | careview | simple
    ) -> str:
        """
        Generate SEO-optimized video title.

        Args:
            story_title: Story title
            chapter_num: Chapter number (None for single-video stories)
            channel_name: Channel name for branding
            style: Title style
                - "xaino": "AUDIO | TÊN TRUYỆN | Channel #audio"
                - "careview": "[ Truyện Audio ] Tên Truyện"
                - "simple": "Tên Truyện - Audio"

        Returns:
            Title string (max 100 chars for YouTube)
        """
        if style == "xaino":
            if chapter_num:
                base = f"AUDIO | {story_title} - CHƯƠNG {chapter_num} | {channel_name} #audio"
            else:
                base = f"Full audio | {story_title.upper()} | {channel_name} #audio"
        elif style == "careview":
            if chapter_num:
                base = f"[ Truyện Audio ] {story_title} - Chương {chapter_num}"
            else:
                base = f"[ Truyện Audio ] {story_title}"
        else:  # simple
            base = f"{story_title} - Audio"
            if chapter_num:
                base += f" (Chương {chapter_num})"

        # Truncate to 100 chars (YouTube limit)
        if len(base) > 100:
            base = base[:97] + "..."

        return base

    # ============================================================
    # Description Generation
    # ============================================================
    @staticmethod
    def generate_description(
        story: Dict,
        chapter: Dict,
        channel_name: str,
        include_english: bool = True,
    ) -> str:
        """
        Generate full video description with disclaimer and SEO.

        Args:
            story: Story metadata dict
            chapter: Chapter metadata dict
            channel_name: Your channel name
            include_english: Include English translation for broader reach

        Returns:
            Description string (max 5000 chars)
        """
        story_title = story.get("title", "Truyện Audio")
        chapter_title = chapter.get("title", "")
        chapter_num = chapter.get("chapter", 1)
        genre = story.get("genre_name_vi", "")
        mood = story.get("mood", "")

        parts = []

        # === HASHTAGS ===
        hashtags = (
            "#truyenaudio #truyenfull #truyenhay #truyenngontinh "
            "#audio #audiobook"
        )

        # === ENGLISH SECTION ===
        if include_english:
            parts.append(hashtags)
            parts.append("")
            parts.append(
                f"- This is a COMPLETELY FICTIONAL story created for "
                f"entertainment purposes."
            )
            parts.append(
                f"- All characters, events, organizations and situations "
                f"in this story are fictional and do not represent real people, "
                f"real organizations or real-life events."
            )
            parts.append(
                f"- The main value of this video lies in its original audio "
                f"storytelling created by {channel_name}."
            )
            parts.append(
                f"- Audio content produced using AI text-to-speech technology, "
                f"owned by {channel_name}."
            )
            parts.append(
                f"- All content is created, edited, and owned by {channel_name}. "
                f"Please do not copy, re-upload, or reuse under any form."
            )
            parts.append("")

        # === VIETNAMESE SECTION ===
        parts.append(
            f"❤️ Đây là một câu chuyện HOÀN TOÀN HƯ CẤU được sản xuất "
            f"dưới hình thức truyện audio."
        )
        if chapter_title:
            parts.append(f"📖 {chapter_title}")
        if genre:
            parts.append(f"📚 Thể loại: {genre}")
        if mood:
            parts.append(f"🎭 Không khí: {mood}")

        parts.append("")
        parts.append(
            "🌸 Nội dung được xây dựng chủ yếu để phục vụ mục đích "
            "giải trí và mang lại trải nghiệm nghe truyện cảm xúc "
            "cho khán giả."
        )
        parts.append("")
        parts.append(
            "🥰 Mọi vấn đề vi phạm chính sách, luật bản quyền, "
            "nguyên tắc cộng đồng hoặc hợp tác kinh doanh "
            f"xin liên hệ trực tiếp qua: {SEOMetadataGenerator.CHANNEL_EMAIL}"
        )
        parts.append("")
        parts.append(
            f"✨ Video do {channel_name} sản xuất, "
            "nghiêm cấm re-up dưới mọi hình thức."
        )
        parts.append("")

        # === CTA ===
        parts.append(
            "Nếu các bạn thích truyện, hãy cho mình một Like 👍 "
            "và một Đăng ký 🔔 nhé!"
        )
        parts.append("")
        parts.append(
            "#truyenaudio #truyenngontinh #reviewtruyen "
            "#truyenngan #truyenhay #truyenfull #audio"
        )

        description = "\n".join(parts)

        # Truncate if too long
        if len(description) > 5000:
            description = description[:4997] + "..."

        return description

    # ============================================================
    # Tag Generation
    # ============================================================
    @staticmethod
    def generate_tags(genre: str = "", story_title: str = "") -> List[str]:
        """
        Generate optimized tags list.

        Strategy: Mix of broad keywords + genre-specific + story-specific

        Args:
            genre: Story genre key
            story_title: Story title for keyword extraction

        Returns:
            List of tags (max 20)
        """
        # Broad keywords (always included)
        broad_tags = [
            "truyen audio",
            "audio",
            "truyen hay",
            "truyen full",
            "audiobook",
        ]

        # Genre-specific keywords
        genre_tags_map = {
            "ngon_tinh_hien_dai": [
                "ngôn tình",
                "tình yêu hiện đại",
                "truyện tình cảm",
                "truyện hay",
            ],
            "ngon_tinh_tong_tai": [
                "tổng tài",
                "bá đạo",
                "sủng",
                "hào môn",
                "ngôn tình tổng tài",
            ],
            "trong_sinh_xuyen_khong": [
                "trọng sinh",
                "xuyên không",
                "cổ đại",
                "báo thù",
            ],
            "co_dai_cung_dau": [
                "cung đấu",
                "cổ đại",
                "vương phi",
                "hoàng đế",
            ],
            "thanh_xuan_vuon_truong": [
                "thanh xuân",
                "vườn trường",
                "học đường",
                "tình đầu",
            ],
            "chua_lanh_gia_dinh": [
                "chữa lành",
                "gia đình",
                "truyện cảm động",
                "tình thân",
            ],
            "nu_cuong": [
                "nữ cường",
                "độc lập",
                "mạnh mẽ",
                "nữ chính",
            ],
            "hai_huoc_doi_thuong": [
                "hài hước",
                "đời thường",
                "truyện vui",
                "giải trí",
            ],
        }

        # Specific keywords
        specific_tags = [
            "review truyen",
            "truyen ngắn",
            "kể chuyện",
            "truyện audio",
        ]

        # Assemble
        tags = list(broad_tags)
        tags.extend(genre_tags_map.get(genre, []))
        tags.extend(specific_tags)

        # Add story-specific keywords
        if story_title:
            words = story_title.lower().split()
            for word in words[:3]:
                if len(word) > 3 and word not in tags:
                    tags.append(word)

        # Deduplicate while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_tags.append(tag)

        return unique_tags[:20]  # YouTube allows max ~20 tags

    # ============================================================
    # Full Metadata Generation
    # ============================================================
    @staticmethod
    def generate(
        story: Dict,
        chapter: Dict,
        channel_name: str = "Audiobook Channel",
        video_file: str = "",
        thumbnail_file: str = "",
        playlist_id: Optional[str] = None,
        title_style: str = "xaino",
    ) -> Dict:
        """
        Generate complete YouTube metadata dict for one video.

        Args:
            story: Story metadata
            chapter: Chapter metadata
            channel_name: Channel name
            video_file: Path to video file
            thumbnail_file: Path to thumbnail
            playlist_id: Optional playlist ID
            title_style: "xaino" | "careview" | "simple"

        Returns:
            Complete metadata dict ready for YouTube upload
        """
        story_title = story.get("title", "Truyện Audio")
        chapter_num = chapter.get("chapter", None)
        genre = story.get("genre", "")

        title = SEOMetadataGenerator.generate_title(
            story_title=story_title,
            chapter_num=chapter_num,
            channel_name=channel_name,
            style=title_style,
        )

        description = SEOMetadataGenerator.generate_description(
            story=story,
            chapter=chapter,
            channel_name=channel_name,
        )

        tags = SEOMetadataGenerator.generate_tags(
            genre=genre,
            story_title=story_title,
        )

        metadata = {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "24",
            "made_for_kids": False,
            "filename": Path(video_file).name if video_file else "",
        }

        if video_file:
            metadata["file"] = video_file
        if thumbnail_file:
            metadata["thumbnail"] = thumbnail_file
        if playlist_id:
            metadata["playlist_id"] = playlist_id

        return metadata

    # ============================================================
    # Batch Metadata
    # ============================================================
    @staticmethod
    def generate_for_story(
        story: Dict,
        video_dir: str,
        channel_name: str,
        playlist_id: Optional[str] = None,
    ) -> Dict:
        """
        Generate metadata for all chapters in a story.

        Returns a dict ready to save as video_metadata.json
        """
        story_id = story.get("id", "unknown")
        videos_meta = []

        for chapter in story.get("chapters", []):
            ch_num = chapter.get("chapter", 0)
            video_file = str(
                Path(video_dir) / story_id / f"chapter_{ch_num:02d}.mp4"
            )
            thumb_file = str(
                Path(video_dir) / story_id / f"chapter_{ch_num:02d}_thumb.jpg"
            )

            meta = SEOMetadataGenerator.generate(
                story=story,
                chapter=chapter,
                channel_name=channel_name,
                video_file=video_file,
                thumbnail_file=thumb_file,
                playlist_id=playlist_id,
            )

            meta["publishAt"] = SEOMetadataGenerator._calculate_publish_time(
                ch_num
            )
            videos_meta.append(meta)

        return {
            "story_id": story_id,
            "title": story.get("title", "Unknown"),
            "channel": channel_name,
            "generated_at": datetime.now().isoformat(),
            "videos": videos_meta,
        }

    @staticmethod
    def _calculate_publish_time(
        chapter_num: int,
        videos_per_day: int = 2,
        start_hour: int = 18,
        start_minute: int = 30,
    ) -> str:
        """
        Calculate scheduled publish time.

        Spaces out videos to avoid flooding subscribers.

        Args:
            chapter_num: Chapter number (1-based)
            videos_per_day: How many videos per day
            start_hour: First publish hour (Vietnam time)

        Returns:
            ISO 8601 datetime string
        """
        today = datetime.now()
        day_offset = (chapter_num - 1) // videos_per_day
        slot = (chapter_num - 1) % videos_per_day

        publish_date = today + timedelta(days=day_offset)

        # Space videos 4 hours apart
        hour = start_hour + (slot * 4)
        if hour >= 24:
            hour -= 24
            publish_date += timedelta(days=1)

        publish_dt = publish_date.replace(
            hour=hour % 24,
            minute=start_minute,
            second=0,
            microsecond=0,
        )

        return publish_dt.isoformat() + "Z"


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    """CLI for SEO metadata generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate SEO metadata for audiobook videos"
    )
    parser.add_argument(
        "--story", type=str, required=True,
        help="Story title"
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Chapter number"
    )
    parser.add_argument(
        "--genre", type=str, default="",
        help="Story genre"
    )
    parser.add_argument(
        "--channel", type=str, default="Audiobook Channel",
        help="Channel name"
    )
    parser.add_argument(
        "--style", type=str, default="xaino",
        choices=["xaino", "careview", "simple"],
        help="Title style"
    )

    args = parser.parse_args()

    # Generate title
    title = SEOMetadataGenerator.generate_title(
        story_title=args.story,
        chapter_num=args.chapter,
        channel_name=args.channel,
        style=args.style,
    )

    tags = SEOMetadataGenerator.generate_tags(
        genre=args.genre,
        story_title=args.story,
    )

    print(f"\n{'='*50}")
    print(f"TITLE: {title}")
    print(f"{'='*50}")
    print(f"\nTAGS ({len(tags)}):")
    print(", ".join(tags))


if __name__ == "__main__":
    main()
