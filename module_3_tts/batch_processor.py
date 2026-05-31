"""
Module 3: Batch TTS Processor
=============================
Xử lý hàng loạt: toàn bộ truyện text → audio từng chương.
Tự động ghép các câu đã synthesize thành file audio hoàn chỉnh.

Usage:
    from module_3_tts import BatchTTSProcessor, TTSEngine

    engine = TTSEngine(emotion="storytelling")
    processor = BatchTTSProcessor(engine)
    result = processor.process_story("data/stories/abc123.json")
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from loguru import logger
from tqdm import tqdm

from module_2_preprocessing import TextProcessor
from module_3_tts.tts_engine import TTSEngine, create_engine


class BatchTTSProcessor:
    """
    Process entire stories into audio files.

    Pipeline:
        1. Load story JSON
        2. For each chapter: clean text → split sentences → synthesize → concatenate
        3. Output: one WAV file per chapter + metadata JSON
    """

    def __init__(
        self,
        engine: Optional[TTSEngine] = None,
        max_chars_per_segment: int = 500,
        pause_between_sentences_ms: int = 350,
        add_silence_markers: bool = False,
    ):
        """
        Initialize batch processor.

        Args:
            engine: TTSEngine instance (created automatically if None)
            max_chars_per_segment: Max chars per TTS call
            pause_between_sentences_ms: Pause inserted between sentences
            add_silence_markers: Add silent gaps between sentences in final audio
        """
        self.engine = engine or create_engine()
        self.text_processor = TextProcessor(
            max_chars_per_segment=max_chars_per_segment,
            sentence_pause_ms=pause_between_sentences_ms,
        )
        self.pause_ms = pause_between_sentences_ms
        self.add_silence = add_silence_markers

    # ============================================================
    # Main Processing
    # ============================================================
    def process_story(
        self,
        story_path: str,
        output_dir: str = "data/audio",
        chapter_indices: Optional[List[int]] = None,
    ) -> Dict:
        """
        Process an entire story: text → audio files.

        Args:
            story_path: Path to story JSON file
            output_dir: Output directory for audio files
            chapter_indices: Specific chapters to process (None = all)

        Returns:
            Processing result dict with output file paths
        """
        # Load story
        story_path = Path(story_path)
        if not story_path.exists():
            raise FileNotFoundError(f"Story not found: {story_path}")

        with open(story_path, "r", encoding="utf-8") as f:
            story = json.load(f)

        story_id = story.get("id", story_path.stem)
        story_title = story.get("title", "Unknown")
        chapters = story.get("chapters", [])

        logger.info(
            f"Processing story: '{story_title}' "
            f"({len(chapters)} chapters, engine={self.engine.engine})"
        )

        # Setup output
        story_output_dir = Path(output_dir) / story_id
        story_output_dir.mkdir(parents=True, exist_ok=True)

        # Select chapters
        if chapter_indices:
            chapters = [ch for i, ch in enumerate(chapters) if i + 1 in chapter_indices]

        results = []
        total_duration = 0.0

        for chapter in tqdm(chapters, desc=f"Story {story_id[:8]}"):
            ch_num = chapter.get("chapter", 0)
            ch_title = chapter.get("title", f"Chương {ch_num}")
            ch_text = chapter.get("text", "")

            logger.info(f"  Chapter {ch_num}: '{ch_title}' ({len(ch_text)} chars)")

            # Step 1: Preprocess text
            processed = self.text_processor.process_chapter(ch_text)
            logger.debug(f"    → {processed.sentence_count} sentences")

            # Step 2: Synthesize each sentence
            chapter_dir = story_output_dir / f"chapter_{ch_num:02d}"
            chapter_dir.mkdir(exist_ok=True)

            audio_segments = []
            for i, sentence in enumerate(processed.sentences):
                try:
                    audio = self.engine.synthesize(sentence)
                    segment_path = chapter_dir / f"seg_{i:04d}.wav"
                    self.engine.save(audio, str(segment_path))
                    audio_segments.append((str(segment_path), audio))
                except Exception as e:
                    logger.error(f"Failed on sentence {i}: {e}")
                    continue

            if not audio_segments:
                logger.error(f"  ✗ Chapter {ch_num}: No audio generated")
                continue

            # Step 3: Concatenate all segments into one file
            chapter_wav = str(story_output_dir / f"chapter_{ch_num:02d}.wav")
            self._concatenate_audio(
                [seg[0] for seg in audio_segments],
                chapter_wav,
                pause_ms=self.pause_ms,
            )

            # Calculate duration
            ch_duration = sum(
                self.engine.get_audio_duration(seg[1])
                for seg in audio_segments
            )
            total_duration += ch_duration

            # Clean up individual segments
            for seg_path, _ in audio_segments:
                Path(seg_path).unlink(missing_ok=True)
            try:
                chapter_dir.rmdir()
            except OSError:
                pass

            results.append({
                "chapter": ch_num,
                "title": ch_title,
                "audio_file": chapter_wav,
                "duration_seconds": round(ch_duration, 1),
                "sentence_count": processed.sentence_count,
            })

            logger.info(
                f"  ✓ Chapter {ch_num}: {ch_duration:.0f}s audio"
            )

        # Step 4: Save metadata
        metadata = {
            "story_id": story_id,
            "title": story_title,
            "genre": story.get("genre", ""),
            "engine": self.engine.engine,
            "mode": self.engine.mode,
            "emotion": self.engine.emotion,
            "processed_at": __import__("datetime").datetime.now().isoformat(),
            "total_duration_seconds": round(total_duration, 1),
            "chapters": results,
        }

        metadata_path = story_output_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Story complete: {len(results)} chapters, "
            f"total duration: {total_duration/60:.1f} min"
        )

        return metadata

    # ============================================================
    # Audio Concatenation (FFmpeg)
    # ============================================================
    def _concatenate_audio(
        self,
        file_list: List[str],
        output_path: str,
        pause_ms: int = 350,
    ):
        """
        Concatenate multiple audio files into one.
        Uses FFmpeg concat demuxer for lossless joining.
        Optionally inserts silence between segments.
        """
        if not file_list:
            raise ValueError("No audio files to concatenate")

        if len(file_list) == 1:
            # Single file - just copy
            import shutil
            shutil.copy(file_list[0], output_path)
            return

        # Create concat file list for FFmpeg
        concat_list = output_path + ".concat.txt"
        with open(concat_list, "w") as f:
            for audio_path in file_list:
                abs_path = str(Path(audio_path).absolute())
                f.write(f"file '{abs_path}'\n")

        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list,
                "-c", "copy",
                output_path,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg concatenation failed")

        finally:
            Path(concat_list).unlink(missing_ok=True)

    # ============================================================
    # Batch Story Processing
    # ============================================================
    def process_story_directory(
        self,
        stories_dir: str = "data/stories",
        output_dir: str = "data/audio",
        max_stories: Optional[int] = None,
    ) -> List[Dict]:
        """
        Process all story JSON files in a directory.

        Args:
            stories_dir: Directory containing story JSON files
            output_dir: Output directory for audio
            max_stories: Maximum number of stories to process
        """
        stories_dir = Path(stories_dir)
        story_files = sorted(stories_dir.glob("*.json"))

        if max_stories:
            story_files = story_files[:max_stories]

        logger.info(f"Processing {len(story_files)} stories from {stories_dir}")

        results = []
        for i, story_file in enumerate(story_files):
            logger.info(f"\n{'='*50}")
            logger.info(f"Story {i+1}/{len(story_files)}: {story_file.name}")
            logger.info(f"{'='*50}")

            try:
                result = self.process_story(str(story_file), output_dir)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {story_file.name}: {e}")
                continue

        logger.info(
            f"\nBatch complete: {len(results)}/{len(story_files)} stories processed"
        )
        return results

    # ============================================================
    # Direct Text-to-Audio (No story JSON)
    # ============================================================
    def text_to_audio(
        self,
        text: str,
        output_path: str,
        preprocess: bool = True,
    ) -> str:
        """
        Convert raw text directly to audio file.

        Args:
            text: Raw text
            output_path: Output WAV file path
            preprocess: Whether to clean and split text first

        Returns:
            Output file path
        """
        if preprocess:
            processed = self.text_processor.process_chapter(text)
        else:
            processed = type("Result", (), {
                "sentences": [text],
                "sentence_count": 1,
            })()

        # Synthesize and concatenate
        audio_segments = []
        temp_files = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for i, sentence in enumerate(processed.sentences):
                audio = self.engine.synthesize(sentence)
                seg_path = os.path.join(tmpdir, f"seg_{i:04d}.wav")
                self.engine.save(audio, seg_path)
                temp_files.append(seg_path)

            self._concatenate_audio(temp_files, output_path)

        return output_path


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    """CLI for batch TTS processing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch TTS Processing for Audiobook Stories"
    )
    parser.add_argument(
        "story", type=str, nargs="?",
        help="Story JSON file or directory"
    )
    parser.add_argument(
        "--output", type=str, default="data/audio",
        help="Output directory"
    )
    parser.add_argument(
        "--engine", type=str, default="vieneu",
        help="TTS engine"
    )
    parser.add_argument(
        "--mode", type=str, default="standard",
        help="VieNeu-TTS mode"
    )
    parser.add_argument(
        "--emotion", type=str, default="storytelling",
        help="Voice emotion"
    )
    parser.add_argument(
        "--voice", type=str, default="truc_ly",
        help="Voice preset"
    )
    parser.add_argument(
        "--device", type=str, default="cpu",
        help="Compute device"
    )
    parser.add_argument(
        "--max-chars", type=int, default=500,
        help="Max chars per TTS call"
    )
    parser.add_argument(
        "--max-stories", type=int, default=None,
        help="Limit number of stories to process"
    )

    args = parser.parse_args()

    # Create engine
    engine = create_engine(
        engine=args.engine,
        mode=args.mode,
        emotion=args.emotion,
        voice=args.voice,
        device=args.device,
    )

    # Create batch processor
    processor = BatchTTSProcessor(
        engine=engine,
        max_chars_per_segment=args.max_chars,
    )

    if args.story is None:
        parser.error("Please provide a story JSON file or directory")

    story_path = Path(args.story)

    if story_path.is_dir():
        # Process all stories in directory
        results = processor.process_story_directory(
            str(story_path),
            args.output,
            args.max_stories,
        )
        total_duration = sum(
            r.get("total_duration_seconds", 0) for r in results
        )
        print(f"\n✓ Processed {len(results)} stories")
        print(f"  Total audio duration: {total_duration/60:.1f} minutes")

    elif story_path.is_file():
        # Process single story
        result = processor.process_story(str(story_path), args.output)
        print(f"\n✓ Story processed: {result['title']}")
        print(f"  Chapters: {len(result['chapters'])}")
        print(f"  Total duration: {result['total_duration_seconds']/60:.1f} minutes")
        for ch in result['chapters']:
            print(f"    Ch {ch['chapter']}: {ch['audio_file']} ({ch['duration_seconds']}s)")

    else:
        parser.error(f"Path not found: {args.story}")


if __name__ == "__main__":
    main()
