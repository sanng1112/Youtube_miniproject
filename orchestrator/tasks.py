"""
Celery tasks for asynchronous pipeline processing.
Allows running pipeline stages in the background.

Usage:
    celery -A orchestrator.tasks worker --loglevel=info --concurrency=1
"""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from celery import Celery
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False

if HAS_CELERY:
    app = Celery("audiobook_pipeline")
    app.config_from_object("orchestrator.celeryconfig", namespace="CELERY")

    @app.task(name="pipeline.generate_story")
    def generate_story(genre: str, num_chapters: int = 6):
        """Celery task: Generate a story."""
        from module_1_ingestion import StoryGenerator
        gen = StoryGenerator()
        story = gen.generate_story(genre=genre, num_chapters=num_chapters)
        gen.save_story(story)
        return {"story_id": story["id"], "title": story["title"]}

    @app.task(name="pipeline.synthesize_audio")
    def synthesize_audio(story_path: str):
        """Celery task: Convert story to audio."""
        from module_3_tts import BatchTTSProcessor, create_engine
        engine = create_engine(emotion="storytelling")
        processor = BatchTTSProcessor(engine=engine)
        result = processor.process_story(story_path)
        return {"story_id": result["story_id"], "duration": result["total_duration_seconds"]}

    @app.task(name="pipeline.assemble_video")
    def assemble_video(audio_metadata_path: str, channel_name: str = "My Channel"):
        """Celery task: Assemble video."""
        from module_4_assembly import VideoComposer
        import json
        with open(audio_metadata_path, "r") as f:
            audio_meta = json.load(f)
        composer = VideoComposer(channel_name=channel_name)
        videos = composer.process_chapters(audio_meta, "data/mukbang_library/sample.mp4")
        return {"videos": len(videos)}

    @app.task(name="pipeline.full_pipeline")
    def full_pipeline(genre: str = "ngon_tinh_hien_dai"):
        """Celery task: Run complete pipeline."""
        from orchestrator.run import PipelineRunner
        runner = PipelineRunner()
        return runner.run_full_pipeline(genre=genre)
else:
    # No-op if Celery not installed
    app = None
    def generate_story(*args, **kwargs): pass
    def synthesize_audio(*args, **kwargs): pass
    def assemble_video(*args, **kwargs): pass
    def full_pipeline(*args, **kwargs): pass
