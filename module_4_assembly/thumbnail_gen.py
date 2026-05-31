"""
Module 4: Thumbnail Generator
=============================
Tự động tạo thumbnail cho video audiobook.
Style: Text overlay lớn trên nền tối + hình minh họa.

Usage:
    from module_4_assembly import ThumbnailGenerator

    gen = ThumbnailGenerator(channel_name="MyChannel")
    gen.generate(title="TÊN TRUYỆN", chapter="Chương 1", output="thumb.jpg")
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow not installed. Install with: pip install Pillow")


class ThumbnailGenerator:
    """
    Generate YouTube thumbnails for audiobook videos.

    Dimensions: 1280x720 (YouTube recommended)
    Style: Dark background + large title text + branding
    """

    WIDTH = 1280
    HEIGHT = 720

    # Color scheme
    BG_COLOR = (15, 15, 35)         # Dark navy black
    ACCENT_COLOR = (255, 50, 50)    # Red
    TITLE_COLOR = (255, 255, 255)   # White
    SUB_COLOR = (255, 200, 50)      # Gold/Yellow
    DIM_COLOR = (180, 180, 180)     # Light gray
    OVERLAY_COLOR = (0, 0, 0, 180)  # Semi-transparent black

    def __init__(
        self,
        channel_name: str = "My Audiobook Channel",
        logo_path: Optional[str] = None,
    ):
        """
        Initialize thumbnail generator.

        Args:
            channel_name: Channel name to display
            logo_path: Optional channel logo
        """
        if not HAS_PIL:
            raise ImportError("Pillow required: pip install Pillow")

        self.channel_name = channel_name
        self.logo_path = logo_path

    # ============================================================
    # Main Generation
    # ============================================================
    def generate(
        self,
        title: str,
        chapter: str = "",
        genre: str = "",
        output: str = "thumbnail.jpg",
        background_image: Optional[str] = None,
    ) -> str:
        """
        Generate a YouTube thumbnail.

        Args:
            title: Story title (displayed prominently)
            chapter: Chapter info
            genre: Story genre
            output: Output file path
            background_image: Optional custom background

        Returns:
            Output file path
        """
        logger.info(f"Generating thumbnail: {title[:40]}...")

        # Create canvas
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Add background image if provided
        if background_image and Path(background_image).exists():
            bg = Image.open(background_image).resize(
                (self.WIDTH, self.HEIGHT), Image.LANCZOS
            )
            bg = bg.filter(ImageFilter.GaussianBlur(radius=3))
            # Darken the background
            overlay = Image.new("RGBA", (self.WIDTH, self.HEIGHT), self.OVERLAY_COLOR)
            bg.paste(overlay, (0, 0), overlay)
            img.paste(bg, (0, 0))

            # Recreate draw on new image
            draw = ImageDraw.Draw(img)

        # Load fonts
        title_font = self._get_font(64, bold=True)
        sub_font = self._get_font(32, bold=False)
        small_font = self._get_font(24, bold=False)

        # --- DRAW ELEMENTS ---

        # Top accent bar
        draw.rectangle([(0, 0), (self.WIDTH, 8)], fill=self.ACCENT_COLOR)

        y_offset = 60

        # Genre badge (top left)
        if genre:
            self._draw_badge(draw, genre, (30, y_offset), font=small_font)
            y_offset += 50

        # Main title (centered, large)
        title_lines = self._wrap_text(title, title_font, max_width=self.WIDTH - 80)
        for line in title_lines[:3]:  # Max 3 lines
            text_bbox = draw.textbbox((0, 0), line, font=title_font)
            text_w = text_bbox[2] - text_bbox[0]
            x = (self.WIDTH - text_w) // 2

            # Text shadow
            draw.text(
                (x + 3, y_offset + 3), line,
                fill=(0, 0, 0), font=title_font,
            )
            # Main text
            draw.text((x, y_offset), line, fill=self.TITLE_COLOR, font=title_font)
            y_offset += text_bbox[3] - text_bbox[1] + 10

        # Chapter info
        if chapter:
            y_offset += 20
            self._draw_badge(
                draw,
                f"📖 {chapter}",
                (60, y_offset),
                font=sub_font,
                bg_color=(60, 10, 10),
                text_color=self.SUB_COLOR,
            )

        # Bottom section
        bottom_y = self.HEIGHT - 80

        # Divider line
        draw.line(
            [(40, bottom_y - 20), (self.WIDTH - 40, bottom_y - 20)],
            fill=(80, 80, 80), width=1,
        )

        # Channel name
        self._draw_badge(
            draw,
            f"🎧 {self.channel_name}",
            (40, bottom_y),
            font=sub_font,
            bg_color=self.ACCENT_COLOR,
            text_color=(255, 255, 255),
        )

        # Audio badge (right side)
        self._draw_badge(
            draw,
            "🔊 TRUYỆN AUDIO",
            (self.WIDTH - 320, bottom_y),
            font=small_font,
            bg_color=(30, 30, 60),
            text_color=self.DIM_COLOR,
        )

        # Save
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        img.save(output, "JPEG", quality=90)
        logger.info(f"✓ Thumbnail saved: {output}")
        return output

    # ============================================================
    # Helpers
    # ============================================================
    def _draw_badge(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: Tuple[int, int],
        font: ImageFont.FreeTypeFont,
        bg_color: Tuple[int, int, int] = (40, 40, 60),
        text_color: Tuple[int, int, int] = (255, 255, 255),
        padding: int = 12,
    ):
        """Draw a badge with background."""
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]

        x, y = position
        box = [
            x - padding,
            y - padding // 2,
            x + text_w + padding,
            y + text_h + padding // 2,
        ]

        # Rounded rectangle background
        draw.rounded_rectangle(box, radius=8, fill=bg_color)
        draw.text((x, y), text, fill=text_color, font=font)

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            text_bbox = font.getbbox(test_line)
            if text_bbox[2] - text_bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines if lines else [text]

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Find a suitable font that supports Vietnamese characters."""
        font_paths = [
            # DejaVu (good Vietnamese support)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # Liberation
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # Noto
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            # Fallback: search
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue

        # Last resort: default font (may not support Vietnamese)
        logger.warning("No Vietnamese-capable font found, using default")
        return ImageFont.load_default()

    # ============================================================
    # Batch Generation
    # ============================================================
    def generate_for_story(
        self,
        story_metadata: dict,
        output_dir: str = "data/thumbnails",
    ) -> List[str]:
        """Generate thumbnails for all chapters in a story."""
        story_id = story_metadata.get("story_id", "unknown")
        story_title = story_metadata.get("title", "Unknown")
        genre = story_metadata.get("genre", "")

        output_dir = Path(output_dir) / story_id
        output_dir.mkdir(parents=True, exist_ok=True)

        thumbnails = []
        for chapter in story_metadata.get("chapters", []):
            ch_num = chapter.get("chapter", 0)
            ch_title = chapter.get("title", f"Chương {ch_num}")

            output_path = str(output_dir / f"chapter_{ch_num:02d}.jpg")
            self.generate(
                title=story_title,
                chapter=ch_title,
                genre=genre,
                output=output_path,
            )
            thumbnails.append(output_path)

        return thumbnails
