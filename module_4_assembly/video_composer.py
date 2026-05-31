"""
Module 4: Video Composer (FFmpeg Assembly)
==========================================
Tự động ghép video hoàn chỉnh từ audio + video nền + graphics.
Layout 3 panels ngang: Trái (Title) | Giữa (Mukbang) | Phải (Channel)

Usage:
    from module_4_assembly import VideoComposer

    composer = VideoComposer(channel_name="MyChannel")
    composer.create_video(
        audio_file="chapter_01.wav",
        mukbang_video="mukbang_library/cooking.mp4",
        title="TÊN TRUYỆN",
        chapter="Chương 1",
        output="output/chapter_01.mp4"
    )
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger


# ============================================================
# Video Composer Class
# ============================================================
class VideoComposer:
    """
    Assemble final video with 3-panel layout.

    Layout (1920x1080):
    ┌──────────────┬──────────────────────┬─────────────────────┐
    │   PANEL 1    │      PANEL 2         │       PANEL 3        │
    │   (480px)    │      (960px)         │       (480px)        │
    │              │                      │                      │
    │  • Title     │   MUKBANG / ASMR     │  • Logo kênh         │
    │  • Tên truyện│      VIDEO           │  • "Hãy Subscribe"   │
    │  • Chương    │                      │  • Chuông thông báo  │
    │              │                      │  • Social links      │
    └──────────────┴──────────────────────┴─────────────────────┘
    """

    CANVAS_WIDTH = 1920
    CANVAS_HEIGHT = 1080
    PANEL_LEFT_W = 480
    PANEL_CENTER_W = 960
    PANEL_RIGHT_W = 480
    FPS = 30
    VIDEO_CODEC = "libx264"
    AUDIO_CODEC = "aac"
    AUDIO_BITRATE = "192k"
    CRF = "18"
    PRESET = "medium"

    def __init__(
        self,
        channel_name: str = "My Audiobook Channel",
        channel_logo: Optional[str] = None,
        font_dir: Optional[str] = None,
        bgm_volume: float = 0.12,
        voice_volume: float = 1.0,
    ):
        """
        Initialize Video Composer.

        Args:
            channel_name: Channel name for overlay text
            channel_logo: Path to channel logo image
            font_dir: Directory containing .ttf fonts (for Vietnamese support)
            bgm_volume: Background music volume ratio (0.0 - 1.0)
            voice_volume: Voice audio volume ratio (0.0 - 1.0)
        """
        self.channel_name = channel_name
        self.channel_logo = channel_logo
        self.font_dir = font_dir or "/usr/share/fonts"
        self.bgm_volume = bgm_volume
        self.voice_volume = voice_volume

        # Verify FFmpeg is available
        self._check_ffmpeg()

    @staticmethod
    def _check_ffmpeg():
        """Verify FFmpeg is installed."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "FFmpeg not found. Install with: sudo apt-get install ffmpeg"
            )

    # ============================================================
    # Main Video Creation
    # ============================================================
    def create_video(
        self,
        audio_file: str,
        mukbang_video: str,
        title: str,
        chapter: str = "",
        output: str = "output.mp4",
        background_music: Optional[str] = None,
        thumbnail_output: Optional[str] = None,
        genre: str = "",
        watermark_text: str = "",
    ) -> str:
        """
        Create complete audiobook video.

        Args:
            audio_file: Path to voice audio (WAV/MP3)
            mukbang_video: Path to background mukbang video (MP4)
            title: Story title (displayed on left panel)
            chapter: Chapter info (displayed on left panel)
            output: Output video path
            background_music: Optional background music file
            thumbnail_output: Optional custom thumbnail path
            genre: Story genre for display
            watermark_text: Optional watermark

        Returns:
            Output video file path
        """
        logger.info(f"Creating video: {title[:50]}...")

        # Validate inputs
        for fpath, label in [
            (audio_file, "Audio"),
            (mukbang_video, "Mukbang video"),
        ]:
            if not Path(fpath).exists():
                raise FileNotFoundError(f"{label} not found: {fpath}")

        output = str(Path(output).absolute())
        Path(output).parent.mkdir(parents=True, exist_ok=True)

        # Step 1: Get audio duration
        audio_duration = self._get_duration(audio_file)
        logger.info(f"  Audio duration: {audio_duration:.1f}s")

        # Step 2: Resize mukbang video to center panel
        mukbang_resized = self._resize_mukbang(mukbang_video, audio_duration)

        # Step 3: Generate overlay panels (left + right)
        overlay_video = self._generate_overlay(audio_duration, title, chapter, genre)

        # Step 4: Compose 3-panel layout
        composed_video = self._compose_panels(mukbang_resized, overlay_video, output)

        # Step 5: Mix audio (voice + BGM) and mux into video
        final_output = self._mix_and_mux(
            composed_video, audio_file, background_music, output
        )

        # Step 6: Generate thumbnail
        if thumbnail_output:
            from module_4_assembly.thumbnail_gen import ThumbnailGenerator
            thumb_gen = ThumbnailGenerator(channel_name=self.channel_name)
            thumb_gen.generate(
                title=title,
                chapter=chapter,
                genre=genre,
                output=thumbnail_output,
            )

        # Cleanup temp files
        for tmp in [mukbang_resized, overlay_video, composed_video]:
            if tmp != output and tmp != final_output:
                p = Path(tmp)
                if p.exists():
                    p.unlink()

        logger.info(f"✓ Video created: {final_output}")
        return final_output

    # ============================================================
    # Mukbang Video Processing
    # ============================================================
    def _resize_mukbang(self, video_path: str, target_duration: float) -> str:
        """
        Resize and loop mukbang video for center panel.

        Crops to 960x1080, loops if shorter than target duration.
        """
        output = tempfile.mktemp(suffix="_mukbang.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",  # Loop indefinitely
            "-i", video_path,
            "-t", str(target_duration),
            "-vf",
            f"scale={self.PANEL_CENTER_W}:{self.CANVAS_HEIGHT}"
            f":force_original_aspect_ratio=increase,"
            f"crop={self.PANEL_CENTER_W}:{self.CANVAS_HEIGHT}",
            "-c:v", self.VIDEO_CODEC,
            "-preset", "ultrafast",
            "-crf", self.CRF,
            "-an",  # Remove original audio from mukbang
            "-r", str(self.FPS),
            output,
        ]

        self._run_ffmpeg(cmd, "Resize mukbang")
        return output

    # ============================================================
    # Overlay Generation (Left + Right panels)
    # ============================================================
    def _generate_overlay(
        self,
        duration: float,
        title: str,
        chapter: str,
        genre: str,
    ) -> str:
        """
        Generate static overlay for left and right panels.
        Uses FFmpeg drawtext filter for text rendering.
        """
        output = tempfile.mktemp(suffix="_overlay.mp4")

        # Build FFmpeg filter chain for text rendering
        # Left panel text
        left_filters = self._build_left_panel_text(title, chapter, genre)
        # Right panel text
        right_filters = self._build_right_panel_text()

        all_filters = f"{left_filters},{right_filters}"

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i",
            f"color=c=0x0f0f23:s={self.CANVAS_WIDTH}x{self.CANVAS_HEIGHT}"
            f":d={duration}:r={self.FPS}",
            "-vf", all_filters,
            "-c:v", self.VIDEO_CODEC,
            "-preset", "ultrafast",
            "-crf", self.CRF,
            "-pix_fmt", "yuv420p",
            output,
        ]

        self._run_ffmpeg(cmd, "Generate overlay")
        return output

    def _build_left_panel_text(
        self,
        title: str,
        chapter: str,
        genre: str,
    ) -> str:
        """
        Build FFmpeg drawtext filters for left panel.

        Displays:
        - Story title (large, bold)
        - Chapter info
        - Genre badge
        - Audio visualization indicator
        """
        font_file = self._find_font("DejaVuSans-Bold.ttf") or self._find_font("Arial.ttf")
        font_small = self._find_font("DejaVuSans.ttf") or self._find_font("Arial.ttf")

        # Escape special characters for FFmpeg
        title = self._escape_ffmpeg_text(title)
        chapter = self._escape_ffmpeg_text(chapter)
        genre = self._escape_ffmpeg_text(genre)

        filters = []

        # Title line 1 (if title is long, split at word boundary)
        if len(title) > 25:
            mid = title[:25].rfind(" ")
            if mid > 10:
                title_line1 = title[:mid]
                title_line2 = title[mid:].strip()
            else:
                title_line1 = title[:25]
                title_line2 = title[25:]

            filters.append(
                f"drawtext=fontfile='{font_file}':"
                f"text='{title_line1}':"
                f"fontsize=26:fontcolor=white@0.95:"
                f"x=15:y=30:"
                f"box=1:boxcolor=black@0.4:boxborderw=8"
            )
            if title_line2:
                filters.append(
                    f"drawtext=fontfile='{font_file}':"
                    f"text='{title_line2}':"
                    f"fontsize=26:fontcolor=white@0.95:"
                    f"x=15:y=65:"
                    f"box=1:boxcolor=black@0.4:boxborderw=8"
                )
        else:
            filters.append(
                f"drawtext=fontfile='{font_file}':"
                f"text='{title}':"
                f"fontsize=26:fontcolor=white@0.95:"
                f"x=15:y=40:"
                f"box=1:boxcolor=black@0.4:boxborderw=8"
            )

        # Chapter info
        if chapter:
            filters.append(
                f"drawtext=fontfile='{font_small}':"
                f"text='📖 {chapter}':"
                f"fontsize=22:fontcolor=yellow@0.9:"
                f"x=15:y=130:"
                f"box=1:boxcolor=black@0.4:boxborderw=6"
            )

        # Genre badge
        if genre:
            filters.append(
                f"drawtext=fontfile='{font_small}':"
                f"text='🏷 {genre}':"
                f"fontsize=18:fontcolor=#ff8888@0.85:"
                f"x=15:y=170:"
                f"box=1:boxcolor=black@0.4:boxborderw=6"
            )

        # Audio indicator
        filters.append(
            f"drawtext=fontfile='{font_small}':"
            f"text='🔊 Đang phát...':"
            f"fontsize=18:fontcolor=#88ff88@0.7:"
            f"x=15:y=h-50:"
            f"box=1:boxcolor=black@0.3:boxborderw=5"
        )

        return ",".join(filters)

    def _build_right_panel_text(self) -> str:
        """Build FFmpeg drawtext filters for right panel."""
        font_file = self._find_font("DejaVuSans-Bold.ttf") or self._find_font("Arial.ttf")
        font_small = self._find_font("DejaVuSans.ttf") or self._find_font("Arial.ttf")

        # Escape channel name
        channel = self._escape_ffmpeg_text(self.channel_name)

        right_x = self.PANEL_LEFT_W + self.PANEL_CENTER_W  # Start of right panel

        filters = []

        # Channel name
        filters.append(
            f"drawtext=fontfile='{font_file}':"
            f"text='{channel}':"
            f"fontsize=28:fontcolor=white@0.95:"
            f"x={right_x}+(w-{right_x}-text_w)/2:y=40:"
            f"box=1:boxcolor=red@0.6:boxborderw=10"
        )

        # Subscribe button
        filters.append(
            f"drawtext=fontfile='{font_small}':"
            f"text='🔔 HÃY SUBSCRIBE!':"
            f"fontsize=22:fontcolor=white@0.9:"
            f"x={right_x}+30:y=120:"
            f"box=1:boxcolor=red@0.5:boxborderw=8"
        )

        # Like reminder
        filters.append(
            f"drawtext=fontfile='{font_small}':"
            f"text='👍 Like & Share':"
            f"fontsize=20:fontcolor=white@0.85:"
            f"x={right_x}+30:y=180:"
            f"box=1:boxcolor=black@0.4:boxborderw=6"
        )

        # Bell notification
        filters.append(
            f"drawtext=fontfile='{font_small}':"
            f"text='🔔 Bật chuông thông báo':"
            f"fontsize=18:fontcolor=#ffcc00@0.8:"
            f"x={right_x}+30:y=230:"
            f"box=1:boxcolor=black@0.4:boxborderw=6"
        )

        # Comment prompt
        filters.append(
            f"drawtext=fontfile='{font_small}':"
            f"text='💬 Để lại bình luận nhé!':"
            f"fontsize=18:fontcolor=white@0.7:"
            f"x={right_x}+30:y=270:"
            f"box=1:boxcolor=black@0.3:boxborderw=5"
        )

        # Copyright notice (bottom)
        filters.append(
            f"drawtext=fontfile='{font_small}':"
            f"text='© {channel} - Nội dung hư cấu':"
            f"fontsize=14:fontcolor=gray@0.6:"
            f"x={right_x}+(w-{right_x}-text_w)/2:y=h-40:"
        )

        return ",".join(filters)

    # ============================================================
    # Panel Composition
    # ============================================================
    def _compose_panels(
        self,
        center_video: str,
        overlay_video: str,
        output: str,
    ) -> str:
        """
        Compose 3 panels horizontally using FFmpeg hstack.

        The overlay video contains all 1920px (left+center+right bg).
        We replace center region with the mukbang video.
        """
        temp_output = output.replace(".mp4", "_composed.mp4")

        # Strategy: overlay mukbang onto the center of the full canvas
        # Overlay video already has left and right panels rendered
        # We overlay center video on top at position x=PANEL_LEFT_W
        cmd = [
            "ffmpeg", "-y",
            "-i", overlay_video,  # Background with text
            "-i", center_video,    # Mukbang overlay
            "-filter_complex",
            f"[0:v][1:v]overlay={self.PANEL_LEFT_W}:0[out]",
            "-map", "[out]",
            "-c:v", self.VIDEO_CODEC,
            "-preset", self.PRESET,
            "-crf", self.CRF,
            "-pix_fmt", "yuv420p",
            temp_output,
        ]

        self._run_ffmpeg(cmd, "Compose panels")
        return temp_output

    # ============================================================
    # Audio Mixing
    # ============================================================
    def _mix_and_mux(
        self,
        video_file: str,
        voice_audio: str,
        background_music: Optional[str],
        output: str,
    ) -> str:
        """
        Mix voice audio with background music, then mux into video.
        """
        # Get voice audio duration
        voice_duration = self._get_duration(voice_audio)

        if background_music and Path(background_music).exists():
            logger.info("  Mixing voice + background music...")

            cmd = [
                "ffmpeg", "-y",
                "-i", video_file,
                "-i", voice_audio,
                "-stream_loop", "-1",
                "-i", background_music,
                "-filter_complex",
                (
                    f"[1:a]volume={self.voice_volume}[voice];"
                    f"[2:a]volume={self.bgm_volume},"
                    f"atrim=duration={voice_duration}[bgm];"
                    f"[voice][bgm]amix=inputs=2:duration=first"
                    f":dropout_transition=3[audio]"
                ),
                "-map", "0:v",
                "-map", "[audio]",
                "-c:v", "copy",
                "-c:a", self.AUDIO_CODEC,
                "-b:a", self.AUDIO_BITRATE,
                "-shortest",
                output,
            ]
        else:
            logger.info("  Adding voice audio (no BGM)...")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_file,
                "-i", voice_audio,
                "-c:v", "copy",
                "-c:a", self.AUDIO_CODEC,
                "-b:a", self.AUDIO_BITRATE,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                output,
            ]

        self._run_ffmpeg(cmd, "Mix audio")
        return output

    # ============================================================
    # Batch Processing
    # ============================================================
    def process_chapters(
        self,
        audio_metadata: Dict,
        mukbang_video: str,
        output_dir: str = "data/video",
        background_music: Optional[str] = None,
    ) -> List[str]:
        """
        Process all chapters from audio metadata into videos.

        Args:
            audio_metadata: Metadata dict from BatchTTSProcessor
            mukbang_video: Background video file
            output_dir: Output directory
            background_music: Optional BGM file

        Returns:
            List of output video paths
        """
        story_title = audio_metadata.get("title", "Unknown")
        output_dir = Path(output_dir) / audio_metadata.get("story_id", "unknown")
        output_dir.mkdir(parents=True, exist_ok=True)

        videos = []

        for chapter in audio_metadata.get("chapters", []):
            ch_num = chapter.get("chapter", 0)
            ch_title = chapter.get("title", f"Chương {ch_num}")
            audio_file = chapter.get("audio_file", "")

            if not Path(audio_file).exists():
                logger.warning(f"Audio not found: {audio_file}, skipping")
                continue

            output_path = str(output_dir / f"chapter_{ch_num:02d}.mp4")
            thumb_path = str(output_dir / f"chapter_{ch_num:02d}_thumb.jpg")

            video_path = self.create_video(
                audio_file=audio_file,
                mukbang_video=mukbang_video,
                title=story_title,
                chapter=ch_title,
                output=output_path,
                background_music=background_music,
                thumbnail_output=thumb_path,
                genre=audio_metadata.get("genre", ""),
            )
            videos.append(video_path)
            logger.info(f"  ✓ Chapter {ch_num}: {video_path}")

        # Save video metadata
        video_metadata = {
            "story_id": audio_metadata.get("story_id"),
            "title": story_title,
            "videos": [
                {
                    "chapter": ch.get("chapter"),
                    "file": str(output_dir / f"chapter_{ch.get('chapter'):02d}.mp4"),
                    "thumbnail": str(output_dir / f"chapter_{ch.get('chapter'):02d}_thumb.jpg"),
                }
                for ch in audio_metadata.get("chapters", [])
            ],
        }

        meta_path = output_dir / "video_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(video_metadata, f, ensure_ascii=False, indent=2)

        return videos

    # ============================================================
    # Helpers
    # ============================================================
    @staticmethod
    def _get_duration(filepath: str) -> float:
        """Get media duration using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    @staticmethod
    def _run_ffmpeg(cmd: List[str], step_name: str):
        """Run FFmpeg command with logging."""
        logger.debug(f"FFmpeg [{step_name}]: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg [{step_name}] failed:")
            logger.error(f"  stderr: {result.stderr[-500:]}")
            raise RuntimeError(f"FFmpeg {step_name} failed: {result.stderr[-200:]}")

    def _find_font(self, font_name: str) -> Optional[str]:
        """Find a font file on the system."""
        search_paths = [
            self.font_dir,
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
        ]
        for base in search_paths:
            for root, _, files in os.walk(base):
                for f in files:
                    if f.lower() == font_name.lower():
                        return os.path.join(root, f)
        return None

    @staticmethod
    def _escape_ffmpeg_text(text: str) -> str:
        """Escape special characters for FFmpeg drawtext filter."""
        # Replace characters that break FFmpeg drawtext
        text = text.replace("\\", "\\\\")
        text = text.replace(":", "\\:")
        text = text.replace("'", "\\'")
        text = text.replace("%", "\\%")
        return text


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    """CLI for video composition."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create audiobook video with 3-panel layout"
    )
    parser.add_argument(
        "--audio", type=str, required=True,
        help="Voice audio file (WAV/MP3)"
    )
    parser.add_argument(
        "--mukbang", type=str, required=True,
        help="Mukbang background video (MP4)"
    )
    parser.add_argument(
        "--title", type=str, required=True,
        help="Story title"
    )
    parser.add_argument(
        "--chapter", type=str, default="",
        help="Chapter info"
    )
    parser.add_argument(
        "--output", type=str, default="output.mp4",
        help="Output video path"
    )
    parser.add_argument(
        "--bgm", type=str, default=None,
        help="Background music file"
    )
    parser.add_argument(
        "--channel", type=str, default="My Audiobook Channel",
        help="Channel name"
    )
    parser.add_argument(
        "--genre", type=str, default="",
        help="Story genre"
    )

    args = parser.parse_args()

    composer = VideoComposer(channel_name=args.channel)
    composer.create_video(
        audio_file=args.audio,
        mukbang_video=args.mukbang,
        title=args.title,
        chapter=args.chapter,
        output=args.output,
        background_music=args.bgm,
        genre=args.genre,
    )


if __name__ == "__main__":
    main()
