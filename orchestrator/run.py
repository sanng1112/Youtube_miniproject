#!/usr/bin/env python3
"""
🎧 YouTube Audiobook Pipeline - Main Orchestrator
==================================================
Chạy pipeline tự động hoàn toàn:
Text → Audio → Video → YouTube

Usage:
    # Full pipeline: generate story → TTS → video → upload
    python -m orchestrator.run --full --publish

    # Just generate a story
    python -m orchestrator.run --generate --genre ngon_tinh_hien_dai

    # TTS from existing story
    python -m orchestrator.run --tts --story data/stories/my_story.json

    # Video assembly from existing audio
    python -m orchestrator.run --assemble --story-id abc123

    # YouTube upload from existing videos
    python -m orchestrator.run --upload --story-id abc123

    # List all stories
    python -m orchestrator.run --list-stories
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Pipeline Runner
# ============================================================
class PipelineRunner:
    """
    Master orchestrator for the audiobook production pipeline.

    Pipeline flow:
        1. Module 1: Generate/fetch story text
        2. Module 2: Preprocess text for TTS
        3. Module 3: Synthesize voice audio
        4. Module 4: Assemble video with background
        5. Module 5: Upload to YouTube

    Each stage can run independently or as a chain.
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        verbose: bool = False,
    ):
        """
        Initialize pipeline runner.

        Args:
            config: Custom configuration dict
            verbose: Enable debug logging
        """
        self.config = config or {}
        self.verbose = verbose

        if verbose:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG")

        # Results tracking per stage
        self.results = {
            "pipeline_start": datetime.now().isoformat(),
            "stages": {},
        }

        logger.info("Pipeline Runner initialized")

    # ============================================================
    # Stage 1: Story Generation
    # ============================================================
    def stage_generate_story(
        self,
        genre: str = "ngon_tinh_hien_dai",
        num_chapters: int = 6,
        words_per_chapter: int = 1500,
        engine: str = "openai",
        title: Optional[str] = None,
    ) -> Dict:
        """
        Stage 1: Generate an original fictional story using AI.

        Args:
            genre: Story genre key
            num_chapters: Number of chapters
            words_per_chapter: Target words per chapter
            engine: AI engine ("openai" or "anthropic")
            title: Optional custom title

        Returns:
            Story dict
        """
        logger.info("=" * 60)
        logger.info("STAGE 1: Story Generation")
        logger.info("=" * 60)

        from module_1_ingestion import StoryGenerator

        gen = StoryGenerator(
            engine=engine,
            output_dir=self.config.get("stories_dir", "data/stories"),
        )

        story = gen.generate_story(
            genre=genre,
            num_chapters=num_chapters,
            words_per_chapter=words_per_chapter,
            title=title,
        )

        filepath = gen.save_story(story)
        logger.info(f"✓ Story saved: {filepath}")
        logger.info(f"  ID: {story['id']}")
        logger.info(f"  Title: {story['title']}")
        logger.info(f"  Chapters: {story['total_chapters']}")
        logger.info(f"  Total words: {story['total_words']}")

        self.results["stages"]["generate"] = {
            "story_id": story["id"],
            "file": filepath,
            "title": story["title"],
            "chapters": story["total_chapters"],
        }

        return story

    # ============================================================
    # Stage 3: TTS Synthesis
    # ============================================================
    def stage_synthesize_audio(
        self,
        story_path: str,
        engine: str = "vieneu",
        mode: str = "standard",
        emotion: str = "storytelling",
        voice: str = "truc_ly",
        device: str = "cpu",
    ) -> Dict:
        """
        Stage 3: Convert story text to audio using TTS.

        Args:
            story_path: Path to story JSON file
            engine: TTS engine
            mode: VieNeu-TTS mode
            emotion: Voice emotion
            voice: Voice preset
            device: Compute device

        Returns:
            Audio metadata dict
        """
        logger.info("=" * 60)
        logger.info("STAGE 3: TTS Audio Synthesis")
        logger.info("=" * 60)

        from module_3_tts import BatchTTSProcessor, create_engine

        # Initialize TTS engine
        tts_engine = create_engine(
            engine=engine,
            mode=mode,
            emotion=emotion,
            voice=voice,
            device=device,
        )
        logger.info(f"TTS Engine: {tts_engine.get_info()}")

        # Process story
        processor = BatchTTSProcessor(engine=tts_engine)
        metadata = processor.process_story(
            story_path=story_path,
            output_dir=self.config.get("audio_dir", "data/audio"),
        )

        total_minutes = metadata["total_duration_seconds"] / 60
        logger.info(f"✓ Audio synthesis complete: {total_minutes:.1f} minutes")
        for ch in metadata.get("chapters", []):
            logger.info(f"  Ch {ch['chapter']}: {ch['audio_file']} ({ch['duration_seconds']}s)")

        self.results["stages"]["tts"] = {
            "story_id": metadata["story_id"],
            "total_duration_minutes": round(total_minutes, 1),
            "chapters": len(metadata.get("chapters", [])),
        }

        return metadata

    # ============================================================
    # Stage 4: Video Assembly
    # ============================================================
    def stage_assemble_video(
        self,
        audio_metadata_path: str,
        mukbang_video: Optional[str] = None,
        background_music: Optional[str] = None,
        channel_name: str = "My Audiobook Channel",
    ) -> Dict:
        """
        Stage 4: Assemble video with 3-panel layout.

        Args:
            audio_metadata_path: Path to audio metadata JSON
            mukbang_video: Background mukbang video (auto-select if None)
            background_music: Background music file
            channel_name: Channel name for branding

        Returns:
            Video metadata dict
        """
        logger.info("=" * 60)
        logger.info("STAGE 4: Video Assembly")
        logger.info("=" * 60)

        from module_4_assembly import MukbangFetcher, VideoComposer

        # Load audio metadata
        with open(audio_metadata_path, "r", encoding="utf-8") as f:
            audio_metadata = json.load(f)

        # Auto-select mukbang video from library
        if mukbang_video is None:
            logger.info("Auto-selecting background video from library...")
            api_key = os.getenv("YOUTUBE_API_KEY", "")
            fetcher = MukbangFetcher(
                youtube_api_key=api_key,
                library_dir=self.config.get("mukbang_dir", "data/mukbang_library"),
            )
            mukbang_video = fetcher.get_random_video()

            if mukbang_video is None:
                logger.warning(
                    "No mukbang videos in library. "
                    "Run: python -m module_4_assembly.mukbang_fetcher --build"
                )

        if mukbang_video is None:
            raise RuntimeError(
                "No background video available. "
                "Build library first with --build-library"
            )

        logger.info(f"Using background video: {Path(mukbang_video).name}")

        # Assemble videos
        composer = VideoComposer(
            channel_name=channel_name,
            bgm_volume=float(self.config.get("bgm_volume", 0.12)),
        )

        video_dir = self.config.get("video_dir", "data/video")

        videos = composer.process_chapters(
            audio_metadata=audio_metadata,
            mukbang_video=mukbang_video,
            output_dir=video_dir,
            background_music=background_music,
        )

        logger.info(f"✓ Video assembly complete: {len(videos)} videos")
        for v in videos:
            logger.info(f"  {v}")

        self.results["stages"]["assemble"] = {
            "story_id": audio_metadata.get("story_id"),
            "videos_created": len(videos),
        }

        # Return video metadata for next stage
        video_meta_path = (
            Path(video_dir)
            / audio_metadata.get("story_id", "unknown")
            / "video_metadata.json"
        )
        if video_meta_path.exists():
            with open(video_meta_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {"videos": videos}

    # ============================================================
    # Stage 5: YouTube Upload
    # ============================================================
    def stage_upload(
        self,
        video_metadata: Dict,
        channel_name: str = "My Audiobook Channel",
        privacy: str = "private",
    ) -> Dict:
        """
        Stage 5: Upload videos to YouTube.

        Args:
            video_metadata: Video metadata dict from stage 4
            channel_name: Channel name
            privacy: Privacy setting

        Returns:
            Upload results
        """
        logger.info("=" * 60)
        logger.info("STAGE 5: YouTube Upload")
        logger.info("=" * 60)

        from module_5_publishing import YouTubePublisher

        secrets_file = self.config.get(
            "client_secrets_file", "config/client_secrets.json"
        )

        try:
            pub = YouTubePublisher(
                client_secrets_file=secrets_file,
            )
            pub.authenticate()

            videos = video_metadata.get("videos", [])
            results = []
            for i, video_info in enumerate(videos):
                video_file = video_info.get("file", "")
                thumbnail = video_info.get("thumbnail", "")

                if not Path(video_file).exists():
                    logger.warning(f"Video not found: {video_file}")
                    continue

                # Generate SEO metadata
                from module_5_publishing import SEOMetadataGenerator

                story_title = video_metadata.get("title", "Audiobook")
                chapter_num = i + 1

                meta = {
                    "title": SEOMetadataGenerator.generate_title(
                        story_title=story_title,
                        chapter_num=chapter_num,
                        channel_name=channel_name,
                        style="xaino",
                    ),
                    "description": f"#truyenaudio #truyenfull #truyenhay #audio\n\n"
                    f"Đây là truyện HOÀN TOÀN HƯ CẤU.\n"
                    f"© {channel_name}",
                    "tags": [
                        "truyen audio", "audio", "truyen hay",
                        "truyen full", "audiobook",
                    ],
                    "thumbnail": thumbnail,
                }

                result = pub.upload_video(
                    video_file=video_file,
                    metadata=meta,
                    privacy=privacy,
                )
                results.append(result)
                logger.info(f"  [{i+1}/{len(videos)}] {result['url']}")

            self.results["stages"]["upload"] = {
                "uploaded": len(results),
                "urls": [r["url"] for r in results],
            }

            return {"results": results}

        except Exception as e:
            logger.error(f"Upload stage failed: {e}")
            raise

    # ============================================================
    # Full Pipeline
    # ============================================================
    def run_full_pipeline(
        self,
        genre: str = "ngon_tinh_hien_dai",
        num_chapters: int = 6,
        tts_engine: str = "vieneu",
        tts_emotion: str = "storytelling",
        tts_voice: str = "truc_ly",
        channel_name: str = "My Audiobook Channel",
        publish: bool = False,
        privacy: str = "private",
    ) -> Dict:
        """
        Run the COMPLETE pipeline from story to YouTube.

        Args:
            genre: Story genre
            num_chapters: Number of chapters
            tts_engine: TTS engine
            tts_emotion: Voice emotion
            tts_voice: Voice preset
            channel_name: Channel name
            publish: Whether to upload to YouTube
            privacy: YouTube privacy setting

        Returns:
            Complete pipeline results
        """
        logger.info("\n" + "🎧" * 30)
        logger.info("FULL PIPELINE: Text → Audio → Video → YouTube")
        logger.info("🎧" * 30 + "\n")

        # Stage 1: Generate story
        story = self.stage_generate_story(
            genre=genre,
            num_chapters=num_chapters,
        )

        # Stage 3: TTS (Module 2 is internal to Module 3)
        audio_metadata = self.stage_synthesize_audio(
            story_path=str(
                Path(self.config.get("stories_dir", "data/stories"))
                / f"{story['id']}_{story['genre']}.json"
            ),
            engine=tts_engine,
            emotion=tts_emotion,
            voice=tts_voice,
        )

        # Stage 4: Video assembly
        video_metadata = self.stage_assemble_video(
            audio_metadata_path=str(
                Path(self.config.get("audio_dir", "data/audio"))
                / story["id"]
                / "metadata.json"
            ),
            channel_name=channel_name,
        )

        # Stage 5: Upload (optional)
        if publish:
            self.stage_upload(
                video_metadata=video_metadata,
                channel_name=channel_name,
                privacy=privacy,
            )

        # Save pipeline results
        self.results["pipeline_end"] = datetime.now().isoformat()
        results_file = Path(self.config.get("audio_dir", "data/audio")) / "pipeline_results.json"

        # Load existing results
        all_results = []
        if results_file.exists():
            with open(results_file, "r") as f:
                all_results = json.load(f)

        all_results.append(self.results)

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        logger.info("\n" + "✅" * 30)
        logger.info("PIPELINE COMPLETE!")
        logger.info("✅" * 30)
        logger.info(f"Story: {story['title']}")
        logger.info(f"Chapters: {len(audio_metadata.get('chapters', []))}")
        logger.info(
            f"Total audio: {audio_metadata.get('total_duration_seconds', 0)/60:.1f} min"
        )
        if publish:
            logger.info(f"YouTube: {self.results['stages'].get('upload', {}).get('uploaded', 0)} videos uploaded")

        return self.results

    # ============================================================
    # Utility Commands
    # ============================================================
    def list_stories(self) -> list:
        """List all generated stories."""
        from module_1_ingestion import StoryGenerator
        return StoryGenerator.list_stories(
            self.config.get("stories_dir", "data/stories")
        )

    def build_mukbang_library(self, target_count: int = 20):
        """Build/download mukbang video library."""
        from module_4_assembly import MukbangFetcher

        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY not set in environment")

        fetcher = MukbangFetcher(
            youtube_api_key=api_key,
            library_dir=self.config.get("mukbang_dir", "data/mukbang_library"),
        )
        stats = fetcher.build_library(target_count=target_count)
        logger.info(f"Library built: {stats}")
        return stats


# ============================================================
# CLI
# ============================================================
def main():
    """Main CLI entry point for the pipeline."""
    parser = argparse.ArgumentParser(
        description="🎧 YouTube Audiobook Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (story → audio → video)
  python -m orchestrator.run --full

  # Full pipeline + upload to YouTube
  python -m orchestrator.run --full --publish

  # Generate stories in batch
  python -m orchestrator.run --batch 5 --genre ngon_tinh_hien_dai

  # TTS from existing story
  python -m orchestrator.run --tts --story data/stories/abc123.json

  # Assemble video from existing audio
  python -m orchestrator.run --assemble --story-id abc123

  # Upload existing videos to YouTube
  python -m orchestrator.run --upload --story-id abc123

  # Build mukbang video library
  python -m orchestrator.run --build-library --library-count 20
        """,
    )

    # Pipeline modes
    mode_group = parser.add_argument_group("Pipeline Mode")
    mode_group.add_argument(
        "--full", action="store_true",
        help="Run full pipeline (generate → TTS → video → upload)",
    )
    mode_group.add_argument(
        "--generate", action="store_true",
        help="Generate story only",
    )
    mode_group.add_argument(
        "--tts", action="store_true",
        help="TTS synthesis from existing story",
    )
    mode_group.add_argument(
        "--assemble", action="store_true",
        help="Video assembly from existing audio",
    )
    mode_group.add_argument(
        "--upload", action="store_true",
        help="Upload existing videos to YouTube",
    )
    mode_group.add_argument(
        "--batch", type=int, default=None,
        help="Batch generate N stories",
    )
    mode_group.add_argument(
        "--list-stories", action="store_true",
        help="List all generated stories",
    )
    mode_group.add_argument(
        "--build-library", action="store_true",
        help="Build/download mukbang video library",
    )

    # Common options
    common = parser.add_argument_group("Common Options")
    common.add_argument("--genre", type=str, default="ngon_tinh_hien_dai",
                        help="Story genre")
    common.add_argument("--chapters", type=int, default=6,
                        help="Chapters per story")
    common.add_argument("--words", type=int, default=1500,
                        help="Words per chapter")
    common.add_argument("--channel", type=str, default="My Audiobook Channel",
                        help="Channel name")
    common.add_argument("--story", type=str, default=None,
                        help="Path to story JSON file")
    common.add_argument("--story-id", type=str, default=None,
                        help="Story ID for existing content")
    common.add_argument("--publish", action="store_true",
                        help="Upload to YouTube (requires OAuth)")
    common.add_argument("--privacy", type=str, default="private",
                        choices=["private", "unlisted", "public"],
                        help="YouTube privacy setting")
    common.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose debug logging")

    # Engine options
    engine = parser.add_argument_group("Engine Options")
    engine.add_argument("--ai-engine", type=str, default="openai",
                        choices=["openai", "anthropic"],
                        help="AI engine for story generation")
    engine.add_argument("--tts-engine", type=str, default="vieneu",
                        choices=["vieneu", "edge"],
                        help="TTS engine")
    engine.add_argument("--tts-mode", type=str, default="standard",
                        choices=["standard", "turbo", "remote"],
                        help="VieNeu-TTS mode")
    engine.add_argument("--tts-emotion", type=str, default="storytelling",
                        choices=["natural", "storytelling"],
                        help="Voice emotion")
    engine.add_argument("--tts-voice", type=str, default="truc_ly",
                        help="Voice preset")
    engine.add_argument("--tts-device", type=str, default="cpu",
                        choices=["cpu", "cuda"],
                        help="TTS compute device")
    engine.add_argument("--library-count", type=int, default=20,
                        help="Target videos for mukbang library")

    args = parser.parse_args()

    # Setup Runner
    runner = PipelineRunner(verbose=args.verbose)

    try:
        # === FULL PIPELINE ===
        if args.full:
            runner.run_full_pipeline(
                genre=args.genre,
                num_chapters=args.chapters,
                tts_engine=args.tts_engine,
                tts_emotion=args.tts_emotion,
                tts_voice=args.tts_voice,
                channel_name=args.channel,
                publish=args.publish,
                privacy=args.privacy,
            )

        # === GENERATE STORY ===
        elif args.generate or args.batch:
            if args.batch:
                from module_1_ingestion import StoryGenerator
                gen = StoryGenerator(engine=args.ai_engine)
                stories = gen.generate_batch(
                    count=args.batch,
                    genres=[args.genre],
                    num_chapters=args.chapters,
                    words_per_chapter=args.words,
                )
                for s in stories:
                    print(f"  ✓ {s['id']}: {s['title']} ({s['total_words']} words)")
            else:
                runner.stage_generate_story(
                    genre=args.genre,
                    num_chapters=args.chapters,
                    words_per_chapter=args.words,
                    engine=args.ai_engine,
                )

        # === TTS SYNTHESIS ===
        elif args.tts:
            if not args.story:
                parser.error("--story is required for TTS mode")
            runner.stage_synthesize_audio(
                story_path=args.story,
                engine=args.tts_engine,
                mode=args.tts_mode,
                emotion=args.tts_emotion,
                voice=args.tts_voice,
                device=args.tts_device,
            )

        # === VIDEO ASSEMBLY ===
        elif args.assemble:
            if not args.story_id:
                parser.error("--story-id is required for assembly")
            audio_meta = (
                Path("data/audio") / args.story_id / "metadata.json"
            )
            if not audio_meta.exists():
                print(f"Audio metadata not found: {audio_meta}")
                print("Run TTS first: python -m orchestrator.run --tts --story ...")
                sys.exit(1)
            runner.stage_assemble_video(
                audio_metadata_path=str(audio_meta),
                channel_name=args.channel,
            )

        # === UPLOAD ===
        elif args.upload:
            if not args.story_id:
                parser.error("--story-id is required for upload")
            video_meta = (
                Path("data/video") / args.story_id / "video_metadata.json"
            )
            if not video_meta.exists():
                print(f"Video metadata not found: {video_meta}")
                print("Run assembly first: python -m orchestrator.run --assemble --story-id ...")
                sys.exit(1)
            with open(video_meta, "r", encoding="utf-8") as f:
                vmeta = json.load(f)
            runner.stage_upload(
                video_metadata=vmeta,
                channel_name=args.channel,
                privacy=args.privacy,
            )

        # === BUILD LIBRARY ===
        elif args.build_library:
            runner.build_mukbang_library(target_count=args.library_count)

        # === LIST STORIES ===
        elif args.list_stories:
            stories = runner.list_stories()
            if not stories:
                print("No stories found. Generate one with: python -m orchestrator.run --generate")
            else:
                print(f"\n{'ID':<14} {'Title':<50} {'Genre':<25} {'Ch':<5} {'Words':<8}")
                print("-" * 105)
                for s in stories:
                    print(
                        f"{s['id']:<14} {s['title'][:48]:<50} "
                        f"{s['genre_name_vi'][:23]:<25} {s['chapters']:<5} "
                        f"{s['total_words']:<8}"
                    )

        # === DEFAULT: show help ===
        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
