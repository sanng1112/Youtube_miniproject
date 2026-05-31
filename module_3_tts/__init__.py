"""
Module 3: TTS Generation
========================
Vietnamese Text-to-Speech engine wrapper and batch processor.

Primary: VieNeu-TTS (local, free, open-source, Apache 2.0)
- Preset voice "Trúc Ly" (nữ Bắc) for audiobook narration
- Voice cloning for custom voices (e.g., Ngọc Huyền style)
- Emotion modes: natural & storytelling

Usage:
    from module_3_tts import TTSEngine, BatchTTSProcessor, create_engine

    # Simple usage
    engine = create_engine(emotion="storytelling")
    audio = engine.synthesize("Chào bạn...")
    engine.save(audio, "output.wav")

    # Batch processing
    processor = BatchTTSProcessor(engine)
    result = processor.process_story("data/stories/story.json")
"""

from module_3_tts.batch_processor import BatchTTSProcessor
from module_3_tts.tts_engine import (
    TTSEngine,
    create_engine,
)

__all__ = [
    "TTSEngine",
    "BatchTTSProcessor",
    "create_engine",
]
